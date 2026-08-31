"""Point d'entrée démo — câble xcore + microframe + xui, sans dispatcher
générique (docs/spec-v1.md §15).

Ordre important (voir microframe/docs/integration-xcore.md et le
avertissement Starlette dans xui/csrf.py) :
  1. `FastAPI(lifespan=...)` construit l'app.
  2. `CSRFMiddleware` est ajouté AVANT que l'app démarre, mais résout le
     token paresseusement (l'engine n'existe qu'après boot()).
  3. `xcore.setup(app)` — middlewares kernel (tenancy, tracing) — doit
     lui aussi tourner avant le démarrage, jamais depuis lifespan().
  4. `await xcore.boot(app)` (dans lifespan) charge les plugins et monte
     leurs routers.

On appelle délibérément PAS `microframe.engine.integration.xcore.bind_engine()`
ni `register_action_routes()` : c'est exactement le dispatcher `<action>`/
`<remote>` à URL opaque que la spec interdit (§15). Sans ces deux appels,
`engine.env.globals["_action_resolver"]` reste vide — si un template utilise
quand même `<action>`, le tag retombe sur `href="#"` (mort, mais sans risque)
plutôt que de router vers un plugin arbitraire.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from xcore import Xcore

from microframe import TemplateEngine
from microframe.engine.integration.xcore import mount_template_static

from xui.csrf import CSRFMiddleware
from xui.mount import mount_builtin_assets
from xui.nav import registry as nav_registry
from xui.security import SecurityHeadersMiddleware

xcore = Xcore(config_path="integration.yaml")


def _engine() -> TemplateEngine:
    return xcore.services.get("ext.template_engine").engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    await xcore.boot(app)
    mount_template_static(app, template_dir="templates", url_prefix="/static")
    mount_builtin_assets(app)  # CSS/JS des composants <ui.x> livrés avec xui
    yield
    await xcore.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CSRFMiddleware,
    get_token=lambda: _engine().csrf_token,
    protected_paths=["/plugins/crm_app"],
)

# CSP souple en Report-Only pour la démo (xui/security.py) : pas de bloquage
# tant que les blocs inline (styles du layout, enregistrement alpine:init)
# ne sont pas externalisés — voir le TODO durcissement dans xui/security.py.
app.add_middleware(SecurityHeadersMiddleware, report_only=True)

xcore.setup(app)  # middlewares kernel — avant le démarrage, jamais dans lifespan()


@app.get("/")
async def index(request: Request):
    """Landing de démo — rendu server-side des composants interactifs portés.

    Pas de `mount_xui_page` ici (pas de plugin) : contexte de template bâti à
    la main comme `xui.mount._base_render_context` (nav filtré par rôles,
    utilisateur résolu par le même `_resolve_user` que le kernel)."""
    from xcore.kernel.api.rbac import _resolve_user

    try:
        user = await _resolve_user(request)
    except Exception:
        user = None
    user_roles = set(user.get("roles", [])) | set(user.get("permissions", [])) if user else set()
    html = await _engine().render(
        "landing.html",
        {
            "user": user,
            "nav": nav_registry.tree(user_roles),
            "request": request,
        },
    )
    return HTMLResponse(html)
