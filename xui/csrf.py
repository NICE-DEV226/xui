"""CSRF pour les routes XUI cookie-authentifiées (docs/spec-v1.md §10).

Seules les pages en cookie-auth ont besoin de ça : le navigateur rejoue la
session cookie automatiquement sur une requête cross-site, donc une route de
mutation doit exiger en plus une valeur que la page de l'attaquant ne peut
pas lire (same-origin only) — le token rendu côté serveur dans le
formulaire. Les routes API pures en `Authorization: Bearer` ne passent
jamais par ce chemin : il n'y a pas de credential ambiant sur lequel un site
tiers pourrait s'appuyer.

Le token vient de `microframe.TemplateEngine.csrf_token` (un secret stable
généré une fois par process, exposé aux templates via `{{ csrf_token() }}` —
voir microframe/engine/core/environment.py). `get_token` est un callable
plutôt qu'un `TemplateEngine` en dur : l'engine n'existe qu'après
`await xcore.boot(app)`, exécuté dans `lifespan()` — trop tard pour
`app.add_middleware()` (Starlette refuse d'ajouter un middleware une fois
l'app démarrée). En différant la résolution à la requête, le middleware
peut être enregistré avant boot() sans connaître encore l'engine.

Rejeu du body : `BaseHTTPMiddleware.call_next()` ne réutilise pas l'objet
`Request` du middleware pour la route — il relance l'app interne avec le
`receive()` ASGI d'origine. Le cache `_body` de Starlette vit sur l'instance
`Request`, pas sur le flux : une fois `await request.form()` appelé ici, le
flux ASGI est déjà consommé et la route verrait un formulaire vide. On
capture donc les bytes bruts puis on remplace `request._receive` par une
closure qui les rejoue, avant d'appeler `call_next` — pattern standard pour
lire le body dans un `BaseHTTPMiddleware` sans le voler à la route.
"""

from __future__ import annotations

from typing import Callable, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        get_token: Callable[[], str],
        protected_paths: Sequence[str],
    ) -> None:
        super().__init__(app)
        self._get_token = get_token
        self._paths = tuple(protected_paths)

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in MUTATING_METHODS
            and request.url.path.startswith(self._paths)
            and "session" in request.cookies
        ):
            body = await request.body()  # draine le receive ASGI, cache `_body` sur CETTE instance

            async def _replay() -> dict:
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = _replay  # la route (nouvelle instance Request) relit via ce receive

            # .form() relit `self.stream()`, qui rejoue depuis `_body` déjà en
            # cache plutôt que de re-consommer `_receive` — gère multipart et
            # urlencoded sans dépendre du content-type ici.
            form = await request.form()
            token = form.get("csrf_token")
            if not token or token != self._get_token():
                return JSONResponse({"error": "csrf_invalid"}, status_code=403)
        return await call_next(request)
