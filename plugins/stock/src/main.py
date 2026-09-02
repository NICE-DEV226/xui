"""Stock — inventaire de démo en lecture seule (pas de mutation : le but est
de vérifier la navigation/le layout partagés entre plugins, pas de couvrir
un vrai flux d'inventaire)."""

from __future__ import annotations

from fastapi import APIRouter

from xcore import TrustedBase

from xui.context import UIContext
from xui.urls import mount_xui_pages
from xui.nav import NavNode
from xui.nav import registry as nav_registry
from xui.urls import path as xui_path

_ITEMS: list[dict] = [
    {"sku": "SKU-001", "name": "Clavier mécanique", "qty": 42},
    {"sku": "SKU-002", "name": "Écran 27\"", "qty": 7},
    {"sku": "SKU-003", "name": "Câble USB-C", "qty": 150},
]


def _items_view(ctx: UIContext):
    ctx.require_role("stock.view")
    return {"items": _ITEMS}


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        nav_registry.register(
            NavNode(id="stock.items", label="Stock", plugin=self.ctx.name,
                     path="/plugins/stock/items", permission="stock.view", order=20)
        )

    async def on_unload(self) -> None:
        nav_registry.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine
        mount_xui_pages(router, self.ctx, engine, [
            xui_path("/items", _items_view, template="stock/items.html", name="stock.items"),
        ], login_path="/plugins/demo_auth/login")
        return router

    async def handle(self, action: str, payload: dict) -> dict:
        if action == "list_items":
            return {"ok": True, "items": _ITEMS}
        return {"ok": False, "error": "unknown action"}
