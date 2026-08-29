"""NavRegistry — arbre de navigation cross-plugin.

La spec (docs/spec-v1.md §7) place ce registre sur `KernelContext` pour que
tout plugin y accède sans importer xui. Le vrai `xcore` installé
(xcoreruntime==2.5.2) n'a pas ce slot, et ce dépôt ne patch pas le kernel
installé (principe §0.1 : rien dans xcore/kernel/ ne connaît xui — dans
l'autre sens aussi, xui ne doit pas avoir besoin de forker le kernel pour
exister). Le registre vit donc ici comme singleton de module : même effet
dans un seul process (`from xui.nav import registry`), tant qu'une vraie
extension kernel n'est pas montée en amont.

Nettoyage au hot-reload : puisque le kernel n'appelle pas automatiquement
`unregister_plugin()` pour nous, chaque plugin qui enregistre des noeuds doit
le faire lui-même dans son `on_unload()` (voir plugins/crm_app/src/main.py).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NavNode:
    id: str
    label: str
    plugin: str
    path: str | None = None
    icon: str | None = None
    parent_id: str | None = None
    order: int = 100
    permission: str | None = None


class NavRegistry:
    def __init__(self) -> None:
        self._nodes: dict[str, NavNode] = {}

    def register(self, node: NavNode) -> None:
        if node.id in self._nodes:
            raise ValueError(
                f"NavNode id en collision : '{node.id}' "
                f"(déjà déclaré par '{self._nodes[node.id].plugin}')"
            )
        self._nodes[node.id] = node

    def unregister_plugin(self, plugin_name: str) -> None:
        self._nodes = {k: v for k, v in self._nodes.items() if v.plugin != plugin_name}

    def tree(self, user_roles: set[str] | None = None) -> list[dict]:
        by_parent: dict[str | None, list[NavNode]] = {}
        for n in self._nodes.values():
            if n.permission and user_roles is not None and n.permission not in user_roles:
                continue
            parent = n.parent_id if n.parent_id in self._nodes else None
            by_parent.setdefault(parent, []).append(n)

        def build(pid: str | None) -> list[dict]:
            children = sorted(by_parent.get(pid, []), key=lambda n: (n.order, n.label))
            return [
                {
                    "id": n.id,
                    "label": n.label,
                    "path": n.path,
                    "icon": n.icon,
                    "children": build(n.id),
                }
                for n in children
            ]

        return build(None)


registry = NavRegistry()
