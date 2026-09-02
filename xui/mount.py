"""Dispatcher de page XUI (docs/spec-v1.md §5) — adapté à un rendu par
fichiers Jinja2 (microframe) plutôt qu'à des builders Python (`ui.page(...)`).

Différence assumée avec la spec d'origine : `mount_ui(ui_module=...)`
scannait un module Python à la recherche d'une fonction `*_page` (une
convention implicite). Ici chaque appel à `mount_xui_page()` déclare UNE
route explicitement — cohérent avec le principe central de la spec
("chaque interaction est une route HTTP explicite", §0.5/§6/§15) plutôt
qu'une résolution par nommage.

Aucun dispatcher générique de mutation ici : une page XUI ne fait que du
GET/rendu. Les formulaires pointent vers une route POST déclarée séparément
par le plugin dans son propre `get_router()` (voir plugins/crm_app), exactement
comme le prescrit §6 — jamais via microframe.engine.integration.xcore.bind_engine()
(le dispatcher `<action>`/`<remote>` à URL opaque que la spec §15 interdit).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Union

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from starlette.staticfiles import StaticFiles

from .context import UIContext, UIPermissionDenied, UIRedirect
from .nav import registry as nav_registry

try:  # import différé pour ne pas forcer microframe sur un plugin mode=spa pur
    from microframe import TemplateEngine
except ImportError:  # pragma: no cover
    TemplateEngine = Any  # type: ignore[assignment,misc]

PageView = Callable[[UIContext], Union[dict, UIRedirect, Awaitable[Union[dict, UIRedirect]]]]


def _render_403(required_roles: tuple[str, ...]) -> str:
    roles = ", ".join(required_roles)
    return f"<h1>403 — Accès refusé</h1><p>Rôle(s) requis : {roles}</p>"


def _base_render_context(plugin_ctx: Any, request: Request, user: Any) -> dict:
    """Contexte auto-injecté (`nav`, `static`, `user`, `request`) — partagé
    entre `mount_xui_page` et `render_xui_template` pour qu'une route de
    mutation qui ré-affiche la même page (ex. erreurs de validation d'un
    formulaire) obtienne exactement le même contexte que le GET normal."""
    user_roles = set(user.get("roles", [])) | set(user.get("permissions", [])) if user else set()
    plugin_name = getattr(plugin_ctx, "name", "")
    return {
        "user": user,
        "nav": nav_registry.tree(user_roles),
        "request": request,
        "static": lambda path: f"/plugins/{plugin_name}/static/{path}",
    }


async def render_xui_template(
    engine: "TemplateEngine",
    template: str,
    plugin_ctx: Any,
    request: Request,
    user: Any,
    extra: dict | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Ré-affiche un template XUI en dehors du flux `mount_xui_page` normal —
    typiquement depuis une route POST qui doit remontrer la même page avec
    des erreurs de validation (`xui.forms.parse_form`) plutôt que rediriger.
    """
    ctx_dict = _base_render_context(plugin_ctx, request, user)
    ctx_dict.update(extra or {})
    html = await engine.render(template, ctx_dict)
    return HTMLResponse(html, status_code=status_code)


def mount_xui_page(
    router: APIRouter,
    plugin_ctx: Any,
    engine: "TemplateEngine",
    *,
    path: str,
    template: str,
    view: PageView,
    login_path: str = "/login",
) -> None:
    """Monte UNE page server-rendue sur `path`.

    Toujours GET (+ HEAD, gratuit avec) — pas de paramètre `methods` à
    élargir par erreur (docs/XUI_EVOLUTION_ROADMAP.md §12.1 : "le rendu
    d'une page doit rester une opération de lecture"). Une mutation reste
    une route POST explicite déclarée à côté, jamais un `mount_xui_page`
    avec `methods=("GET", "POST")`.

    `view(ctx)` reçoit un `UIContext` déjà résolu (utilisateur, services) et
    retourne soit un dict de contexte de template, soit un `UIRedirect`.
    Le rendu délègue à `engine.render(template, ctx_dict)` — donc à
    `ComponentRegistry`/`<component.x>` pour les sous-composants partagés.

    `nav` (l'arbre de `NavRegistry` filtré par les rôles de l'utilisateur
    courant) est injecté automatiquement dans le contexte de template, sans
    que chaque vue ait à le recalculer.

    C'est la seule entrée de xui qui exige xcore à l'appel (pas à l'import) :
    `_resolve_user` est importé paresseusement depuis `xcore.kernel.api.rbac`
    à l'intérieur de la fonction. Le reste du SDK (composants, CSRF, forms,
    mounts statics) fonctionne sans xcore.
    """
    from .context import resolve_user_or_anonymous

    @router.api_route(path, methods=["GET", "HEAD"], response_class=HTMLResponse)
    async def render_page(request: Request):
        user = await resolve_user_or_anonymous(request)

        ui_ctx = UIContext(plugin_ctx=plugin_ctx, request=request, user=user)
        try:
            result = view(ui_ctx)
            if hasattr(result, "__await__"):
                result = await result
        except UIPermissionDenied as exc:
            if user is None:
                return RedirectResponse(f"{login_path}?next={request.url.path}", status_code=303)
            return HTMLResponse(_render_403(exc.required_roles), status_code=403)

        if isinstance(result, UIRedirect):
            return RedirectResponse(result.path, status_code=result.code)

        return await render_xui_template(engine, template, plugin_ctx, request, user, extra=result)


