"""xui s'importe et s'utilise sans xcore.

`xcoreruntime` est une dépendance optionnelle (extra `xcore`) : seul
`mount_xui_page` l'exige à l'appel. Ce test bloque l'import des modules
`xcore` puis vérifie que l'import du package, l'instanciation d'`UIContext`,
la logique RBAC et l'auto-enregistrement des composants fonctionnent quand
même — pour empêcher une régression du découplage.
"""

import builtins
import sys
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture
def sans_xcore(monkeypatch):
    """Simule un environnement sans xcore : bloque l'import et purge les
    modules xcore déjà chargés."""
    for name in [m for m in sys.modules if str(m).startswith("xcore")]:
        del sys.modules[name]

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if str(name).startswith("xcore"):
            raise ImportError(f"xcore indisponible (test) : {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    yield


def test_xui_s_importe_sans_xcore(sans_xcore):
    import xui  # noqa: F401 — l'import ne doit pas planter

    assert xui.__name__ == "xui"


def test_uicontext_instancie_sans_xcore(sans_xcore):
    from xui.context import UIContext, UIPermissionDenied

    class Req:
        pass

    u = UIContext(plugin_ctx=req_ctx(), request=Req(), user=None)
    assert u.has_role("sales.view") is False
    with pytest.raises(UIPermissionDenied):
        u.require_role("sales.view")


def test_auto_registration_des_composants_sans_xcore(sans_xcore):
    from pathlib import Path

    import xui
    from microframe.engine.components import auto_register_ui_components

    auto_register_ui_components(str(Path(xui.__file__).parent / "components"))  # ne doit pas planter


def req_ctx() -> Any:
    """plugin_ctx factice (duck-typing, aucun PluginContext xcore requis)."""

    class PluginCtx(ModuleType):
        pass

    ctx = PluginCtx("ctx")
    ctx.name = "demo"
    ctx.tenant_id = None
    ctx.caller = None

    def get_service(self, _name):
        return None

    ctx.get_service = get_service
    return ctx  # type: ignore[return-value]