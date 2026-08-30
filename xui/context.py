"""UIContext — injecté dans chaque vue de page XUI.

Aucune logique RBAC dupliquée : `has_role`/`require_role` lisent le même
`AuthPayload` que `get_current_user`/`RBACChecker` (xcore.kernel.api.rbac),
résolu via la même fonction `_resolve_user`. `call_plugin` appelle
`PluginContext.caller` avec exactement la même convention que
`TrustedBase.call_plugin` (xcore.kernel.api.contract) pour rester cohérent
avec les plugins IPC-purs.

## Sans xcore

`xui` s'importe et s'utilise en base (UIContext, CSRF, composants, forms,
mounts statics) sans xcore installé : les types `AuthPayload`/`PluginContext`
ne servent qu'à l'annotation et tombent sur `Any` si le kernel est absent
(voir `__init__.py`). Seul `mount_xui_page` — qui résout l'utilisateur via
`xcore.kernel.api.rbac._resolve_user` — exige xcore au moment de l'appel, pas
à l'import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from starlette.requests import Request

if TYPE_CHECKING:  # types xcore utilisés seulement pour l'annotation
    from xcore.kernel.api.auth import AuthPayload
    from xcore.kernel.api.context import PluginContext
else:
    # xui est utilisable sans xcore : ces deux types ne servent qu'au typage,
    # jamais à la logique. Au runtime on conserve des aliases optionnels.
    try:
        from xcore.kernel.api.auth import AuthPayload
        from xcore.kernel.api.context import PluginContext
    except ImportError:
        AuthPayload = Any  # type: ignore[misc, assignment]
        PluginContext = Any  # type: ignore[misc, assignment]



class UIPermissionDenied(Exception):
    """Levée par `UIContext.require_role` — jamais laissée remonter telle
    quelle : `mount_xui_page` l'intercepte pour rediriger vers le login
    (utilisateur anonyme) ou rendre une page 403 (rôle manquant)."""

    def __init__(self, required_roles: tuple[str, ...]) -> None:
        self.required_roles = required_roles
        super().__init__(f"rôle(s) requis manquant(s) : {', '.join(required_roles)}")


@dataclass
class UIRedirect:
    path: str
    code: int = 303


@dataclass
class UIContext:
    plugin_ctx: PluginContext
    request: Request
    user: AuthPayload | None

    def get_service(self, name: str) -> Any:
        return self.plugin_ctx.get_service(name)

    async def call_plugin(self, plugin: str, action: str, payload: dict | None = None) -> dict:
        if self.plugin_ctx.caller is None:
            raise RuntimeError(
                f"[{self.plugin_ctx.name}] call_plugin() indisponible "
                "(pas de caller injecté — plugin sandboxed ou contexte de test)."
            )
        return await self.plugin_ctx.caller(
            plugin,
            action,
            payload or {},
            caller=self.plugin_ctx.name,
            tenant_id=self.plugin_ctx.tenant_id,
        )

    def has_role(self, *roles: str) -> bool:
        if self.user is None:
            return False
        granted = set(self.user.get("roles", [])) | set(self.user.get("permissions", []))
        return bool(granted & set(roles))

    def require_role(self, *roles: str) -> None:
        if not self.has_role(*roles):
            raise UIPermissionDenied(roles)

    def redirect(self, path: str, code: int = 303) -> UIRedirect:
        return UIRedirect(path, code)