def mount_builtin_assets(app: "FastAPI", url_prefix: str = "/xui-static") -> None:
    """Sert les assets statiques livrés avec le SDK (`xui/static/` — CSS/JS
    vendorés pour les composants `<ui.x>` du package, voir
    `xui/static/cotton-ui/NOTICE.md`). Un seul appel au niveau app, comme
    `mount_template_static` de microframe pour les assets du projet
    consommateur ; les deux coexistent sous des préfixes différents.
    """
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount(url_prefix, StaticFiles(directory=str(static_dir)), name="xui-static")


def mount_plugin_static(router: APIRouter, static_dir: Path, url_path: str = "/static") -> None:
    """Monte le dossier statique propre à CE plugin, sous son propre routeur.

    Atterrit automatiquement sous `/plugins/<name>/static/...` grâce au
    préfixage déjà appliqué par le kernel à chaque `get_router()` — aucune
    collision possible entre plugins, contrairement au dossier
    `templates/static/` partagé (servi par `mount_template_static` côté app).
    Silencieux si `static_dir` n'existe pas encore (plugin sans assets).
    """
    static_dir = Path(static_dir).resolve()
    if static_dir.is_dir():
        router.mount(url_path, StaticFiles(directory=str(static_dir)), name="plugin-static")


def mount_spa(router: APIRouter, dist_dir: Path) -> None:
    """Sert un build SPA statique déjà compilé (docs/spec-v1.md §5/§14) —
    zéro dépendance à microframe ou à `xui.context`. Toute route API doit
    être déclarée sur `router` AVANT cet appel : le fallback `{full_path}`
    capture tout ce qui n'a pas déjà matché une route plus spécifique.
    """
    dist_dir = Path(dist_dir).resolve()
    if not dist_dir.exists():
        raise FileNotFoundError(f"dist_dir introuvable : {dist_dir} — build requis avant packaging")

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        router.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    index_path = dist_dir / "index.html"

    @router.get("/{full_path:path}", response_class=HTMLResponse)
    async def spa_fallback(full_path: str):
        return FileResponse(index_path)


_PROXY_EXCLUDED_REQUEST_HEADERS = {"host", "content-length"}
_PROXY_EXCLUDED_RESPONSE_HEADERS = {"content-length", "transfer-encoding", "connection"}
_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


def mount_dev_proxy(router: APIRouter, dev_server: str) -> None:
    """Reverse-proxy tout ce qui atterrit sur ce routeur vers un dev server
    front vivant (Vite/webpack --host, docs/spec-v1.md §2.1 `ui.dev_server`)
    au lieu de servir un `dist/` pré-compilé — évite un rebuild à chaque
    changement pendant le développement d'un plugin `mode: spa`.

    HTTP seulement : pas de proxy des upgrades WebSocket. Le client Vite HMR
    ouvre une connexion WS pour recevoir les mises à jour — elle ne passera
    pas par ici. Le rechargement à chaud ne fonctionnera donc pas tel quel ;
    seul le service des fichiers/requêtes HTTP classiques est proxifié. Un
    vrai proxy WS est un morceau nettement plus gros, volontairement hors
    scope (même logique que §16 : ne pas construire par anticipation).
    """
    import httpx

    client = httpx.AsyncClient(base_url=dev_server.rstrip("/"))

    @router.api_route("/{full_path:path}", methods=_PROXY_METHODS)
    async def proxy(full_path: str, request: Request):
        body = await request.body()
        headers = {
            k: v for k, v in request.headers.items() if k.lower() not in _PROXY_EXCLUDED_REQUEST_HEADERS
        }
        # `query=b""` forcerait un `?` littéral même sans query string —
        # certains serveurs (dont http.server) le voient comme un chemin
        # différent. On n'ajoute le composant query que s'il existe vraiment.
        url_kwargs: dict = {"path": f"/{full_path}"}
        if request.url.query:
            url_kwargs["query"] = request.url.query.encode("utf-8")
        upstream_req = client.build_request(
            request.method,
            httpx.URL(**url_kwargs),
            headers=headers,
            content=body,
        )
        upstream_resp = await client.send(upstream_req, stream=True)

        async def _stream():
            async for chunk in upstream_resp.aiter_raw():
                yield chunk
            await upstream_resp.aclose()

        resp_headers = {
            k: v for k, v in upstream_resp.headers.items() if k.lower() not in _PROXY_EXCLUDED_RESPONSE_HEADERS
        }
        return StreamingResponse(_stream(), status_code=upstream_resp.status_code, headers=resp_headers)


def mount_spa_or_proxy(
    router: APIRouter,
    *,
    dist_dir: Path | None = None,
    dev_server: str | None = None,
) -> None:
    """Bascule entre les deux modes `spa` du manifeste (§2.1) : `dev_server`
    (proxy vers un serveur de dev vivant) si présent, sinon `dist_dir`
    (build statique pré-compilé)."""
    if dev_server:
        mount_dev_proxy(router, dev_server)
    elif dist_dir is not None:
        mount_spa(router, dist_dir)
    else:
        raise ValueError("mount_spa_or_proxy : dist_dir ou dev_server requis")
