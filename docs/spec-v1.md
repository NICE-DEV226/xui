# XUI — Spécification technique v1

*Décision actée : suppression complète du dispatcher batch générique et du bus d'événements local pub/sub. Chaque action passe par un appel réseau explicite, individuel, vérifié par le pipeline middleware existant. Simplicité et surface d'attaque réduite priment sur l'optimisation de transport.*

---

## 0. Principes fondateurs

1. **XUI est un plugin SDK, jamais du kernel.** Rien dans `xcore/kernel/` ne doit connaître XUI. Le kernel expose des contrats génériques (router, auth, permissions, events) ; XUI les consomme comme n'importe quel framework frontend externe.
2. **Le serveur est la seule source de vérité pour la sécurité.** Aucune décision d'affichage côté client (rôle, permission, tenant) n'est jamais un substitut à la vérification serveur. Le client peut cacher un bouton ; il ne protège jamais une route.
3. **Un seul système d'auth, deux façades.** `AuthBackend` / `RBACChecker` / `get_current_user` du kernel servent à la fois les routes API pures et les pages XUI. Pas de logique RBAC dupliquée.
4. **Compatible par construction avec tout frontend externe.** XUI ne doit jamais être un prérequis. Un plugin React/Vue/Svelte pur doit fonctionner sans importer un seul module `xui`.
5. **Chaque appel réseau est explicite, tracé, et passe par le pipeline de sécurité complet** (`PermissionMiddleware`, `RateLimitMiddleware`, `RetryMiddleware`, `TracingMiddleware`) — aucun raccourci "optimisé" qui contournerait un de ces maillons.

---

## 1. Architecture globale

```
Browser
   │  HTTP (form POST / fetch JSON) — 1 requête = 1 action
   │  WS (optionnel, server→client uniquement, jamais de décision de sécurité dessus)
   ▼
FastAPI app (xcore)
   │
   ├── Router système (kernel/api/router.py)         → /plugins/{name}/ipc/{action}
   ├── Router par plugin (get_router())               → /plugins/{name}/...  OU  mount_path custom
   │        │
   │        ├── mode=xui  → pages server-rendered (SDK xui)
   │        ├── mode=spa  → StaticFiles + fallback index.html (React/Vue/Svelte build)
   │        └── mode=hybrid → mix des deux, routes déclarées explicitement
   │
   └── PluginSupervisor.call() → pipeline middlewares → LifecycleManager.call() → plugin.handle()
```

Aucune couche de transport supplémentaire entre le navigateur et `PluginSupervisor.call()`. Le formulaire XUI fait un `POST` classique ou un `fetch()` JSON standard vers une route déclarée par le plugin — rien de plus.

---

## 2. Packaging — structure d'un plugin avec UI

```
plugins/<name>/
├── plugin.yaml
├── src/
│   └── main.py              # Plugin(TrustedBase), get_router()
└── ui/
    ├── pages/                # si mode=xui
    │   └── *.py
    ├── components/           # composants XUI réutilisables, exportables via ui.exports
    └── dist/                 # si mode=spa|hybrid — build déjà compilé (Vite/webpack/etc)
        ├── index.html
        └── assets/
```

### 2.1 Extension du manifeste (`manifest_schema.json`)

```json
"ui": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "mode": { "type": "string", "enum": ["xui", "spa", "hybrid", "none"], "default": "none" },
    "mount_path": { "type": "string", "description": "override du /plugins/<name>/ par defaut" },
    "dist_dir": { "type": "string", "default": "ui/dist" },
    "dev_server": { "type": "string", "description": "URL proxy en dev, ex http://localhost:5173" },
    "package_id": { "type": "string", "pattern": "^[a-z][a-z0-9]*(\\.[a-z][a-z0-9]*)+$" },
    "exports": { "type": "array", "items": { "type": "string" } },
    "packages": { "type": "array", "items": { "type": "string" } }
  }
}
```

