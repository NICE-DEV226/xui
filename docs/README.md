# Documentation xui

Hall d'entrée de la documentation. Le SDK lui-même est présenté dans
[`../README.md`](../README.md) (démarrage rapide, structure, idées maîtresses).

| Doc | Contenu |
|---|---|
| [spec-v1.md](spec-v1.md) | **La spec technique de référence** — principes fondateurs (§0), architecture (§1), packaging (§2), ajouts kernel (§3), `UIContext` (§4), dispatcher de page (§5), soumission de formulaire (§6), nav (§7), packages UI (§8), auth/RBAC (§9), CSRF (§10), WS (§11), tenancy (§12), checklist sécurité (§13), compat frontend (§14), ce qui a été retiré (§15), plan (§16). |
| [architecture.md](architecture.md) | Module par module du SDK `xui/` : `__init__`, `urls`, `theme`, `context`, `mount`, `nav`, `packages`, `csrf`, `security`, `forms` ; le moteur de composants `<ui.x>` (uivars, attrs, named slots) ; flux d'une requête ; câblage de `main.py` ; divergences spec/code ; périmètre acté hors scope ; état du MFE. |
| [components.md](components.md) | Catalogue des 57 composants `<ui.x>` par famille (props, runtime Alpine), les composants XUI natifs (`<ui.form>`, `<ui.theme/>`, `<ui.xuiboost/>`, `<ui.mode_toggle/>`...), conventions d'utilisation, assets vendorés. |
| [plugins.md](plugins.md) | Guide d'intégration pour un plugin xcore : pages XUI (`xui.urls`), mutations POST, RBAC, CSRF (`<ui.form>`), nav, packages UI (exemple réel `ui_kit`), thème custom, navigation sans rechargement, mode SPA, MFE. |
| [demo.md](demo.md) | L'app de démo elle-même : 7 plugins (dashboard/crm_app/stock/billing/tasks/demo_auth/ui_kit) comme une seule app, comment la lancer, ce que chacun prouve. |

## Par où commencer

1. **Comprendre le projet** → [`../README.md`](../README.md).
2. **Lire la spec** → [spec-v1.md](spec-v1.md) (§0 surtout : les principes
   ne se négocient pas).
3. **Voir tourner l'app de démo** → [demo.md](demo.md).
4. **Explorer le code** → [architecture.md](architecture.md).
5. **Utiliser les composants** → [components.md](components.md).
6. **Écrire un plugin** → [plugins.md](plugins.md).