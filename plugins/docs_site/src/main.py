"""Documentation de xui — servie par xui, comme django-cotton.com sert la
doc de cotton avec cotton. Chaque page de "Composants" rend les vrais
`<ui.x>` en live à côté du snippet qui les produit — les snippets sont des
CHAÎNES PYTHON dans ce fichier, pas du markup écrit dans les templates :
le préprocesseur `<ui.x>` scanne le texte SOURCE des templates avant même
que Jinja2 ne s'en occupe, donc un exemple de code écrit en dur dans un
`.html` serait converti en vrai composant au lieu de rester du texte
affiché (voir docs/components.md, "Attention au prose dans les templates").
En passant le snippet par le contexte de rendu, il traverse
`{{ snippet }}` (auto-échappé par Jinja2) sans jamais passer par ce
préprocesseur.

Aucune mutation, aucun RBAC — la doc est publique.
"""

from __future__ import annotations

from fastapi import APIRouter

from xcore import TrustedBase

from xui.urls import mount_xui_pages
from xui.nav import NavNode
from xui.nav import registry as nav_registry
from xui.urls import path as xui_path


def _page(**extra):
    def view(ctx):
        return extra
    return view


_SNIPPETS: dict[str, str] = {
    "card": '<ui.card title="Titre" subheading="Sous-titre">\n  Contenu de la carte.\n</ui.card>',
    "alert": '<ui.alert variant="success" title="Enregistré">\n  Les modifications ont été sauvegardées.\n</ui.alert>',
    "badge": '<ui.badge color="emerald">Payée</ui.badge>',
    "progress": '<ui.progress value="65" color="blue" show_value/>',
    "spinner": '<ui.spinner size="md"/>',
    "table": '<ui.table>\n  <thead><tr><th>Nom</th></tr></thead>\n  <tbody><tr><td>Ada</td></tr></tbody>\n</ui.table>',
    "avatar": '<ui.avatar initials="AL" color="blue"/>',
    "breadcrumbs": '<ui.breadcrumbs>\n  <ui.breadcrumb_item href="/">Accueil</ui.breadcrumb_item>\n  <ui.breadcrumb_item current>Contacts</ui.breadcrumb_item>\n</ui.breadcrumbs>',
    "input": '<ui.field label="Email">\n  <ui.input type="email" name="email" placeholder="vous@exemple.com"/>\n</ui.field>',
    "checkbox": '<ui.checkbox name="accept" label="J\'accepte les conditions"/>',
    "switch": '<ui.switch name="notifs" checked/>',
    "button": '<ui.button variant="primary">Enregistrer</ui.button>',
    "form": '<ui.form action="/plugins/crm_app/contacts/new">\n  <ui.input name="name"/>\n  <ui.button type="submit">Créer</ui.button>\n</ui.form>',
    "accordion": '<ui.accordion>\n  <ui.accordion_item header="Section 1">Contenu 1</ui.accordion_item>\n  <ui.accordion_item header="Section 2">Contenu 2</ui.accordion_item>\n</ui.accordion>',
    "tabs": '<ui.tabs default_tab="a">\n  <ui.tab name="a">Onglet A</ui.tab>\n  <ui.tab name="b">Onglet B</ui.tab>\n</ui.tabs>',
    "dropdown": '<ui.dropdown trigger_text="Actions">\n  <ui.dropdown_item>Modifier</ui.dropdown_item>\n  <ui.dropdown_item variant="danger">Supprimer</ui.dropdown_item>\n</ui.dropdown>',
    "select": '<ui.select variant="native" name="pays" placeholder="Choisir…">\n  <ui.select_option value="fr">France</ui.select_option>\n</ui.select>',
    "tooltip": '<ui.tooltip content="Plus d\'infos">\n  <ui.badge>?</ui.badge>\n</ui.tooltip>',
    "popover": '<ui.popover trigger="Ouvrir">\n  Contenu du popover.\n</ui.popover>',
    "toast": "<ui.button @click=\"$dispatch('toast', { variant:'success', title:'OK' })\">Déclencher</ui.button>",
    "calendar": '<ui.calendar mode="single" name="rdv"/>',
    "mode_toggle": '<ui.mode_toggle variant="switch"/>',
    "theme": '<ui.theme/>  {# vide si mount_theme() jamais appelé #}',
    "xuiboost": '<ui.xuiboost/>  {# une fois dans le layout de base #}',
}


def _components_base(ctx):
    return {"snippets": _SNIPPETS}


def _components_forms(ctx):
    return {"snippets": _SNIPPETS}


def _components_disclosure(ctx):
    return {"snippets": _SNIPPETS}


def _components_overlays(ctx):
    return {"snippets": _SNIPPETS}


def _components_system(ctx):
    return {"snippets": _SNIPPETS}


class Plugin(TrustedBase):
    async def on_load(self) -> None:
        nav_registry.register(
            NavNode(id="docs.root", label="Documentation", plugin=self.ctx.name, path="/plugins/docs_site/", order=100)
        )
        for node_id, label, sub_path in [
            ("docs.accueil", "Accueil", "/plugins/docs_site/"),
            ("docs.demarrage", "Démarrage", "/plugins/docs_site/demarrage"),
            ("docs.composants.base", "Composants — Base", "/plugins/docs_site/composants/base"),
            ("docs.composants.formulaire", "Composants — Formulaire", "/plugins/docs_site/composants/formulaire"),
            ("docs.composants.disclosure", "Composants — Disclosure & nav", "/plugins/docs_site/composants/disclosure"),
            ("docs.composants.overlays", "Composants — Overlays", "/plugins/docs_site/composants/overlays"),
            ("docs.composants.systeme", "Composants — Système & thème", "/plugins/docs_site/composants/systeme"),
            ("docs.guide_plugins", "Guide plugin", "/plugins/docs_site/guide-plugins"),
            ("docs.architecture", "Architecture", "/plugins/docs_site/architecture"),
        ]:
            nav_registry.register(
                NavNode(id=node_id, label=label, plugin=self.ctx.name, path=sub_path, parent_id="docs.root")
            )

    async def on_unload(self) -> None:
        nav_registry.unregister_plugin(self.ctx.name)

    def get_router(self) -> APIRouter:
        router = APIRouter()
        engine = self.get_service("ext.template_engine").engine
        mount_xui_pages(router, self.ctx, engine, [
            xui_path("/", _page(), template="docs_site/index.html", name="docs.accueil"),
            xui_path("/demarrage", _page(), template="docs_site/demarrage.html", name="docs.demarrage"),
            xui_path("/composants/base", _components_base, template="docs_site/composants_base.html", name="docs.composants.base"),
            xui_path("/composants/formulaire", _components_forms, template="docs_site/composants_formulaire.html", name="docs.composants.formulaire"),
            xui_path("/composants/disclosure", _components_disclosure, template="docs_site/composants_disclosure.html", name="docs.composants.disclosure"),
            xui_path("/composants/overlays", _components_overlays, template="docs_site/composants_overlays.html", name="docs.composants.overlays"),
            xui_path("/composants/systeme", _components_system, template="docs_site/composants_systeme.html", name="docs.composants.systeme"),
            xui_path("/guide-plugins", _page(), template="docs_site/guide_plugins.html", name="docs.guide_plugins"),
            xui_path("/architecture", _page(), template="docs_site/architecture.html", name="docs.architecture"),
        ])
        return router

    async def handle(self, action: str, payload: dict) -> dict:
        return {"ok": False, "error": "unknown action"}
