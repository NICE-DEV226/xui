"""XUI — SDK de pages server-rendues pour plugins xcore.

Consomme les contrats génériques du kernel (`xcore.kernel.api.rbac`,
`xcore.kernel.api.context.PluginContext`) exactement comme un plugin API pure
le ferait. Rien ici n'est importé par `xcore/kernel/` — voir docs/spec-v1.md
§0 pour les principes fondateurs.

xui s'importe et fonctionne (composants `<ui.x>`, CSRF, forms, mounts
statics, UIContext) **sans xcore installé** : les types xcore ne servent qu'à
l'annotation et tombent sur `Any` au runtime s'ils manquent. Seul
`mount_xui_page` exige xcore à l'appel (résolution de l'utilisateur) — voir
`xui/context.py` pour le détail.

Le rendu HTML délègue au vrai moteur de templates (`microframe.TemplateEngine`
+ `ComponentRegistry`), installé séparément depuis le sibling repo. XUI
n'ajoute aucun dispatcher générique par-dessus : les mutations passent
toujours par une route FastAPI explicite déclarée par le plugin lui-même
(docs/spec-v1.md §6, §15).
"""

from pathlib import Path

from .context import UIContext, UIPermissionDenied, UIRedirect
from .forms import FormResult, parse_form
from .mount import (
    mount_builtin_assets,
    mount_dev_proxy,
    mount_plugin_static,
    mount_spa,
    mount_spa_or_proxy,
    mount_xui_page,
    render_xui_template,
)

# Composants <ui.x> livrés avec le SDK (xui/components/*.html — voir
# NOTICE.md dans ce dossier pour leur provenance). Enregistrés à l'import de
# `xui` pour que tout projet qui dépend de xui les ait disponibles sans
# copier de fichiers — plus besoin d'un `templates/ui/` par projet.
try:
    from microframe.engine.components import auto_register_ui_components

    auto_register_ui_components(str(Path(__file__).parent / "components"))
except ImportError:  # pragma: no cover
    pass  # microframe pas installé — un plugin mode=spa pur n'en a pas besoin

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
    "mount_builtin_assets",
    "FormResult",
    "parse_form",
]
