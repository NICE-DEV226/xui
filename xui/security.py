"""En-têtes de sécurité de base pour l'app hôte (démo et plugins).

Pourquoi souple : les composants `<ui.x>` et les layouts consommateurs
utilisent des `<style>`/`<script>` inline (titres CSS du layout, behaviors
Alpine enregistrés sur `alpine:init` via `<script>` inline dans
`toast.html`, originaux des pages). Une CSP stricte `script-src 'self'`
(spec-v1 §13) casserait ces pages tant que ces blocs ne sont pas externalisés
dans `xui/static/`. La politique ci-dessous est donc un compromis assumé :

    default-src 'self'
    script-src  'self' 'unsafe-inline'   # hydrated par Alpine — à durcir
    style-src   'self' 'unsafe-inline'   # styles inline du layout/composants
    img-src     'self' data:
    connect-src 'self'
    object-src  'none'
    frame-ancestors 'none'
    base-uri 'self'

TODO kernel/durcissement : externaliser les blocs inline (CSS du layout en
fichier statique, enregistrement `alpine:init` de `toast.html` côté bundle)
puis retirer `'unsafe-inline'` de `script-src`. `report_only=True` (mode
`Content-Security-Policy-Report-Only`) permet de déployer en surveillance
sans bloquer — penser à le positionner selon l'environnement (`env: prod`).

Le middleware est posé côté app hôte (comme `CSRFMiddleware`) : il reste au
consommateur de décider de sa politique, xui ne l'impose pas.
"""

from __future__ import annotations

from typing import Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
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