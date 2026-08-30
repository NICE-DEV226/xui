"""Rendu des composants `<ui.x>` livrés avec le SDK (xui/components/*.html).

Importe `xui`, ce qui déclenche l'auto-enregistrement du dossier components
dans le registre microframe partagé, puis rend un usage minimal de chaque
composant porté depuis django-cotton-ui pour s'assurer qu'il compile et
qu'aucun marqueur d'erreur silencieuse n'apparaît dans la sortie.
"""

import jinja2
import pytest

import xui  # noqa: F401 — enregistre xui/components/*.html

from microframe.engine.components.ui_kit import (
    UIComponentExtension,
    UIComponentPreprocessor,
    UIVarsExtension,
)

USAGES = {
    "accordion": '<ui.accordion><ui.accordion_item title="A">Body</ui.accordion_item></ui.accordion>',
    "collapse": '<ui.collapse title="C" summary="Sum">Body</ui.collapse>',
    "tabs": (
        '<ui.tabs default_tab="one"><ui.tab label="Un" value="one">Content</ui.tab>'
        '<ui.tab label="Deux" value="two">Autre</ui.tab></ui.tabs>'
    ),
    "dropdown": (
        '<ui.dropdown trigger="Menu"><ui.dropdown_item>Item 1</ui.dropdown_item>'
        '<ui.dropdown_separator/><ui.dropdown_group label="Groupe">'
        "<ui.dropdown_item>Item 2</ui.dropdown_item></ui.dropdown_group></ui.dropdown>"
    ),
    "menu": (
        '<ui.menu name="status" placeholder="Choisir"><ui.menu_trigger>Click</ui.menu_trigger>'
        '<ui.menu_content><ui.menu_search/><ui.menu_group label="Roles">'
        '<ui.menu_item value="admin" label="Admin"/></ui.menu_group></ui.menu_content></ui.menu>'
    ),
    "popover": '<ui.popover trigger="T">Contenu slot</ui.popover>',
    "tooltip": '<ui.tooltip content="Astuce !"><button>Survol</button></ui.tooltip>',
    "dialog": (
        '<ui.dialog trigger="Ouvrir" '
        'header="<div class=&quot;x&quot;><ui.dialog_title>Titre</ui.dialog_title></div>" '
        'footer="<button>OK</button>"><ui.dialog_description>Sous</ui.dialog_description>Corps</ui.dialog>'
    ),
    "drawer": (
        '<ui.drawer trigger="<button>Open</button>" title="T" content="Contenu" '
        'footer="<button>OK</button>"/>'
    ),
    "toast": "<ui.toast/>",
    "calendar": '<ui.calendar mode="single"/>',
    "datepicker": '<ui.datepicker name="d" label="Date"/>',
    "combobox": (
        '<ui.combobox name="c" label="Tags" options="{{ [\'Alpha\', \'Beta\'] }}" '
        'selected="{{ [\'Alpha\'] }}"/>'
    ),
    "select_native": (
        '<ui.select variant="native" name="s" placeholder="Choisir">'
        '<ui.select_option value="a">Abc</ui.select_option>'
        '<ui.select_option value="b" selected="true">Def</ui.select_option></ui.select>'
    ),
    "select_listbox": (
        '<ui.select variant="listbox" name="s2">'
        '<ui.menu_item value="x" label="X">X</ui.menu_item></ui.select>'
    ),
    "select_native0": (
        '<ui.select_native name="n"><ui.select_option value="1">Un</ui.select_option></ui.select_native>'
    ),
}


@pytest.fixture
def env():
    e = jinja2.Environment(enable_async=True, autoescape=True)
    e.add_extension(UIVarsExtension)
    e.add_extension(UIComponentExtension)
    e.add_extension(UIComponentPreprocessor)
    return e


async def _render(env, source, **ctx):
    return await env.from_string(source).render_async(**ctx)


@pytest.mark.parametrize("name", sorted(USAGES))
async def test_porte_rend_sans_erreur(env, name):
    out = await _render(env, USAGES[name])
    assert "Error rendering component" not in out
    assert "<!-- Component" not in out
    assert out.strip() != ""


async def test_accordion_rend_du_contenu(env):
    out = await _render(env, USAGES["accordion"])
    assert "Body" in out
    assert "A" in out


async def test_select_listbox_empile_menu(env):
    out = await _render(env, USAGES["select_listbox"])
    assert "x-select-search" not in out
    assert "menu_item" not in out


async def test_selected_option_native(env):
    out = await _render(env, USAGES["select_native"])
    assert "selected" in out


async def test_alpine_emmet_scripts_auto_heberges(env):
    out = await _render(env, "<ui.alpine/>")
    # Les trois scripts, dans le bon ordre (plugins avant le core) :
    i_collapse = out.find("xui-static/alpine/@alpinejs_collapse.min.js")
    i_focus = out.find("xui-static/alpine/@alpinejs_focus.min.js")
    i_core = out.find("xui-static/alpine/alpinejs.min.js")
    assert i_collapse != -1 and i_focus != -1 and i_core != -1
    assert i_collapse < i_focus < i_core
    # Pas de dépendance CDN ni de plugin teleport séparé (intégré au core) :
    assert "cdn.jsdelivr" not in out
    assert "@alpinejs_teleport" not in out