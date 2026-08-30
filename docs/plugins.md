# Intégrer xui dans un plugin xcore

Guide, basé sur les plugins de référence/démo du repo (`plugins/crm_app`,
`plugins/demo_auth`, `plugins/ui_kit`, `plugins/spa_demo`).

## Structure d'un plugin avec UI

Conforme à la spec `docs/spec-v1.md` §2 :

```
plugins/<name>/
├── plugin.yaml            # manifeste (dont ui.mode, ui.packages…)
├── src/main.py            # Plugin(TrustedBase), get_router()
├── static/                # assets du plugin (servis sous /plugins/<name>/static)
└── ui/dist/               # si mode=spa — build déjà compilé (index.html, assets/)
```

Le manifeste `plugin.yaml` déclare notamment `ui.mode` (`xui` | `spa` |
`hybrid` | `none`) — ici les plugins utilisent la forme live de xcore
(`trusted_backends`, `ipc`, services…). Toute route/ressource non servie par
un routeur de plugin relevant de xcore.

Le `PluginContext` installé n'expose **pas** `plugin_dir` (gap spec §3) :
chaque plugin dérive son propre chemin de `__file__` :

```python
_PLUGIN_DIR = Path(__file__).resolve().parent.parent
```

## Pages server-rendues (`mode: xui`)

### 1. Déclarer la page

```python
from xui.context import UIContext
from xui.mount import mount_xui_page, mount_plugin_static, render_xui_template
from xui.nav import NavNode
from xui.nav import registry as nav_registry

def _contacts_view(ctx: UIContext):
    ctx.require_role("sales.view")          # RBAC — même AuthPayload que l'API
    return {
        "title": "Contacts",
        "contacts": _CONTACTS,
        "can_create": ctx.has_role("sales.create"),
    }
```

Dans `get_router()` :

```python
def get_router(self) -> APIRouter:
    router = APIRouter()
    engine = self.get_service("ext.template_engine").engine  # engine partagé

    mount_plugin_static(router, _PLUGIN_DIR / "static")

    mount_xui_page(
        router, self.ctx, engine,
        path="/contacts",
        template="crm/contacts.html",
        view=_contacts_view,
        login_path="/plugins/demo_auth/login",
    )
    return router
```

