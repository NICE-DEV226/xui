"""ui_kit — démonstration bout en bout de `UIPackageRegistry` (docs/spec-v1.md
§8) : ce plugin exporte un vocabulaire de statuts (couleur+libellé) que
`billing` et `tasks` consomment plutôt que de dupliquer chacun leur propre
dict. Aucune route/page propre — ce plugin n'existe que pour ses exports.

L'ordre de chargement (ui_kit avant billing/tasks) est garanti par le
`requires:` du VRAI kernel installé (graphe de dépendances backend, pas une
invention xui) — billing et tasks déclarent `requires: [ui_kit]` dans leur
`plugin.yaml`. Voir xui/packages.py pour la limite : `UIPackageRegistry`
lui-même ne vérifie rien au boot, il compte entièrement sur cet ordre de
chargement garanti par le kernel pour que `get()` ne rate jamais au premier
accès.
"""

from __future__ import annotations

from fastapi import APIRouter

from xcore import TrustedBase

from xui.packages import registry as ui_packages

PACKAGE_ID = "xui.ui_kit"

STATUS_STYLES = {
    # billing
    "paid": {"color": "emerald", "label": "Payée"},
    "open": {"color": "amber", "label": "En attente"},
    "overdue": {"color": "red", "label": "En retard"},
    # tasks
    "todo": {"color": "ink", "label": "À faire"},
    "in_progress": {"color": "amber", "label": "En cours"},
    "done": {"color": "emerald", "label": "Terminée"},
}


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        ui_packages.register(PACKAGE_ID, self.ctx.name, {"status_styles": STATUS_STYLES})

    async def on_unload(self) -> None:
        ui_packages.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        return APIRouter()  # export-only, aucune route

    async def handle(self, action: str, payload: dict) -> dict:
        return {"ok": False, "error": "unknown action"}
