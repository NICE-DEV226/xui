# Documentation xui

Hall d'entrée de la documentation. Le SDK lui-même est présenté dans
[`../README.md`](../README.md) (démarrage rapide, structure, idées maîtresses).

| Doc | Contenu |
|---|---|
| [spec-v1.md](spec-v1.md) | **La spec technique de référence** — principes fondateurs (§0), architecture (§1), packaging (§2), ajouts kernel (§3), `UIContext` (§4), dispatcher de page (§5), soumission de formulaire (§6), nav (§7), packages UI (§8), auth/RBAC (§9), CSRF (§10), WS (§11), tenancy (§12), checklist sécurité (§13), compat frontend (§14), ce qui a été retiré (§15), plan (§16). |
| [architecture.md](architecture.md) | Module par module du SDK `xui/` : `__init__`, `context`, `mount`, `nav`, `packages`, `csrf`, `security`, `forms` ; flux d'une requête ; câblage de `main.py` ; divergences spec/code ; périmètre acté hors scope ; état du MFE. |
| [components.md](components.md) | Catalogue des 50 composants `<ui.x>` par famille (props, runtime Alpine), conventions d'utilisation, assets vendorés. |
| [plugins.md](plugins.md) | Guide d'intégration pour un plugin xcore : pages XUI, mutations POST, RBAC, CSRF, formulaires, nav, packages UI, mode SPA, MFE. |

## Par où commencer

1. **Comprendre le projet** → [`../README.md`](../README.md).
2. **Lire la spec** → [spec-v1.md](spec-v1.md) (§0 surtout : les principes
   ne se négocient pas).
3. **Explorer le code** → [architecture.md](architecture.md).
4. **Utiliser les composants** → [components.md](components.md).
5. **Écrire un plugin** → [plugins.md](plugins.md).