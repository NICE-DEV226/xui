import pytest

from xui.packages import UIPackageRegistry


def test_register_and_get():
    reg = UIPackageRegistry()
    reg.register("com.xcore.ui_kit", "ui_kit", {"button": lambda label: f"<button>{label}</button>"})

    fn = reg.get("com.xcore.ui_kit", "button")
    assert fn("Go") == "<button>Go</button>"


def test_duplicate_package_id_raises():
    reg = UIPackageRegistry()
    reg.register("com.xcore.ui_kit", "ui_kit", {})
    with pytest.raises(ValueError):
        reg.register("com.xcore.ui_kit", "other_plugin", {})


def test_missing_package_raises_keyerror():
    reg = UIPackageRegistry()
    with pytest.raises(KeyError):
        reg.get("com.unknown", "whatever")


def test_missing_export_raises_keyerror():
    reg = UIPackageRegistry()
    reg.register("com.xcore.ui_kit", "ui_kit", {"button": object()})
    with pytest.raises(KeyError):
        reg.get("com.xcore.ui_kit", "nope")


def test_unregister_plugin_removes_its_packages():
    reg = UIPackageRegistry()
    reg.register("com.a", "plugin_a", {})
    reg.register("com.b", "plugin_b", {})

    reg.unregister_plugin("plugin_a")

    with pytest.raises(KeyError):
        reg.get("com.a", "x")

    reg.register("com.a", "plugin_a", {})  # no longer collides once unregistered
