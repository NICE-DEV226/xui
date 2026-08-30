"""ui_kit — composants réutilisables par d'autres plugins (docs/spec-v1.md
§8). Exporte des callables Python via `UIPackageRegistry`, pas des fichiers
`.html` dans `ComponentRegistry` : ça montre l'usage prévu par la spec —
`package_id` + `exports` déclarés dans le manifeste, résolus par un plugin
consommateur au moment du rendu (jamais à l'import — voir xui/packages.py).

Aucune route HTTP ici : ce plugin n'exporte que de l'UI, pas d'IPC utile.
"""

from __future__ import annotations

from markupsafe import escape

from xcore import TrustedBase
from xcore.sdk import ok

from xui.packages import registry as ui_packages

PACKAGE_ID = "com.xcore.ui_kit"


def button(label: str, kind: str = "primary") -> str:
    return f'<button type="submit" class="uikit-btn uikit-btn-{escape(kind)}">{escape(label)}</button>'


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="uikit-badge uikit-badge-{escape(kind)}">{escape(text)}</span>'


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        ui_packages.register(PACKAGE_ID, self.ctx.name, {"button": button, "badge": badge})

    async def on_unload(self) -> None:
        ui_packages.unregister_plugin(self.ctx.name)

    async def handle(self, action: str, payload: dict) -> dict:
        return ok(message="ui_kit n'expose pas d'action IPC — voir ui.exports dans plugin.yaml")
