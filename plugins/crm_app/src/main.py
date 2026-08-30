"""Plugin CRM de démo — reprend l'exemple contacts de docs/spec-v1.md §6,
adapté au vrai kernel et au vrai moteur de rendu :

  - la page (GET /plugins/crm_app/contacts) est montée via `mount_xui_page`,
    rendue par le `TemplateEngine` partagé (extension xcore `template_engine`) ;
  - la mutation (POST /plugins/crm_app/contacts/new) est une route FastAPI
    ordinaire déclarée dans `get_router()` — pas de dispatcher générique.
    Le CSRF sur cette route est validé en amont par `xui.csrf.CSRFMiddleware`
    (câblé sur `/plugins/crm_app` dans main.py), pas ici : une seule source
    de vérité pour la validation du token.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from xcore import TrustedBase
from xcore.sdk import error, ok

from xui.context import UIContext
from xui.forms import parse_form
from xui.mount import mount_plugin_static, mount_xui_page, render_xui_template
from xui.nav import NavNode
from xui.nav import registry as nav_registry
from xui.packages import registry as ui_packages

_UI_KIT_PACKAGE = "com.xcore.ui_kit"


def _ui_kit_exports() -> dict:
    # Résolu ici, à chaque rendu — jamais mis en cache au niveau module : une
    # référence prise à l'import serait périmée après un hot-reload de
    # ui_kit (voir la règle documentée dans xui/packages.py).
    return {
        "ui_button": ui_packages.get(_UI_KIT_PACKAGE, "button"),
        "ui_badge": ui_packages.get(_UI_KIT_PACKAGE, "badge"),
    }

# PluginContext n'expose pas plugin_dir (absent du vrai xcoreruntime installé
# — voir docs/spec-v1.md §3) : chaque plugin qui a besoin de son propre
# chemin le dérive lui-même de __file__, comme ici.
_PLUGIN_DIR = Path(__file__).resolve().parent.parent

_CONTACTS: list[dict] = [
    {"name": "Grace Hopper", "email": "grace@example.com"},
    {"name": "Ada Lovelace", "email": "ada@example.com"},
]


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


def _contacts_view(ctx: UIContext):
    ctx.require_role("sales.view")
    return {
        "title": "Contacts",
        "contacts": _CONTACTS,
        "can_create": ctx.has_role("sales.create"),
        **_ui_kit_exports(),
    }


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        nav_registry.register(
            NavNode(
                id="crm.contacts",
                label="Contacts",
                plugin=self.ctx.name,
                path="/plugins/crm_app/contacts",
                permission="sales.view",
            )
        )

    async def on_unload(self) -> None:
        nav_registry.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine

        mount_plugin_static(router, _PLUGIN_DIR / "static")

        mount_xui_page(
            router,
            self.ctx,
            engine,
            path="/contacts",
            template="crm/contacts.html",
            view=_contacts_view,
            login_path="/plugins/demo_auth/login",
        )

        @router.post("/contacts/new")
        async def create_contact(request: Request):
            from xcore.kernel.api.rbac import _resolve_user

            try:
                user = await _resolve_user(request)
            except Exception:
                user = None
            ctx = UIContext(plugin_ctx=self.ctx, request=request, user=user)
            if not ctx.has_role("sales.create"):
                return RedirectResponse("/plugins/crm_app/contacts", status_code=303)

            form = await request.form()
            result = parse_form(form, ContactCreate)
            if not result.ok:
                # Ré-affiche la même page avec un message par champ et les
                # valeurs déjà saisies — pas de redirection, pour ne pas les
                # perdre (docs/spec-v1.md ne couvrait pas ce cas : extension).
                return await render_xui_template(
                    engine,
                    "crm/contacts.html",
                    self.ctx,
                    request,
                    user,
                    extra={
                        "title": "Contacts",
                        "contacts": _CONTACTS,
                        "can_create": True,
                        "errors": result.errors,
                        "values": result.values,
                        **_ui_kit_exports(),
                    },
                    status_code=422,
                )

            _CONTACTS.append({"name": result.data.name, "email": result.data.email})
            return RedirectResponse("/plugins/crm_app/contacts", status_code=303)

        return router

    async def handle(self, action: str, payload: dict) -> dict:
        if action == "list_contacts":
            return ok(contacts=_CONTACTS)
        return error("unknown action")
