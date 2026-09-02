# App de démo — 5 plugins métier comme une seule app

`plugins/` contient 7 plugins `TrustedBase` qui, ensemble, prouvent que
xui donne l'impression d'**une seule application** sans iframe ni
dispatcher générique — juste un layout partagé, une nav unifiée, et des
routes HTTP normales.

## Lancer

```bash
uv sync                              # pytest, xcoreruntime — voir [dependency-groups]
uv pip install -e ../microframe      # le vrai moteur (pas le paquet PyPI "microframe", sans rapport)
make css && make theme               # compile templates/static/{app,theme}.css (voir architecture.md)
uv run uvicorn main:app --reload
```

`/` redirige sur `/plugins/dashboard/`. Comptes de démo (voir `plugins/demo_auth`) :

| Compte | Rôles | Accès |
|---|---|---|
| `alice` / `alice123` | `sales.view`, `sales.create`, `stock.view`, `billing.view`, `tasks.view` | tout |
| `bob` / `bob123` | `sales.view`, `tasks.view` | Contacts + Tâches seulement — `stock`/`billing` renvoient 403 |

## Les 7 plugins, et ce que chacun prouve

| Plugin | Ce qu'il prouve |
|---|---|
| `demo_auth` | `AuthBackend` en mémoire (protocole du kernel, pas une réimplémentation XUI) — login/logout, cookie `session`, `<ui.form>` pour le CSRF. |
| `dashboard` | Page d'accueil pure vitrine (`<ui.card>`/`<ui.badge>`) — aucune mutation, juste pour vérifier que le layout partagé + la nav donnent le ton "single app". |
| `crm_app` | Le flux complet : liste + création avec `xui.forms.parse_form` (Pydantic), ré-affichage des erreurs par champ, CSRF via `<ui.form>`, RBAC (`sales.view` pour voir, `sales.create` pour créer). |
| `stock` | Page RBAC-gated en lecture seule (`stock.view`) — sert à démontrer le 403 pour bob. |
| `billing`, `tasks` | **Consomment** `ui_kit` (`requires: [ui_kit]`) plutôt que de dupliquer chacun leur dict couleur/libellé de statut — voir `plugins.md` §"Packages UI cross-plugin". |
| `ui_kit` | **Exporte** `status_styles` via `UIPackageRegistry`, aucune route propre. Le kernel le charge dans une vague antérieure à `billing`/`tasks` grâce à `requires:` — vérifié dans les logs de boot (`loading wave plugins=[...ui_kit]` puis `loading wave plugins=[billing, tasks]`). |

## Ce qui fait "une seule app" (pas 5 apps côte à côte)

- **`NavRegistry`** — chaque plugin enregistre son `NavNode` dans
  `on_load()` ; `templates/base.html` rend l'arbre complet, filtré par les
  rôles de l'utilisateur courant (injecté automatiquement par
  `mount_xui_page(s)`).
- **Layout partagé** — toutes les pages étendent `templates/base.html` →
  `templates/layouts/page.html` : même sidebar, même thème, même session.
- **`<ui.xuiboost/>`** — les clics sur les liens de la sidebar ne
  rechargent que `#xui-main` (`fetch()` + `DOMParser`, voir
  `architecture.md`) ; URL et titre restent corrects, back/forward marchent.
- **`<ui.mode_toggle/>`** — un seul switch clair/sombre pour toute l'app,
  pas un par plugin.
- **Pas d'iframe** : les 5 plugins métier sont `TrustedBase`, même origine,
  même session — l'isolation d'un iframe n'apporterait qu'un coût (URL
  fausse, back/forward cassé, CSP `X-Frame-Options: DENY` à affaiblir) pour
  un bénéfice nul entre plugins de confiance. Voir `plugins.md`/`architecture.md`
  pour le détail de l'arbitrage.

## Limites connues de cette démo (pas des bugs, des choix)

- **CSP** en `report_only=True` par défaut (`main.py`) — durcie mais pas
  activée par défaut, voir `architecture.md`/`xui/security.py`.
- **WS `/live`** volontairement non construit (§16 de la spec) — pas de
  cas d'usage temps réel réel dans cette démo.
- **`ui_kit`** n'a aucune route/page : c'est un plugin export-only, un
  pattern légitime pour `UIPackageRegistry` (voir `plugins.md`).
- Les données de tous les plugins métier sont **en mémoire**, perdues au
  redémarrage — c'est une démo, pas une persistance réelle.
