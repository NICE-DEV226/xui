"""Tâches — liste de démo en lecture seule (même logique que stock/billing)."""

from __future__ import annotations

from fastapi import APIRouter

from xcore import TrustedBase

from xui.context import UIContext
from xui.urls import mount_xui_pages
from xui.nav import NavNode
from xui.nav import registry as nav_registry
from xui.packages import registry as ui_packages
from xui.urls import path as xui_path

_TASKS: list[dict] = [
    {"title": "Relancer Globex", "assignee": "alice", "status": "todo"},
    {"title": "Réapprovisionner écrans", "assignee": "bob", "status": "in_progress"},
    {"title": "Clôturer INV-2026-001", "assignee": "alice", "status": "done"},
]


def _tasks_view(ctx: UIContext):
    ctx.require_role("tasks.view")
    styles = ui_packages.get("xui.ui_kit", "status_styles")  # inline, jamais à l'import (§8)
    return {"tasks": _TASKS, "styles": styles}


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        nav_registry.register(
            NavNode(id="tasks.list", label="Tâches", plugin=self.ctx.name,
                     path="/plugins/tasks/list", permission="tasks.view", order=40)
        )

    async def on_unload(self) -> None:
        nav_registry.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine
        mount_xui_pages(router, self.ctx, engine, [
            xui_path("/list", _tasks_view, template="tasks/list.html", name="tasks.list"),
        ], login_path="/plugins/demo_auth/login")
        return router

    async def handle(self, action: str, payload: dict) -> dict:
        if action == "list_tasks":
            return {"ok": True, "tasks": _TASKS}
        return {"ok": False, "error": "unknown action"}
