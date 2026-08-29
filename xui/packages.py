"""UIPackageRegistry — partage de composants UI entre plugins.

Même situation que nav.py : la spec (docs/spec-v1.md §8) le place sur
`KernelContext` avec résolution des dépendances au boot (`_topo_sort`). Le
vrai kernel installé n'a ni ce slot ni cette résolution, donc c'est un
singleton de module ici — un plugin qui exporte des composants les enregistre
dans `on_load()`, un plugin consommateur les résout via `registry.get(...)`
**au moment du rendu**, jamais à l'import du module (sinon référence périmée
après un hot-reload du plugin exportateur — voir spec §8, dernière règle).

Contrairement à la spec, il n'y a pas de vérification "explicite au boot" des
dépendances `ui.packages` ici : sans hook kernel sur l'ordre de chargement des
plugins, on ne peut pas garantir qu'un exportateur est chargé avant son
consommateur. `get()` échoue donc avec un message clair au premier accès
manquant plutôt qu'au boot — c'est un vrai recul par rapport à la spec, à
combler le jour où `UIPackageRegistry` est réellement wiré dans le kernel.
"""

from __future__ import annotations

from typing import Any


class UIPackageRegistry:
    def __init__(self) -> None:
        self._packages: dict[str, dict[str, Any]] = {}

    def register(self, package_id: str, plugin_name: str, exports: dict[str, Any]) -> None:
        if package_id in self._packages:
            raise ValueError(f"UI package '{package_id}' déjà déclaré")
        self._packages[package_id] = {"plugin": plugin_name, "exports": exports}

    def get(self, package_id: str, export_name: str) -> Any:
        pkg = self._packages.get(package_id)
        if pkg is None:
            raise KeyError(
                f"UI package '{package_id}' non trouvé. "
                "Vérifiez que le plugin exportateur est bien chargé "
                "(et chargé avant le consommateur)."
            )
        if export_name not in pkg["exports"]:
            raise KeyError(f"'{package_id}' n'exporte pas '{export_name}'")
        return pkg["exports"][export_name]

    def unregister_plugin(self, plugin_name: str) -> None:
        self._packages = {k: v for k, v in self._packages.items() if v["plugin"] != plugin_name}


registry = UIPackageRegistry()
