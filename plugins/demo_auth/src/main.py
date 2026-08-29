"""Auth de démo — pas pour la prod.

Sessions en mémoire (perdues au redémarrage), deux comptes en dur. Sert
uniquement à donner un vrai `AuthBackend` au kernel pour exercer le flux
RBAC partagé entre routes API et pages XUI (docs/spec-v1.md §9) : remplacer
ce plugin ne change rien à `UIContext`, `get_current_user` ou `RBACChecker`.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from xcore import AuthPayload, TrustedBase, register_auth_backend, unregister_auth_backend
from xcore.sdk import error

_USERS = {
    "alice": {"password": "alice123", "sub": "alice", "roles": ["sales.view", "sales.create"]},
    "bob": {"password": "bob123", "sub": "bob", "roles": ["sales.view"]},
}


class InMemoryAuthBackend:
    def __init__(self) -> None:
        self._sessions: dict[str, AuthPayload] = {}

    def login(self, username: str, password: str) -> str | None:
        user = _USERS.get(username)
        if not user or user["password"] != password:
            return None
        session_id = secrets.token_urlsafe(24)
        self._sessions[session_id] = {"sub": user["sub"], "roles": user["roles"]}
        return session_id

    def logout(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    async def decode_token(self, token: str) -> AuthPayload | None:
        return self._sessions.get(token)

    async def extract_token(self, request) -> str | None:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:]
        return request.cookies.get("session")

    async def has_permission(self, payload: AuthPayload, permission: str) -> bool:
        return permission in payload.get("roles", [])


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        self._backend = InMemoryAuthBackend()
        register_auth_backend(self._backend)

    async def on_unload(self) -> None:
        unregister_auth_backend()

    def get_router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/login", response_class=HTMLResponse)
        async def login_form(next: str = "/plugins/crm_app/contacts"):
            return HTMLResponse(f"""
                <!doctype html><html><body style="font-family:system-ui;max-width:320px;margin:3rem auto">
                <h1>Connexion</h1>
                <form method="post" action="/plugins/demo_auth/login" style="display:flex;flex-direction:column;gap:.5rem">
                  <input type="hidden" name="next" value="{next}">
                  <label>Utilisateur<input name="username"></label>
                  <label>Mot de passe<input name="password" type="password"></label>
                  <button type="submit">Se connecter</button>
                </form>
                <p>Comptes de démo : <code>alice/alice123</code> (sales.view + sales.create),
                <code>bob/bob123</code> (sales.view seul).</p>
                </body></html>
            """)

        @router.post("/login")
        async def login_submit(request: Request):
            form = await request.form()
            session_id = self._backend.login(str(form.get("username", "")), str(form.get("password", "")))
            if not session_id:
                return HTMLResponse("<p>Identifiants invalides</p>", status_code=401)
            next_path = str(form.get("next") or "/plugins/crm_app/contacts")
            response = RedirectResponse(next_path, status_code=303)
            response.set_cookie("session", session_id, httponly=True, samesite="lax")
            return response

        @router.post("/logout")
        async def logout(request: Request):
            session_id = request.cookies.get("session")
            if session_id:
                self._backend.logout(session_id)
            response = RedirectResponse("/plugins/crm_app/contacts", status_code=303)
            response.delete_cookie("session")
            return response

        return router

    async def handle(self, action: str, payload: dict) -> dict:
        return error("demo_auth n'expose pas d'action IPC")
