"""Backend d'auth de démo (docs/plugins.md "Auth de démo") — comptes en
mémoire, aucun hash de mot de passe, aucune expiration : juste de quoi
exercer le flux cookie-authentifié partagé par les 5 plugins métier de
démo (dashboard/crm_app/stock/billing/tasks). Ne PAS reprendre tel quel en
prod.

Implémente le protocole `AuthBackend` du kernel (extract_token/decode_token/
has_permission) — même chemin de résolution que `get_current_user`/
`RBACChecker` (docs/spec-v1.md §9) : ce plugin ne fait qu'alimenter ce
protocole, il ne réimplémente rien côté XUI.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from xcore import TrustedBase
from xcore.kernel.api.auth import AuthPayload, register_auth_backend, unregister_auth_backend

from xui.urls import mount_xui_pages
from xui.urls import path as xui_path

_USERS: dict[str, dict] = {
    "alice": {
        "password": "alice123",
        "roles": ["sales.view", "sales.create", "stock.view", "billing.view", "tasks.view"],
    },
    "bob": {"password": "bob123", "roles": ["sales.view", "tasks.view"]},
}

# token opaque -> AuthPayload, en mémoire process (perdu au restart, comme
# tout le reste de ce plugin de démo).
_sessions: dict[str, AuthPayload] = {}


class _InMemoryAuthBackend:
    async def extract_token(self, request) -> str | None:
        return request.cookies.get("session")

    async def decode_token(self, token: str) -> AuthPayload | None:
        return _sessions.get(token)

    async def has_permission(self, payload: AuthPayload, permission: str) -> bool:
        granted = set(payload.get("roles", [])) | set(payload.get("permissions", []))
        return permission in granted


def _login_view(ctx):
    return {"error": None}


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        register_auth_backend(_InMemoryAuthBackend())

    async def on_unload(self) -> None:
        unregister_auth_backend()

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine

        mount_xui_pages(
            router, self.ctx, engine,
            [xui_path("/login", _login_view, template="demo_auth/login.html", name="auth.login")],
        )

        @router.post("/login")
        async def do_login(request: Request):
            form = await request.form()
            username = str(form.get("username", ""))
            password = str(form.get("password", ""))
            next_path = str(form.get("next") or "/plugins/dashboard/")

            record = _USERS.get(username)
            if record is None or record["password"] != password:
                html = await engine.render(
                    "demo_auth/login.html",
                    {"error": "Identifiants invalides", "next": next_path, "request": request, "user": None, "nav": []},
                )
                return HTMLResponse(html, status_code=401)

            token = secrets.token_urlsafe(24)
            _sessions[token] = AuthPayload(sub=username, roles=list(record["roles"]))
            response = RedirectResponse(next_path, status_code=303)
            response.set_cookie("session", token, httponly=True, samesite="lax")
            return response

        @router.post("/logout")
        async def do_logout(request: Request):
            token = request.cookies.get("session")
            if token:
                _sessions.pop(token, None)
            response = RedirectResponse("/plugins/demo_auth/login", status_code=303)
            response.delete_cookie("session")
            return response

        return router

    async def handle(self, action: str, payload: dict) -> dict:
        return {"ok": False, "error": "unknown action"}
