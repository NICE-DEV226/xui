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

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from xcore import Xcore

from microframe import TemplateEngine
from microframe.engine.integration.xcore import mount_template_static

from xui.csrf import CSRFMiddleware
from xui.mount import mount_builtin_assets
from xui.security import SecurityHeadersMiddleware
from xui.theme import mount_theme

xcore = Xcore(config_path="integration.yaml")




engine: TemplateEngine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    await xcore.boot(app)
    mount_template_static(app, template_dir="templates", url_prefix="/static")
    global engine
    engine = xcore.services.get("ext.template_engine").engine
    mount_builtin_assets(app)  # CSS/JS des composants <ui.x> livrés avec xui
    mount_theme(app, engine, "templates/static/theme.css")  # compilé par `make theme` depuis theme.css
    yield
    await xcore.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CSRFMiddleware,
    get_token=lambda: engine.csrf_token,
    protected_paths=["/plugins/crm_app", "/plugins/demo_auth"],
)

# CSP durcie (xui/security.py) : script-src par hash+unsafe-eval documentés
# plutôt qu'un blanket unsafe-inline, style-src scindé élément/attribut.
# report_only=True reste le défaut prudent — passer False vérifié en local
# sur les 7 plugins de démo, à activer ici quand prêt pour de vrai.
app.add_middleware(SecurityHeadersMiddleware, report_only=True)

xcore.setup(app)  # middlewares kernel — avant le démarrage, jamais dans lifespan()


@app.get("/")
async def index():
    """`/` n'est plus qu'une redirection vers le plugin dashboard (§16, "5
    plugins comme 1 app") : l'app unifiée démarre sur une page de plugin
    normale, pas sur une landing hors-plugin. La landing marketing
    (`templates/landing.html`) reste un chantier séparé, pas encore fait."""
    return RedirectResponse("/plugins/dashboard/", status_code=303)
