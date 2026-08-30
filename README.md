# XUI — SDK de pages server-rendues pour plugins xcore

SDK de pages server-rendues pour les plugins xcore : composants `<ui.x>`
interactifs portés en Jinja2, rendus par le vrai moteur de templates
(microframe), avec RBAC, CSRF et navigation cross-plugin.

> **Principe fondateur** : xui est un plugin SDK, jamais du kernel, jamais un
> prérequis. Rien dans `xcore/kernel/` ne connaît xui ; un plugin
> React/Vue/Svelte pur doit fonctionner sans importer un seul module xui.
> Chaque interaction est une **route HTTP explicite** (spec-v1 §15), jamais un
> dispatcher générique. Voir `docs/spec-v1.md`.

## Démarrage rapide

```bash
# 1. Dépendances (uv). Le vrai moteur microframe est installé en editable
#    depuis le sibling repo — le paquet PyPI "microframe" est un numpy
#    sans rapport (collision de nom) :
uv pip install -e ../microframe
uv sync --extra xcore          # xcore est optionnel : seul mount_xui_page l'exige

# 2. Lancer la démo (xcore + microframe + xui câblés sans dispatcher) :
uv run uvicorn main:app --reload   # http://localhost:8000

# 3. Tests : 42
uv run pytest
```

## Ce que contient le repo

| Chemin | Rôle |
|---|---|
| `xui/` | **Le SDK lui-même** (le package installable) |
| `xui/__init__.py` | Exporte l'API publique + auto-enregistre les composants `<ui.x>` |
| `xui/context.py` | `UIContext`, `UIPermissionDenied`, `UIRedirect` |
| `xui/mount.py` | Monte des pages, SPA, proxy dev, assets SDK |
| `xui/nav.py` | `NavRegistry` — arbre de navigation cross-plugin |
| `xui/packages.py` | `UIPackageRegistry` — exports UI cross-plugin |
| `xui/csrf.py` | `CSRFMiddleware` pour les routes cookie-authentifiées |
| `xui/forms.py` | `parse_form` / `FormResult` — validation Pydantic ré-affichable |
| `xui/components/` | 50 composants `<ui.x>` (pre-built, portés de django-cotton-ui) |
| `xui/static/` | Assets vendorés auto-hébergés (cotton-ui, Alpine 3.17) |
| `templates/` | Démo : `base.html`, layouts, landing, login |
| `main.py` | App démo : câblage xcore + microframe + xui — **pas** le SDK |
| `integration.yaml` | Manifeste de l'app démo (extensions, plugins) |
| `plugins/` | Plugins de référence/démo (crm_app, demo_auth, ui_kit, spa_demo) |
| `tests/` | Suite de tests (42 tests, `uv run pytest`) |
| `docs/spec-v1.md` | **La spec technique** — architecture, sécurité, contraintes |

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — module par module du SDK.
- [`docs/components.md`](docs/components.md) — catalogue complet des composants `<ui.x>` et du runtime Alpine.
- [`docs/plugins.md`](docs/plugins.md) — guide d'intégration pour un plugin (pages XUI, RBAC, formulaires, CSRF, nav, packages UI, mode SPA).
- [`docs/spec-v1.md`](docs/spec-v1.md) — la spec technique de référence.

## Idées maîtresses

1. **Le serveur est la seule source de vérité.** Aucune décision de sécurité
   côté client — `UIContext.user` et `Depends(get_current_user)` proviennent
   strictement de la même fonction (`_resolve_user`).
2. **Pas de runtime générique imposé.** Les mutations sont des `<form>`/`fetch`
   vers des routes FastAPI que le plugin déclare lui-même. Pas de
   `<action>`/`<remote>` ni de bus d'événements (spéc §15).
3. **Rendu délégué à microframe.** `TemplateEngine` + `ComponentRegistry` —
   xui ne réimplémente pas un moteur Jinja.
4. **Sans xcore requis à l'import.** Le SDK s'importe sans xcore installé
   (`UIContext`, CSRF, forms, mounts statics, composants). Seul
   `mount_xui_page()` exige xcore, au moment de l'appel.
5. **Assets vendored, pas de CDN.** Les composants fonctionnent hors-ligne,
   version verrouillée, CSP-friendly, via `mount_builtin_assets`
   (`/xui-static/`).