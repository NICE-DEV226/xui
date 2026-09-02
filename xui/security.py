"""En-têtes de sécurité de base pour l'app hôte (démo et plugins).

Deux besoins réels, deux réponses différentes plutôt qu'un `'unsafe-inline'`
générique qui couvrirait — et cacherait — n'importe quoi :

  - **Alpine.js évalue des expressions** (`x-data`, `:class`, `@click`) via
    `eval`/`new Function` en interne — ça exige `'unsafe-eval'` dans
    `script-src`, sans échappatoire tant qu'on n'est pas passé au build
    "CSP-friendly" d'Alpine (expressions précompilées ailleurs, chantier
    à part). Assumé et documenté, pas silencieux.
  - **Un seul `<script>` inline** existe aujourd'hui dans tout le kit :
    `xui/components/mode_toggle_head.html` (anti-flash du thème, posé dans
    `<head>`). Son rendu est déterministe tant qu'il est appelé sans
    override (`storage_key`/`default` par défaut, le seul appel du repo,
    dans `templates/base.html`) — assez stable pour un hash SHA-256 exact
    plutôt qu'un blanket `'unsafe-inline'`. **Si ce composant change, ou
    si un appelant passe des params différents, regénérer le hash** (voir
    `MODE_TOGGLE_HEAD_SCRIPT_HASH` ci-dessous) — sinon le script casse net
    en mode enforce (`report_only=False`).

    `xui/components/toast.html` a lui aussi un `<script>` inline
    (enregistrement `alpine:init`, contenu statique) — mais rien ne
    l'utilise encore dans ce repo, donc pas dans la CSP pour l'instant.
    Le jour où un plugin ajoute `<ui.toast/>` quelque part, il faudra
    calculer son hash et l'ajouter ici, sous peine de le voir bloqué en
    mode enforce.

`style-src` est scindé en deux (CSP niveau 3) plutôt qu'un `'unsafe-inline'`
qui couvrirait les deux à la fois :
  - `style-src-elem 'self'` — strict : aucun `<style>` inline nulle part
    dans le kit (vérifié), donc rien à assouplir ici.
  - `style-src-attr 'unsafe-inline'` — laxiste : beaucoup de composants
    portés (avatar, mode_toggle switch, theme_builder_widget…) calculent un
    `style="..."` dynamique en JS/Alpine. Aucun mécanisme CSP (nonce ou
    hash) ne couvre les attributs `style=""` — seule alternative réelle :
    éliminer ces attributs au profit de classes, un vrai chantier de
    portage, pas fait ici.

`report_only=True` (`Content-Security-Policy-Report-Only`) reste le défaut
prudent — cette politique durcie a été vérifiée en mode enforce sur les 7
plugins de démo (voir la session de test), mais passer `report_only=False`
par défaut ici imposerait ce choix à tout consommateur de xui ; c'est à
l'app hôte de décider selon son `env`.

Le middleware est posé côté app hôte (comme `CSRFMiddleware`) : il reste au
consommateur de décider de sa politique, xui ne l'impose pas.
"""

from __future__ import annotations

from typing import Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# sha256 du contenu rendu de <ui.mode_toggle_head/> avec ses params par
# défaut (storage_key="theme", default="system") — recalculé en hashant la
# page réellement servie, pas le template source (les {{ }} doivent être
# déjà substitués). Voir le docstring du module pour la procédure si le
# composant change.
MODE_TOGGLE_HEAD_SCRIPT_HASH = "sha256-FU6yTIbNzD2Gth6YRqfv8TQ/RvKywlBj6FNaSgc3qAE="

DEFAULT_CSP = (
    "default-src 'self'; "
    f"script-src 'self' 'unsafe-eval' '{MODE_TOGGLE_HEAD_SCRIPT_HASH}'; "
    "style-src-elem 'self'; "
    "style-src-attr 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute les en-têtes de sécurité minimaux à chaque réponse.

    Args:
        report_only: mode `Content-Security-Policy-Report-Only` (surveille
            sans bloquer) — à passer `False` en production.
        exclude_paths: préfixes de chemins non couverts (ex. assets SDK
            servis par `mount_builtin_assets`, dev server proxy…).
        csp: directive CSP (défaut `DEFAULT_CSP`).
    """

    def __init__(
        self,
        app,
        report_only: bool = True,
        exclude_paths: Sequence[str] = (),
        csp: str = DEFAULT_CSP,
    ) -> None:
        super().__init__(app)
        self._header = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
        self._csp = csp
        self._excluded = tuple(exclude_paths)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if any(request.url.path.startswith(p) for p in self._excluded):
            return response
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(self._header, self._csp)
        return response