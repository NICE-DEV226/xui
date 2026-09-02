"""CRM minimal — liste + création de contacts (docs/spec-v1.md §6, adapté à
`xui.urls`/`xui.forms`). La mutation reste une route POST explicite, jamais
un dispatcher générique ; le CSRF est vérifié en amont par
`xui.csrf.CSRFMiddleware` (câblé sur `/plugins/crm_app` dans main.py)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from xcore import TrustedBase

from xui.context import UIContext, resolve_user_or_anonymous
from xui.forms import parse_form
from xui.mount import render_xui_template
from xui.nav import NavNode
from xui.nav import registry as nav_registry
from xui.urls import mount_xui_pages
from xui.urls import path as xui_path

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
    }


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        nav_registry.register(
            NavNode(id="crm.contacts", label="Contacts", plugin=self.ctx.name,
                     path="/plugins/crm_app/contacts", permission="sales.view", order=10)
        )

    async def on_unload(self) -> None:
        nav_registry.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine

        mount_xui_pages(router, self.ctx, engine, [
            xui_path("/contacts", _contacts_view, template="crm/contacts.html", name="crm.contacts"),
        ], login_path="/plugins/demo_auth/login")

        @router.post("/contacts/new")
        async def create_contact(request: Request):
            user = await resolve_user_or_anonymous(request)
            ctx = UIContext(plugin_ctx=self.ctx, request=request, user=user)
            if not ctx.has_role("sales.create"):
                return RedirectResponse("/plugins/crm_app/contacts", status_code=303)

            form = await request.form()
            result = parse_form(form, ContactCreate)
            if not result.ok:
                return await render_xui_template(
                    engine, "crm/contacts.html", self.ctx, request, user,
                    extra={
                        "title": "Contacts", "contacts": _CONTACTS, "can_create": True,
                        "errors": result.errors, "values": result.values,
                    },
                    status_code=422,
                )

            _CONTACTS.append({"name": result.data.name, "email": result.data.email})
            return RedirectResponse("/plugins/crm_app/contacts", status_code=303)

        return router

    async def handle(self, action: str, payload: dict) -> dict:
        if action == "list_contacts":
            return {"ok": True, "contacts": _CONTACTS}
        return {"ok": False, "error": "unknown action"}
