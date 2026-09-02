"""Dashboard — page d'accueil de l'app unifiée.

Aucune mutation, aucune vraie donnée : juste de quoi vérifier que la
navigation inter-plugins (`NavRegistry`) et le layout partagé
(`templates/base.html`) donnent bien l'impression d'une seule application
quand 5 plugins métier indépendants sont chargés ensemble."""

from __future__ import annotations

from fastapi import APIRouter

from xcore import TrustedBase

from xui.urls import mount_xui_pages
from xui.nav import NavNode
from xui.nav import registry as nav_registry
from xui.urls import path as xui_path


def _home_view(ctx):
    return {
        "stats": [
            {"label": "Contacts", "value": 2, "color": "blue"},
            {"label": "Articles en stock", "value": 3, "color": "emerald"},
            {"label": "Factures ouvertes", "value": 1, "color": "amber"},
            {"label": "Tâches en cours", "value": 4, "color": "violet"},
        ],
    }


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        nav_registry.register(
            NavNode(id="dashboard.home", label="Dashboard", plugin=self.ctx.name,
                     path="/plugins/dashboard/", order=0)
        )

    async def on_unload(self) -> None:
        nav_registry.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine
        mount_xui_pages(router, self.ctx, engine, [
            xui_path("/", _home_view, template="dashboard/index.html", name="dashboard.home"),
        ])
        return router

    async def handle(self, action: str, payload: dict) -> dict:
        return {"ok": False, "error": "unknown action"}
