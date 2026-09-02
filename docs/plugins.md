# Intégrer xui dans un plugin xcore

Guide autonome : extraits à copier/coller dans le `src/main.py` d'un plugin
(`Plugin(TrustedBase)`, `get_router()`), adaptés de ce que faisaient les
plugins de démo retirés du repo.

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

Dans `get_router()` (app démo = `main.py`, plugin = `src/main.py`) — un
plugin à une seule page peut appeler `mount_xui_page` directement, mais dès
qu'il y en a plusieurs, `xui.urls` évite de répéter `ctx`/`engine`/
`login_path` à chaque route (façon `django.urls.path()`, sans dispatcher :
`mount_xui_pages` déroule la liste UNE FOIS au montage, chaque route reste
un `mount_xui_page` normal, FastAPI route comme d'habitude) :

```python
from xui.urls import path as xui_path, mount_xui_pages, reverse

urlpatterns = [
    xui_path("/contacts", _contacts_view, template="crm/contacts.html", name="crm.contacts"),
]

def get_router(self) -> APIRouter:
    router = APIRouter()
    engine = self.get_service("ext.template_engine").engine  # engine partagé

    mount_plugin_static(router, _PLUGIN_DIR / "static")
    mount_xui_pages(router, self.ctx, engine, urlpatterns, login_path="/plugins/demo_auth/login")
    return router
```

- `template` est résolu dans le `directory` du `template_engine` (ou un
  `namespaces` déclaré dans `integration.yaml` si le plugin veut isoler ses
  propres templates).
- `mount_xui_page`/`mount_xui_pages` gèrent : `_resolve_user` → `UIContext`
  → `view` → rendu ; interceptent `UIPermissionDenied` (anonyme → 303
  `/login?next=…`, sinon 403), `UIRedirect` → RedirectResponse.
- `name="crm.contacts"` alimente `reverse("crm.contacts")` → `/plugins/crm_app/contacts`
  (équivalent minimal de `django.urls.reverse()`, pas de segments
  dynamiques pour l'instant) — collision de nom détectée à `mount_xui_pages()`,
  remonter les mêmes `urlpatterns` deux fois (hot-reload) est sans effet.

### 2. Mutation = route POST explicite

Jamais de dispatcher (`<action>`/`<remote>` est interdit, spec §15) :

```python
@router.post("/contacts/new")
async def create_contact(request: Request):
    user = await resolve_user_or_anonymous(request)  # jamais un except Exception: user = None —
    ctx = UIContext(plugin_ctx=self.ctx, request=request, user=user)  # voir plus bas pourquoi
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
(câblé dans `main.py` sur le préfixe du plugin, ex. `/plugins/crm_app`) —
une seule source de vérité. Le formulaire porte le token via `<ui.form>`
(§10), qui l'injecte automatiquement : pas de
`<input type="hidden" name="csrf_token">` à écrire à la main.

**Pourquoi `resolve_user_or_anonymous` et pas `try: ... except Exception: user = None`**
(vu deux fois dans ce repo avant correctif) : `_resolve_user` peut lever un
`503` si le backend d'auth n'est pas chargé — une vraie panne, pas un
visiteur anonyme. Un `except Exception` généralisé les confond toutes les
deux en `user = None`, rendant la panne invisible (elle se comporte comme
"non connecté" au lieu de remonter comme erreur serveur). `xui.context.resolve_user_or_anonymous`
ne convertit en anonyme que le `401` (token absent/invalide/expiré,
légitimement anonyme) — tout le reste remonte tel quel
(docs/XUI_EVOLUTION_ROADMAP.md §12.2).

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
  <ui.form action="/plugins/crm_app/contacts/new">
    <ui.input name="name" label="Nom" value="{{ values.get('name', '') }}"/>
    {% if errors.get('name') %}<ui.error message="{{ errors.get('name') }}"/>{% endif %}
    <ui.button type="submit" variant="primary">Créer</ui.button>
  </ui.form>
{% endblock %}
{% block scripts %}<ui.alpine/>{% endblock %}
```

`<ui.form>` (`xui/components/form.html`) injecte le champ caché
`csrf_token` lui-même (sauf sur `method="get"`, rien à protéger) via
`csrf_token()` comme global Jinja2 — accessible même si le composant est
rendu depuis une template isolée (voir `docs/architecture.md`, "Composants
`<ui.x>`"). `method="post"` est son défaut, inutile de le répéter.

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

### Navigation sans rechargement complet (`<ui.xuiboost/>`)

Posé une fois dans `templates/base.html` (`xui/static/xui-boost.js`) : il
intercepte les clics sur les liens internes marqués `data-xui-nav-link`,
fait un `fetch()` vers la **même route réelle** qu'un clic normal aurait
suivie, extrait `#xui-main` de la réponse et remplace juste ce nœud —
sidebar/header ne bougent pas, l'URL se met à jour via
`history.pushState(..., res.url)` (suit les redirections : un lien vers une
page protégée pendant qu'on est déconnecté affiche bien `/login`, pas
l'ancienne URL). Aucune route n'existe pour ce mécanisme spécifiquement —
sans JS (ou si le `fetch()` échoue), le lien redevient une navigation
normale. Toujours conforme à §15 : c'est le navigateur qui ferait le même
GET, juste demandé par `fetch()` plutôt qu'un clic direct.

Un plugin avec son propre layout n'a qu'à ne pas inclure `<ui.xuiboost/>`.

## Packages UI cross-plugin

Le plugin exporteur déclare un `package_id` et enregistre ses exports
**à `on_load()`** — exemple réel du repo (`plugins/ui_kit`), un vocabulaire
de statuts (couleur+libellé) partagé entre `billing` et `tasks` plutôt que
dupliqué dans chacun :

```python
# plugins/ui_kit/src/main.py — export-only, aucune route propre
PACKAGE_ID = "xui.ui_kit"
STATUS_STYLES = {"paid": {"color": "emerald", "label": "Payée"}, ...}

class Plugin(TrustedBase):
    async def on_load(self) -> None:
        ui_packages.register(PACKAGE_ID, self.ctx.name, {"status_styles": STATUS_STYLES})

    async def on_unload(self) -> None:
        ui_packages.unregister_plugin(self.ctx.name)
```

Le consommateur résout **au moment du rendu**, jamais à l'import du module
(une référence prise à l'import serait périmée après un hot-reload de
l'exportateur) :

```python
# plugins/billing/src/main.py
def _invoices_view(ctx: UIContext):
    ctx.require_role("billing.view")
    styles = ui_packages.get("xui.ui_kit", "status_styles")  # inline, dans la vue
    return {"invoices": _INVOICES, "styles": styles}
```

```yaml
# plugins/billing/plugin.yaml
requires:
  - ui_kit
```

L'ordre de chargement (`ui_kit` avant `billing`) est garanti par le
`requires:` **du vrai kernel** (graphe de dépendances backend, générique —
pas un hook `_topo_sort` spécifique aux packages UI comme l'imaginait la
spec §8) : vérifié en pratique, le kernel charge par vagues successives
(`ui_kit` d'abord, `billing`/`tasks` ensuite). `UIPackageRegistry` lui-même
ne vérifie toujours rien au boot — c'est `requires:` qui protège
`get()`, pas le registre — donc un exportateur oublié dans `requires:`
échoue seulement au premier accès manquant, avec un message clair.

## Auth de démo

Un plugin `demo_auth` fournit un `AuthBackend` en mémoire (comptes
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
                   protected_paths=["/plugins/<plugin>"])
app.add_middleware(SecurityHeadersMiddleware, report_only=True)  # CSP souple (xui/security.py)
xcore.setup(app)   # avant le démarrage
```

Et dans `lifespan()` : `await xcore.boot(app)` puis `mount_template_static`
+ `mount_builtin_assets` (+ `mount_theme(app, engine, "templates/static/theme.css")`
si le projet a un thème custom, voir plus bas). Ne jamais appeler
`bind_engine()` / `register_action_routes()` (dispatcher interdit §15).

### Thème custom (`xui.theme.mount_theme`)

`cotton-ui.css` (vendoré, `xui/static/`) est un Tailwind v4 **pré-compilé,
figé** — aucun build à faire pour l'utiliser tel quel, mais aussi aucune
classe au-delà de celles déjà utilisées par les composants portés (voir
`docs/architecture.md`). Un projet qui veut ses propres tokens
(`--color-brand-*`, une police, des rayons différents) ou ses propres
classes structurelles (`base.html`, layouts) a besoin d'un **vrai build
Tailwind** — pas de Node/npm requis, le CLI standalone officiel suffit
(`make css`/`make theme`, voir le `makefile` : télécharge
`tailwindcss-linux-x64` depuis les releases GitHub `tailwindlabs/tailwindcss`
si absent, checksum vérifiable via `sha256sums.txt`).

```python
mount_theme(app, engine, "templates/static/theme.css")  # sortie compilée, pas la source
```

`mount_theme` sert le fichier via une route dédiée (`FileResponse`, résolue
par requête — pas un `StaticFiles` qui exigerait le dossier au boot) et
enregistre son URL comme global Jinja2 (`xui_theme_url`), consommé par
`<ui.theme/>` — un composant n'a accès à aucune variable de la page qui
l'inclut (voir `docs/architecture.md`, "Composants `<ui.x>`"), donc un
thème (réglage process-wide) passe par un global, pas par le contexte de
rendu.

**Piège vérifié en pratique** : `@theme { --color-x: ... }` dans la
SOURCE ne suffit pas — Tailwind v4 élague par défaut les variables non
référencées par une classe présente dans les fichiers scannés (`@source`).
Sans classe qui les utilise déjà, `@theme static { ... }` force leur
émission.

**Autre piège** : le `dark:` de `cotton-ui.css` (vendoré) est **par
classe** (`:where(.dark, .dark *):not(:where(.light, .light *))` —
`<ui.mode_toggle/>` bascule `.dark` sur `<html>`). Un build de thème projet
qui ne déclare pas la même règle retombe sur `@media
(prefers-color-scheme: dark)` par défaut — les deux CSS doivent s'accorder,
sinon le switch de thème ne change que la moitié de la page :

```css
@custom-variant dark (&:where(.dark, .dark *):not(&:where(.light, .light *)));
```

## MFE (micro-frontends) — état actuel

microframe embarque un client MFE (`microframe.engine.mfe.MFEClient`,
exposé aux templates via le global `render_mfe(name, **params)`), qui
récupère des fragments HTML à la volée au rendu (les erreurs produisent un
commentaire HTML, sans casser la page). `TemplateEngine` instancie ce client
(`engine.mfe`, timeout réglable via config), mais **rien ne l'enregistre** :
le registre démarre vide, et ni xui ni un plugin ne l'alimentent. `xui/`
n'expose volontairement pas de helper MFE tant que ce besoin n'est pas acté
(voir la section MFE de `docs/architecture.md`) — un plugin qui veut un
fragment peut pour l'instant opter pour une **route de fragment dédiée**
(§ ci-dessous, spec §6).

## Checklist sécurité

- **Tenant** : jamais lu du body — `request.state.tenant_id` (TenantMiddleware).
- **CSRF** : actif sur tout chemin cookie-authentifié mutatif ; `<ui.form>`
  injecte `csrf_token` automatiquement (§10) — jamais sur les routes Bearer-only.
- **Headers** : `SecurityHeadersMiddleware` (`xui/security.py`) pose CSP,
  nosniff, `X-Frame-Options: DENY`, Referrer-Policy. `DEFAULT_CSP` évite le
  `'unsafe-inline'` générique sur `script-src` — un hash SHA-256 précis pour
  l'unique `<script>` inline du kit (`mode_toggle_head`, contenu
  déterministe) + `'unsafe-eval'` explicitement documenté (requis par
  Alpine.js, pas de contournement sans son build CSP-friendly).
  `style-src` scindé élément/attribut : `style-src-elem 'self'` strict
  (aucun `<style>` nulle part dans le kit), `style-src-attr 'unsafe-inline'`
  (beaucoup de composants calculent un `style="..."` dynamique en JS —
  aucun mécanisme CSP ne couvre les attributs). `report_only=True` reste le
  défaut prudent, vérifié fonctionnel en mode enforce sur les 7 plugins de
  démo — passer `False` est un choix de posture prod pour l'app hôte, pas
  un défaut xui. **Si un plugin ajoute `<ui.toast/>`** (son propre `<script>`
  inline, pas encore utilisé dans ce repo) : calculer son hash et l'ajouter
  à `DEFAULT_CSP`, sinon il casse net en mode enforce.
- **RBAC** : un seul chemin (`_resolve_user`) entre XUI et API.
- **Fragments** : une route dédiée par fragment, un `fetch()` écrit par le
  plugin — pas de mécanisme générique (§6).
- **Rebind nav/packages** : `unregister_plugin()` dans `on_unload()` — pas de
  références zombies au reload.