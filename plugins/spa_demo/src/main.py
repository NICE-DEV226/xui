"""Plugin SPA de démo — preuve du contrat §14 : un plugin React/Vue/Svelte
n'a AUCUNE obligation envers xui. Volontairement écrit sans un seul import
`xui` pour le démontrer — juste FastAPI + StaticFiles, comme n'importe quel
serveur qui sert un build statique. (`xui.mount_spa`/`mount_spa_or_proxy`
existent comme raccourcis équivalents pour qui préfère ne pas réécrire ces
quelques lignes à chaque plugin — voir plugins/crm_app pour un exemple qui,
lui, utilise le SDK xui côté rendu server-side.)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from xcore import TrustedBase
from xcore.sdk import ok

_PLUGIN_DIR = Path(__file__).resolve().parent.parent
_DIST_DIR = _PLUGIN_DIR / "ui" / "dist"


class Plugin(TrustedBase):
    def get_router(self) -> APIRouter:
        router = APIRouter()

        assets_dir = _DIST_DIR / "assets"
        if assets_dir.is_dir():
            router.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        index_path = _DIST_DIR / "index.html"

        @router.get("/{full_path:path}", response_class=HTMLResponse)
        async def spa_fallback(full_path: str):
            return FileResponse(index_path)

        return router

    async def handle(self, action: str, payload: dict) -> dict:
        return ok(message="spa_demo n'expose pas d'action IPC — voir /plugins/spa_demo/")
