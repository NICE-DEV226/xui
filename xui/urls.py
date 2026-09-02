"""Déclaration de pages façon Django `urlpatterns` (docs/spec-v1.md §6/§15).

Pur sucre syntaxique au moment du montage : `mount_xui_pages` déroule la
liste UNE FOIS pendant `get_router()` et enregistre chaque route via
`mount_xui_page`, exactement comme si elles avaient été écrites à la main.
Rien de nouveau au moment d'une requête — FastAPI fait le matching comme
d'habitude. Ce n'est donc pas le dispatcher générique interdit par la spec :
`urlpatterns` ne résout jamais un chemin en dehors du routeur FastAPI lui-même,
il ne fait que réduire la répétition de `ctx`/`engine`/`login_path` communs à
toutes les pages d'un même plugin.

    urlpatterns = [
        path("/", index_view, template="landing/index.html", name="landing.index"),
        path("/pricing", pricing_view, template="landing/pricing.html", name="landing.pricing"),
    ]

    def get_router(self):
        router = APIRouter()
        mount_xui_pages(router, self.ctx, engine, urlpatterns, login_path="/plugins/demo_auth/login")
        return router
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter

from .mount import PageView, mount_xui_page

_names: dict[str, str] = {}


@dataclass(frozen=True)
class PageRoute:
    path: str
    view: PageView
    template: str
    name: str | None = None


def path(route: str, view: PageView, *, template: str, name: str | None = None) -> PageRoute:
    """Équivalent de `django.urls.path()` pour une page XUI — construit
    l'entrée, ne monte rien : le montage reste explicite via
    `mount_xui_pages()`."""
    return PageRoute(path=route, view=view, template=template, name=name)


def mount_xui_pages(
    router: APIRouter,
    ctx: Any,
    engine: Any,
    urlpatterns: list[PageRoute],
    *,
    login_path: str = "/login",
) -> None:
    """Monte chaque `PageRoute` de `urlpatterns` via `mount_xui_page`, dans
    l'ordre de la liste (important si un fallback plus permissif — ex. un
    futur mode=spa — est ajouté après coup dans le même router, cf. la règle
    de résolution de chemins de `mount_ui`)."""
    for route in urlpatterns:
        if route.name:
            if route.name in _names and _names[route.name] != route.path:
                raise ValueError(
                    f"xui.urls: nom de route '{route.name}' déjà utilisé pour "
                    f"'{_names[route.name]}' — chaque `name` doit être unique "
                    f"process-wide (comme NavNode.id)."
                )
            _names[route.name] = route.path
        mount_xui_page(
            router, ctx, engine,
            path=route.path, template=route.template, view=route.view,
            login_path=login_path,
        )


def reverse(name: str) -> str:
    """Équivalent minimal de `django.urls.reverse()` — pas de paramètres de
    chemin dynamiques (`<int:id>`) pour l'instant, seulement les routes
    statiques déclarées via `path(..., name=...)`."""
    try:
        return _names[name]
    except KeyError:
        raise KeyError(
            f"xui.urls.reverse: aucune route nommée '{name}' — "
            f"vérifie qu'elle est déclarée avec `name=` et que "
            f"`mount_xui_pages()` a bien tourné avant cet appel."
        ) from None