- `package_id` : identifiant reverse-domain (`com.xcore.auth`) si ce plugin exporte des composants UI réutilisables par d'autres plugins.
- `exports` : liste des noms de composants exportés sous ce `package_id`.
- `packages` : liste des `package_id` externes dont ce plugin dépend pour son UI (résolu au boot, cf. §7).

Ceci reste dans `manifest.extra["ui"]` tant que non promu dans `PluginManifest` (comme `ephemeral:` aujourd'hui).

---

## 3. Kernel — ajouts nécessaires (liste exhaustive)

| Ajout | Fichier | Nature |
|---|---|---|
| `plugin_dir` dans `PluginContext` | `kernel/api/context.py` | champ manquant, requis pour `mount_ui()` |
| `NavRegistry` | `kernel/ui/nav.py` (nouveau module) | registre arbre de navigation |
| `nav: NavRegistry` dans `KernelContext` | `kernel/context.py` | wiring |
| `UIPackageRegistry` | `kernel/ui/packages.py` (nouveau) | registre des exports UI cross-plugin |
| `ui_packages: UIPackageRegistry` dans `KernelContext` | `kernel/context.py` | wiring |
| Résolution `ui.packages` dans le graphe topologique | `kernel/runtime/loader.py::_topo_sort` | extension — échec explicite au boot si dépendance UI manquante |
| `mount_path` custom dans l'attache des routers | `xcore/__init__.py::_attach_router` | override du prefix `/plugins/<name>/` |
| Validation anti-collision `mount_path` | `xcore/__init__.py::boot` | avant montage, comparer tous les `mount_path` résolus |
| WS `/plugins/{name}/live` sécurisé | `kernel/api/router.py` | server→client push uniquement |
| `CSRFMiddleware` | `kernel/api/middlewares/csrf.py` (nouveau) | protège les routes cookie-auth mutatives |
| `unregister_plugin()` sur `NavRegistry`/`UIPackageRegistry` au reload | `xcore/__init__.py::_on_plugin_reloaded` | évite nav/exports zombies |

Aucun autre changement kernel n'est requis. Tout le reste (SDK, rendu HTML, composants) vit dans `xcore/sdk/xui/`.

---

## 4. `UIContext` — contexte injecté à chaque page XUI

```python
# xcore/sdk/xui/context.py
from dataclasses import dataclass
from typing import Any
from starlette.requests import Request
from xcore.kernel.api.context import PluginContext
from xcore.kernel.api.auth import AuthPayload


@dataclass
class UIContext:
    plugin_ctx: PluginContext
    request: Request
    user: AuthPayload | None

    def get_service(self, name: str) -> Any:
        return self.plugin_ctx.get_service(name)

    async def call_plugin(self, plugin: str, action: str, payload: dict | None = None) -> dict:
        return await self.plugin_ctx.caller(plugin, action, payload or {}, caller=self.plugin_ctx.name)

    # RBAC — même AuthPayload que get_current_user / RBACChecker
    def has_role(self, *roles: str) -> bool:
        if self.user is None:
            return False
        granted = set(self.user.get("roles", [])) | set(self.user.get("permissions", []))
        return bool(granted & set(roles))

    def require_role(self, *roles: str) -> None:
        if not self.has_role(*roles):
            raise UIPermissionDenied(roles)

    def redirect(self, path: str, code: int = 303) -> "UIRedirect":
        return UIRedirect(path, code)


class UIPermissionDenied(Exception):
    def __init__(self, required_roles): self.required_roles = required_roles


@dataclass
class UIRedirect:
    path: str
    code: int = 303
```

Résolution de l'utilisateur : réutilisation stricte de `_resolve_user()` déjà présent dans `kernel/api/rbac.py` — aucune réimplémentation.

---

## 5. Dispatcher de page — `mount_ui()`

```python
# xcore/sdk/xui/mount.py
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from xcore.kernel.api.rbac import _resolve_user
from .context import UIContext, UIRedirect, UIPermissionDenied
from .render import render_to_html, render_403


def mount_ui(router: APIRouter, ctx, *, ui_module: str | None = None, path: str = "/") -> None:
    ui_cfg: dict = getattr(ctx, "config", {}).get("ui", {})
    mode = ui_cfg.get("mode", "none")

    if mode == "none":
        return
    if mode == "xui":
        _mount_xui(router, ctx, ui_module, path)
    elif mode in ("spa", "hybrid"):
        _mount_spa(router, ctx, ui_cfg)
    else:
        raise ValueError(f"ui.mode inconnu: {mode!r}")


def _mount_xui(router: APIRouter, plugin_ctx, ui_module: str, path: str) -> None:
    import importlib
    mod = importlib.import_module(ui_module)
    page_fn = next(v for k, v in vars(mod).items() if k.endswith("_page"))

    @router.get(path, response_class=HTMLResponse)
    async def render_page(request: Request):
        try:
            user = await _resolve_user(request)
        except Exception:
            user = None

        ui_ctx = UIContext(plugin_ctx=plugin_ctx, request=request, user=user)
        try:
            result = page_fn(ui_ctx)
        except UIPermissionDenied as e:
            if user is None:
                return RedirectResponse(f"/auth/login?next={request.url.path}", status_code=303)
            return HTMLResponse(render_403(e.required_roles), status_code=403)

        if isinstance(result, UIRedirect):
            return RedirectResponse(result.path, status_code=result.code)
        return HTMLResponse(render_to_html(result))


def _mount_spa(router: APIRouter, plugin_ctx, ui_cfg: dict) -> None:
    plugin_dir: Path = plugin_ctx.plugin_dir
    dist = (plugin_dir / ui_cfg.get("dist_dir", "ui/dist")).resolve()
    if not dist.exists():
        raise FileNotFoundError(f"dist_dir introuvable: {dist} — build requis avant packaging")

    router.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    index_path = dist / "index.html"

    @router.get("/{full_path:path}", response_class=HTMLResponse)
    async def spa_fallback(full_path: str):
        return FileResponse(index_path)
```

**Règle stricte de résolution des chemins** : toute route API (`/api/...`) doit être déclarée **avant** l'appel à `mount_ui()` dans `get_router()`, puisque le fallback SPA capture `/{full_path:path}` en dernier recours. `mount_ui()` ne doit jamais être appelé en premier dans une fonction `get_router()` mixte.

---

## 6. Soumission de formulaire XUI — action = route classique, pas de dispatcher

Une action déclenchée depuis une page XUI (bouton, formulaire) pointe vers une **URL réelle**, exactement comme une app serveur traditionnelle. Pas d'abstraction `ActionDescriptor`, pas de bus d'événements.

```python
def contacts_page(ctx: UIContext):
    ctx.require_role("sales.view")
    db = ctx.get_service("db")
    contacts = await db.execute("SELECT * FROM contacts")
    return ui.page(
        title="Contacts",
        children=[
            ui.table(rows=contacts, columns=["name", "email"]),
            ui.form(
                action="/plugins/crm_app/contacts/new",   # route réelle déclarée dans get_router()
                method="POST",
                children=[
                    ui.input(name="name", label="Nom"),
                    ui.input(name="email", label="Email"),
                    ui.button("Créer", type="submit"),
                ],
            ),
        ],
    )
```

```python
def get_router(self):
    router = APIRouter()

    @router.post("/contacts/new")
    async def create_contact(request: Request):
        form = await request.form()
        user = await _resolve_user(request)  # même mécanisme que get_current_user
        ui_ctx = UIContext(plugin_ctx=self.ctx, request=request, user=user)
        ui_ctx.require_role("sales.create")

        db = self.get_service("db")
        await db.execute("INSERT INTO contacts (name, email) VALUES (%s, %s)",
                          (form["name"], form["email"]))
        return RedirectResponse("/plugins/crm_app/contacts", status_code=303)

    mount_ui(router, self.ctx, ui_module="ui.pages.contacts", path="/contacts")
    return router
```

Pour un rendu partiel (rafraîchir juste un fragment sans recharger toute la page), le plugin déclare **une route dédiée** qui renvoie un fragment HTML, appelée par un `fetch()` explicite écrit par le développeur du plugin, sans runtime générique imposé :

```python
@router.get("/contacts/_table")
async def contacts_table_fragment(request: Request):
    ...
    return HTMLResponse(render_to_html(ui.table(rows=contacts, columns=[...])))
```

```html
<button onclick="fetch('/plugins/crm_app/contacts/_table').then(r=>r.text()).then(h=>{
  document.getElementById('contacts-table').outerHTML = h;
})">Rafraîchir</button>
```

Ce `fetch()` est écrit par le plugin lui-même — aucun runtime JS partagé, aucun format d'action générique, aucune surface d'attaque transverse.

---

## 7. Navigation cross-plugin — `NavRegistry`

```python
# xcore/kernel/ui/nav.py
from dataclasses import dataclass, field


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
                f"NavNode id en collision: '{node.id}' "
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
            parent = n.parent_id if n.parent_id in self._nodes or n.parent_id is None else None
            by_parent.setdefault(parent, []).append(n)

        def build(pid):
            children = sorted(by_parent.get(pid, []), key=lambda n: (n.order, n.label))
            return [
                {"id": n.id, "label": n.label, "path": n.path, "icon": n.icon,
                 "children": build(n.id)}
                for n in children
            ]
        return build(None)
```

Route système exposée (`kernel/api/router.py`) :

```python
@router.get("/nav")
async def get_nav(user: AuthPayload = Depends(get_current_user)):
    roles = set(user.get("roles", [])) | set(user.get("permissions", []))
    return {"tree": nav_registry.tree(user_roles=roles)}
```

Consommé identiquement par XUI (appel direct process, pas de HTTP) et par tout frontend externe (`fetch("/api/nav")`).

**Filtrage** : uniquement RBAC utilisateur (`get_current_user`), jamais `PermissionEngine` (qui vérifie des capacités plugin-à-plugin, pas des rôles utilisateur — ne pas confondre les deux systèmes existants).

---

## 8. Packages UI cross-plugin — `UIPackageRegistry`

```python
# xcore/kernel/ui/packages.py
class UIPackageRegistry:
    def __init__(self) -> None:
        self._packages: dict[str, dict] = {}

    def register(self, package_id: str, plugin_name: str, exports: dict) -> None:
        if package_id in self._packages:
            raise ValueError(f"UI package '{package_id}' déjà déclaré")
        self._packages[package_id] = {"plugin": plugin_name, "exports": exports}

    def get(self, package_id: str, export_name: str):
        pkg = self._packages.get(package_id)
        if pkg is None:
            raise KeyError(
                f"UI package '{package_id}' non trouvé. "
                f"Vérifiez ui.packages dans le manifeste et l'ordre de chargement."
            )
        if export_name not in pkg["exports"]:
            raise KeyError(f"'{package_id}' n'exporte pas '{export_name}'")
        return pkg["exports"][export_name]
```

**Résolution obligatoire au boot** — extension de `_topo_sort` (`kernel/runtime/loader.py`) :

```python
def _topo_sort(manifests):
    package_owners = {
        m.extra.get("ui", {}).get("package_id"): m.name
        for m in manifests if m.extra.get("ui", {}).get("package_id")
    }
    resolver = DependencyResolver()
    for m in manifests:
        backend_deps = [d.name for d in m.requires]
        ui_pkg_ids = m.extra.get("ui", {}).get("packages", [])
        ui_deps = []
        for pkg_id in ui_pkg_ids:
            owner = package_owners.get(pkg_id)
            if owner is None:
                raise ManifestError(
                    f"[{m.name}] ui.packages référence '{pkg_id}' introuvable "
                    f"— aucun plugin ne déclare ce package_id."
                )
            ui_deps.append(owner)
        resolver.add(m.name, backend_deps + ui_deps)
    ...
```

Échec **explicite au boot**, jamais silencieux au premier accès utilisateur en prod.

**Règle d'usage** : toujours `registry.get(...)` inline au moment du rendu, jamais en import-time du module — sinon référence périmée après un hot-reload du plugin exportateur.

---

## 9. Authentification & RBAC — unifié, un seul chemin

| Contexte | Mécanisme | Source |
|---|---|---|
| Route API JSON (React, Vue, Svelte) | `Depends(RBACChecker(["role"]))` | `kernel/api/rbac.py`, inchangé |
| Page XUI server-rendered | `ctx.require_role("role")` | même `AuthPayload`, résolu via `_resolve_user()` |
| WS `/live` | vérif avant `accept()` | même `AuthBackend`, cf §11 |

Aucune réimplémentation de la logique de vérification. `UIContext.user` et le `user` injecté par `Depends(get_current_user)` proviennent strictement de la même fonction.

---

## 10. CSRF — uniquement sur les chemins cookie-authentifiés

```python
# kernel/api/middlewares/csrf.py
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cookie_auth_paths: list[str]):
        super().__init__(app)
        self._paths = cookie_auth_paths

    async def dispatch(self, request, call_next):
        if request.method in MUTATING_METHODS and any(
            request.url.path.startswith(p) for p in self._paths
        ):
            if "session" in request.cookies:
                header = request.headers.get("X-CSRF-Token")
                cookie = request.cookies.get("csrf_token")
                if not header or header != cookie:
                    return JSONResponse({"error": "csrf_invalid"}, status_code=403)
        return await call_next(request)
```

- Appliqué **uniquement** aux `mount_path` déclarés `ui.mode: xui` (cookie-based).
- **Jamais** appliqué aux routes API pures consommées via `Authorization: Bearer` (pas de cookie ambient, pas de risque CSRF).
- Tout formulaire XUI généré par `ui.form()` injecte automatiquement un champ caché `csrf_token` synchronisé avec le cookie — géré par `render.py`, jamais laissé à la charge du développeur de plugin.

---

## 11. WebSocket `/live` — push serveur→client uniquement, jamais de décision de sécurité côté client

```python
@router.websocket("/{plugin_name}/live")
async def live_updates(websocket: WebSocket, plugin_name: str, topics: str = ""):
    try:
        user = await _resolve_user_from_ws(websocket)  # cookie ou ?token= en query
    except HTTPException:
        await websocket.close(code=4401)
        return

    tenant_id = _resolve_tenant_from_ws(websocket)
    await websocket.accept()

    allowed_topics = [
        t for t in topics.split(",")
        if _user_can_subscribe(user, tenant_id, plugin_name, t)  # même RBAC que les routes API
    ]
    if not allowed_topics:
        await websocket.close(code=4403)
        return

    queue = asyncio.Queue()
    async def relay(event):
        if event.data.get("tenant_id") != tenant_id:
            return  # filtre silencieux, pas de fuite cross-tenant
        await queue.put(event)

    for t in allowed_topics:
        events_bus.subscribe(t, relay)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json({"topic": event.name, "data": event.data})
    except WebSocketDisconnect:
        pass
    finally:
        for t in allowed_topics:
            events_bus.unsubscribe(t, relay)
```

**Usage strict** : notifier le client qu'une donnée a changé (ex: "un deal a bougé") → le client refait un `fetch()` classique vers la route de fragment pour récupérer le HTML/JSON à jour. Le WS ne transporte **jamais** de HTML pré-rendu ni de décision d'autorisation — seulement un signal "va revérifier X".

---

## 12. Multi-tenance — déjà natif, à activer, pas à recoder

```yaml
tenancy:
  enabled: true
  subdomain: true
  isolate_db: true
  isolate_cache: true
  enforce_ipc: true
```

`self.get_service("db")` dans une page XUI ou un handler de plugin retourne automatiquement `TenantAwareDB` scopé — aucune isolation manuelle à écrire dans XUI. Le tenant est résolu par `TenantMiddleware` avant que toute route (XUI ou API) ne s'exécute.

---

## 13. Sécurité — checklist finale de conformité

| Point | Exigence |
|---|---|
| `tenant_id` | Jamais lu du body/payload client — toujours `request.state.tenant_id` via middleware |
| CSRF | Actif sur tout chemin cookie-authentifié mutatif, jamais sur Bearer-only |
| WS | Auth + filtre tenant/permission **avant** `accept()` |
| RBAC | Un seul chemin (`_resolve_user` + `AuthPayload`), jamais dupliqué entre XUI et API |
| Injection HTML | Tout contenu dynamique passé dans un template XUI passe par `html.escape()` centralisé dans `render.py` |
| CSP | `script-src 'self'` strict, aucun script inline généré par un plugin, seul un éventuel runtime commun est hashé |
| Rate limit / permissions | Chaque route XUI passe par le même pipeline (`RBACChecker` ou `ctx.require_role`) — aucun raccourci |
| Nav / UIPackage au reload | `unregister_plugin()` appelé sur l'event `plugin.*.reloaded` — pas de références zombies |
| Fragments HTML | Générés par une route dédiée explicite du plugin, jamais par un mécanisme générique cross-plugin |

---

## 14. Compatibilité frontend externe — contrat minimal

Un plugin React/Vue/Svelte/Angular n'a **aucune obligation** vis-à-vis de XUI :

```yaml
ui:
  mode: spa
  dist_dir: ui/dist
```

```python
def get_router(self):
    router = APIRouter()
    # routes API JSON classiques, Bearer-authentifiées
    mount_ui(router, self.ctx)  # StaticFiles + fallback index.html
    return router
```

Aucun import `xui`, aucun runtime JS imposé, aucune convention de rendu — juste un build statique servi par le kernel. Le seul point de contact optionnel avec le reste du système : consommer `GET /api/nav` pour afficher la même navigation que les autres modules.

---

## 15. Ce qui a été volontairement retiré (et pourquoi)

| Retiré | Raison |
|---|---|
| Dispatcher JS générique (`xcore.ipc`, `xcore.emit`) | Surface d'attaque transverse à tous les plugins, complexité de maintenance disproportionnée par rapport au gain |
| Endpoint `/api/ipc/batch` | Risque de contournement du rate-limiting per-request, fausse promesse d'atomicité, gestion d'erreur partielle complexe |
| `ActionDescriptor` déclaratif universel | Ajoute une couche d'indirection non nécessaire — un `<form action="...">` ou un `fetch()` explicite est plus simple à auditer |
| Bus pub/sub client-side comme mécanisme de coordination inter-widgets | Confusion quasi garantie entre "UX locale" et "décision de sécurité", risque de mauvais usage par les développeurs de plugins tiers |

Le remplacement : chaque interaction est une route HTTP explicite, écrite par le développeur du plugin, vérifiée par le pipeline middleware existant, sans abstraction de transport partagée entre plugins.

---

## 16. Plan d'implémentation (ordre recommandé)

1. `PluginContext.plugin_dir` + `mount_ui()` (SPA only, sans XUI) — valide la compatibilité frontend externe en premier.
2. `mount_path` custom + validation anti-collision au boot.
3. `UIContext` + rendu XUI minimal (`ui.page`, `ui.heading`, `ui.table`, `ui.form`) — pas de composants avancés au départ.
4. `CSRFMiddleware` — avant tout formulaire XUI en prod.
5. `NavRegistry` + route `/api/nav`.
6. `UIPackageRegistry` + résolution au boot.
7. WS `/live` sécurisé (uniquement si un cas d'usage temps réel réel se présente — ne pas construire par anticipation).

Chaque étape est testable indépendamment ; aucune ne bloque le déploiement d'un plugin SPA pur dès l'étape 2.