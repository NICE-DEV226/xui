"""Facturation — liste de démo en lecture seule (même logique que stock : la
donnée est fabriquée, l'objectif est la navigation/le layout partagés)."""

from __future__ import annotations

from fastapi import APIRouter

from xcore import TrustedBase

from xui.context import UIContext
from xui.urls import mount_xui_pages
from xui.nav import NavNode
from xui.nav import registry as nav_registry
from xui.packages import registry as ui_packages
from xui.urls import path as xui_path

_INVOICES: list[dict] = [
    {"number": "INV-2026-001", "client": "Acme SARL", "amount": "1 200,00 €", "status": "paid"},
    {"number": "INV-2026-002", "client": "Globex", "amount": "450,00 €", "status": "open"},
]


def _invoices_view(ctx: UIContext):
    ctx.require_role("billing.view")
    # registry.get(...) inline dans la vue, jamais à l'import du module — une
    # référence prise à l'import serait périmée après un hot-reload de ui_kit
    # (docs/spec-v1.md §8, dernière règle ; voir xui/packages.py).
    styles = ui_packages.get("xui.ui_kit", "status_styles")
    return {"invoices": _INVOICES, "styles": styles}


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        nav_registry.register(
            NavNode(id="billing.invoices", label="Facturation", plugin=self.ctx.name,
                     path="/plugins/billing/invoices", permission="billing.view", order=30)
        )

    async def on_unload(self) -> None:
        nav_registry.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine
        mount_xui_pages(router, self.ctx, engine, [
            xui_path("/invoices", _invoices_view, template="billing/invoices.html", name="billing.invoices"),
        ], login_path="/plugins/demo_auth/login")
        return router

    async def handle(self, action: str, payload: dict) -> dict:
        if action == "list_invoices":
            return {"ok": True, "invoices": _INVOICES}
        return {"ok": False, "error": "unknown action"}
