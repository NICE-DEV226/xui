"""XUI — SDK de pages server-rendues pour plugins xcore.

Consomme les contrats génériques du kernel (`xcore.kernel.api.rbac`,
`xcore.kernel.api.context.PluginContext`) exactement comme un plugin API pure
le ferait. Rien ici n'est importé par `xcore/kernel/` — voir docs/spec-v1.md
§0 pour les principes fondateurs.

Le rendu HTML délègue au vrai moteur de templates (`microframe.TemplateEngine`
+ `ComponentRegistry`), installé séparément depuis le sibling repo. XUI
n'ajoute aucun dispatcher générique par-dessus : les mutations passent
toujours par une route FastAPI explicite déclarée par le plugin lui-même
(docs/spec-v1.md §6, §15).
"""

from .context import UIContext, UIPermissionDenied, UIRedirect
from .forms import FormResult, parse_form
from .mount import (
    mount_dev_proxy,
    mount_plugin_static,
    mount_spa,
    mount_spa_or_proxy,
    mount_xui_page,
    render_xui_template,
)

__all__ = [
    "UIContext",
    "UIPermissionDenied",
    "UIRedirect",
    "mount_xui_page",
    "render_xui_template",
    "mount_plugin_static",
    "mount_spa",
    "mount_dev_proxy",
    "mount_spa_or_proxy",
    "FormResult",
    "parse_form",
]