- `template` est résolu dans le namespace du plugin (l'extension
  `template_engine` voit `crm → plugins/crm_app/templates` via `namespaceS`
  d'`integration.yaml`).
- `mount_xui_page` gère : `_resolve_user` → `UIContext` → `view` → rendu ;
  intercepte `UIPermissionDenied` (anonyme → 303 `/login?next=…`, sinon
  403), `UIRedirect` → RedirectResponse.

### 2. Mutation = route POST explicite

Jamais de dispatcher (`<action>`/`<remote>` est interdit, spec §15) :

```python
@router.post("/contacts/new")
async def create_contact(request: Request):
    from xcore.kernel.api.rbac import _resolve_user
    user = await _resolve_user(request)          # même mécanisme que get_current_user
    ctx = UIContext(plugin_ctx=self.ctx, request=request, user=user)
    if not ctx.has_role("sales.create"):
        return RedirectResponse("/plugins/crm_app/contacts", status_code=303)

    form = await request.form()
    result = parse_form(form, ContactCreate)      # Pydantic, ré-affichable
    if not result.ok:                             # message par champ, valeurs gardées
        return await render_xui_template(
            engine, "crm/contacts.html", self.ctx, request, user,
            extra={"errors": result.errors, "values": result.values, ...},
            status_code=422,
        )
    ...
    return RedirectResponse("/plugins/crm_app/contacts", status_code=303)
```

Le **CSRF** de cette route est validé en amont par `xui.csrf.CSRFMiddleware`
(câblé dans `main.py` sur le préfixe `/plugins/crm_app`) — une seule source
de vérité. Le formulaire porte le token via `{{ csrf_token() }}` dans un
champ caché.

### 3. Template

Le template étend le layout partagé et met les composants au travail :

```html
{% extends "layouts/page.html" %}
{% block page_title %}{{ title }}{% endblock %}
{% block page_actions %}
 <ui.button href="/plugins/crm_app/contacts/new">Nouveau</ui.button>
{% endblock %}
{% block page_content %}
  <ui.table>…contacts…</ui.table>
  <form method="post" action="/plugins/crm_app/contacts/new">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <ui.input name="name" label="Nom" value="{{ values.get('name', '') }}"/>
    {% if errors.get('name') %}<ui.error name="name" message="{{ errors.get('name') }}"/>{% endif %}
    <ui.button type="submit" variant="primary">Créer</ui.button>
  </form>
{% endblock %}
{% block scripts %}<ui.alpine/>{% endblock %}
```

## RBAC unifié

| Contexte | Mécanisme | Source |
|---|---|---|
| Route API JSON | `Depends(RBACChecker(["role"]))` | `kernel/api/rbac.py` |
| Page XUI server-rendered | `ctx.require_role("role")` | `_resolve_user` → même `AuthPayload` |
| Mutation XUI | `ctx.has_role(...)` dans la route POST | idem |

`UIContext.user` et l'utilisateur injecté par `get_current_user` proviennent
strictement de la même fonction — aucune réimplémentation (§9).

## Navigation cross-plugin

```python
async def on_load(self):
    nav_registry.register(NavNode(
        id="crm.contacts", label="Contacts", plugin=self.ctx.name,
        path="/plugins/crm_app/contacts", permission="sales.view",
    ))

async def on_unload(self):
    nav_registry.unregister_plugin(self.ctx.name)
```

L'arbre (`nav_registry.tree(user_roles)`) est injecté automatiquement dans le
contexte de template par `mount_xui_page` / `render_xui_template` — pas de
recalcul dans la vue. Utilisé par le `<nav>` de `templates/base.html`.

## Packages UI cross-plugin

Le plugin exporteur déclare un `package_id` et enregistre des callables
**à `on_load()`** :

```python
# plugins/ui_kit
PACKAGE_ID = "com.xcore.ui_kit"

async def on_load(self):
    ui_packages.register(PACKAGE_ID, self.ctx.name, {"button": button, "badge": badge})
```

Le consommateur résout **au moment du rendu** (jamais à l'import du module) :

```python
def _ui_kit_exports() -> dict:
    return {
        "ui_button": ui_packages.get("com.xcore.ui_kit", "button"),
        "ui_badge":  ui_packages.get("com.xcore.ui_kit", "badge"),
    }
```

Règle : toujours `registry.get(...)` inline dans la vue/le rendu — une
référence prise à l'import serait périmée après un hot-reload de
l'exportateur. Pas de résolution au boot (le kernel installé n'a pas le hook
`_topo_sort` UI de la spec §8) : `get()` échoue avec un message clair au
premier accès manquant.

## Auth de démo

`plugins/demo_auth` fournit un `AuthBackend` en mémoire (comptes
`alice/alice123` et `bob/bob123`) pour exercer le flux cookie authentifié :
`register_auth_backend(backend)` dans `on_load()`, sessions via cookie
`session`, routes login/logout. Remplacer ce plugin ne change rien à
`UIContext`/`get_current_user`/`RBACChecker`.

## Mode SPA (`mode: spa`) — zéro dépendance xui

Un plugin React/Vue/Svelte n'importe jamais xui (spec §14) :

```python
def get_router(self):
    router = APIRouter()
    # routes API JSON avant le fallback
    mount_spa_or_proxy(router, dist_dir=..., dev_server=...)
    return router
```

- `dist_dir` → `mount_spa` : sert `dist/assets` + fallback `index.html`
  sur `/{full_path:path}`. **Déclarer les routes API avant**, le fallback
  capte tout le reste.
- `dev_server` → `mount_dev_proxy` : reverse-proxy HTTP vers Vite/webpack
  (`--host`) en dev, sans rebuild. HTTP only : pas de WS, donc pas de HMR à
  travers lui.
- Les pages SPA peuvent ponctuellement embarquer un `<ui.alpine/>` dans leur
  `index.html` (HTML servi) pour utiliser les behaviors inline.

## Câblage côté app (non-SDK, `main.py`)

Rappel de l'ordre correct (voir `docs/architecture.md`) :

```python
app = FastAPI(lifespan=lifespan)
app.add_middleware(CSRFMiddleware, get_token=lambda: _engine().csrf_token,
                   protected_paths=["/plugins/crm_app"])
xcore.setup(app)   # avant le démarrage
```

Et dans `lifespan()` : `await xcore.boot(app)` puis `mount_template_static`
+ `mount_builtin_assets`. Ne jamais appeler `bind_engine()` /
`register_action_routes()` (dispatcher interdit §15).

## MFE (micro-frontends) — état actuel

microframe embarque un client MFE (`microframe.engine.mfe.MFEClient`,
exposé aux templates via le global `render_mfe(name, **params)`), qui
récupère des fragments HTML à la volée au rendu (les erreurs produisent un
commentaire HTML, sans casser la page). `TemplateEngine` instancie ce client
(`engine.mfe`, timeout réglable via config), mais **rien ne l'enregistre** :
le registre démarre vide, et ni xui ni un plugin ne l'alimentent. `xui/`
n'expose volontairement pas de helper MFE tant que ce besoin n'est pas acté
(voir la question ouverte en fin de `docs/architecture.md`) — un plugin qui
veut un fragment peut pour l'instant opter pour une **route de fragment
dédiée** (§ ci-dessous), conforme à la spec §6.

## Checklist sécurité

- **Tenant** : jamais lu du body — `request.state.tenant_id` (TenantMiddleware).
- **CSRF** : actif sur tout chemin cookie-authentifié mutatif ; formulaire
  avec `{{ csrf_token() }}` caché ; jamais sur les routes Bearer-only.
- **RBAC** : un seul chemin (`_resolve_user`) entre XUI et API.
- **Fragments** : une route dédiée par fragment, un `fetch()` écrit par le
  plugin — pas de mécanisme générique (§6).
- **Rebind nav/packages** : `unregister_plugin()` dans `on_unload()` — pas de
  références zombies au reload.