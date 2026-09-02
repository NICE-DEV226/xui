"""Montage d'un thème Tailwind custom pour toutes les pages XUI.

Un thème est un simple fichier CSS qui redéfinit des variables déjà
déclarées par `cotton-ui.tokens.css` (`--color-accent`, `--radius-control`,
etc.) : les classes utilitaires du kit les lisent via `var(...)`, donc les
redéfinir suffit à re-thémer sans build Tailwind — mais ça ne fait
jamais apparaître de nouvelle classe utilitaire absente du bundle figé
(voir `xui/static/cotton-ui/NOTICE.md`).

Enregistré comme un global Jinja2 (comme `csrf_token`/`static`), pas passé
dans le contexte de chaque page : un composant (`<ui.x>`) est rendu depuis
une template isolée par `ComponentExtension._render_async`
(microframe/engine/components/extension.py) — il ne voit que ses props et
les globals de l'environnement, jamais les variables de la page qui
l'inclut. Un thème étant un réglage process-wide (pas par-requête), c'est
exactement la bonne case.

Route dédiée (`FileResponse`) plutôt qu'un `StaticFiles` sur un dossier :
le fichier est résolu à chaque requête, pas vérifié une seule fois au
boot — voir la discussion sur `mount_template_static` qui saute son
montage si le dossier n'existe pas encore au démarrage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse


def mount_theme(
    app: FastAPI,
    engine: Any,
    css_path: str | Path,
    url_path: str = "/xui-theme/theme.css",
) -> None:
    """Monte un fichier de thème CSS et le rend disponible à `<ui.theme/>`
    dans tout layout qui l'inclut.

    À appeler une fois au niveau app (comme `mount_builtin_assets`), APRÈS
    lui dans l'ordre des appels — `<ui.theme/>` doit aussi être placé
    APRÈS `<ui.xui/>` dans le `<head>` du layout : l'ordre des `<link>`
    doit suivre l'ordre de montage pour que la cascade CSS donne raison au
    thème sur les tokens par défaut de cotton-ui.
    """
    css_path = Path(css_path).resolve()
    if not css_path.is_file():
        raise FileNotFoundError(f"mount_theme: fichier introuvable: {css_path}")

    @app.get(url_path, include_in_schema=False)
    async def _serve_xui_theme() -> FileResponse:
        return FileResponse(css_path)

    engine.env.globals["xui_theme_url"] = url_path
