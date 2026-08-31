# XUI — Evolution Roadmap for XCore

> **Statut : Draft technique / RFC**
>
> Objectif : faire évoluer XUI d'un SDK de pages server-rendered pour plugins XCore vers une **couche UI native et distribuable de l'écosystème XCore**, sans transformer XUI en framework frontend généraliste.

---

## 1. Contexte actuel

XUI fournit aujourd'hui principalement :

- des pages server-rendered pour les plugins XCore ;
- un `UIContext` connecté au contexte/plugin runtime ;
- l'intégration avec l'authentification et les permissions XCore ;
- CSRF pour les mutations basées sur cookie ;
- une navigation cross-plugin via `NavRegistry` ;
- des UI packages cross-plugin via `UIPackageRegistry` ;
- des composants HTML réutilisables ;
- des formulaires Pydantic ;
- un mode SPA / hybrid en complément du SSR.

Le projet actuel dépend de `xcoreruntime` en extra `xcore` et du moteur `microframe` issu du sibling repository. Le `pyproject.toml` indique explicitement que le package PyPI `microframe` actuellement disponible est un projet différent, ce qui empêche aujourd'hui une installation externe totalement autonome.

---

# 2. Vision cible

## XUI ne doit pas devenir un nouveau React

La vision cible est :

> **XUI = UI integration layer for XCore plugins.**

XCore reste responsable du runtime et de la sécurité :

```text
XCore Runtime
├── Auth
├── RBAC / permissions
├── Tenant
├── Plugin Runtime
├── Sandbox
├── Event Bus
├── Services
├── Registry
└── Lifecycle
```

XUI devient la couche UI native :

```text
XCore Runtime
      │
      ▼
   XUI Layer
      │
 ┌────┼───────────────┐
 │    │               │
Pages Surfaces     Shared UI
 │    │               │
 └────┼───────────────┘
      │
 Plugin application
```

L'objectif n'est donc pas seulement de fournir des composants visuels.

L'objectif est de permettre à XCore de composer plusieurs plugins en **une seule application cohérente, sécurisée et extensible**.

---

# 3. Principes d'architecture

### 3.1 Une seule source de vérité pour la sécurité

XUI ne doit pas recréer :

- Auth ;
- RBAC ;
- tenant isolation ;
- permission engine ;
- plugin caller.

Il doit consommer les primitives XCore existantes.

```text
Browser
   │
   ▼
XUI
   │
   ▼
XCore Auth / RBAC
   │
   ▼
Plugin Runtime
```

### 3.2 Les plugins restent autonomes

Chaque plugin garde :

- son backend ;
- ses services ;
- ses permissions ;
- ses routes ;
- ses interfaces UI.

XCore fournit le runtime commun.

### 3.3 XUI doit rester agnostique du frontend

XUI doit supporter au minimum :

```text
SSR
SPA
Hybrid
```

sans imposer React, Vue ou un framework particulier.

### 3.4 Pas de "magic action dispatcher"

Les mutations importantes doivent rester des routes/API explicites et auditables.

### 3.5 Le mode multi-plugin est une primitive de premier ordre

La navigation, les composants partagés et les surfaces UI doivent être conçus pour un environnement composé de nombreux plugins.

---

# 4. Évolution principale : UI Contract

La plus grosse évolution proposée est l'introduction d'un **XCore UI Contract**.

Au lieu que chaque plugin connaisse les détails d'intégration XUI, il déclare ses capacités UI.

Exemple :

```yaml
ui:
  enabled: true
  mode: xui

  navigation:
    - id: dashboard
      label: Dashboard
      path: /dashboard
      permission: analytics.view

  pages:
    - id: settings
      path: /settings
      mode: xui
      permission: analytics.manage

  widgets:
    - id: summary
      target: dashboard

  actions:
    - id: refresh
      permission: analytics.refresh
```

XCore peut alors comprendre le plugin comme :

```text
Plugin
├── backend
├── permissions
├── services
└── ui contract
    ├── navigation
    ├── pages
    ├── widgets
    ├── actions
    └── settings
```

---

# 5. UI Surfaces

XUI doit passer d'un modèle centré uniquement sur les pages à un modèle de **surfaces UI**.

Surfaces potentielles :

- Page ;
- Dashboard widget ;
- Sidebar entry ;
- Settings section ;
- Modal ;
- Drawer ;
- Context menu ;
- Command ;
- Action ;
- Notification source ;
- User profile section.

Exemple :

```text
CRM Plugin
├── Contacts page
├── Contacts dashboard widget
├── Create contact action
├── User profile section
└── Settings page
```

Cette approche permet à plusieurs plugins de contribuer à une même application.

---

# 6. Navigation cross-plugin

`NavRegistry` doit évoluer vers une primitive officiellement intégrée au modèle XCore.

Objectif :

```text
                 XCore Navigation
                        │
        ┌───────────────┼────────────────┐
        │               │                │
       CRM            Finance             HR
        │               │                │
     Contacts         Invoices         Employees
```

La navigation finale doit être filtrée par :

- identité ;
- tenant ;
- permission ;
- état du plugin ;
- disponibilité du plugin.

La navigation doit donc devenir une projection sécurisée du runtime.

---

# 7. UI Packages

`UIPackageRegistry` est une bonne base mais doit évoluer vers de vrais descripteurs versionnés.

Concept cible :

```python
UIPackageDescriptor(
    package_id="xcore.ui.tables",
    version="1.2.0",
    publisher="xcore",
    plugin="xui",
    exports=[...],
)
```

Le descripteur devra pouvoir contenir :

```text
package_id
version
publisher
plugin
exports
compatibility
capabilities
integrity
```

Objectif :

```text
Plugin A ──┐
Plugin B ──┼──> Shared XUI Packages
Plugin C ──┘
```

---

# 8. Design Tokens XCore

Créer une couche officielle :

```text
@xcore/ui-tokens
```

ou son équivalent Python/web.

Tokens à centraliser :

- couleurs ;
- typographie ;
- spacing ;
- radius ;
- elevation ;
- motion ;
- breakpoints ;
- z-index ;
- focus states.

L'écosystème doit pouvoir partager le même langage visuel :

```text
XUI
XCoreHub
Marketplace
Plugin UIs
Admin UI
```

Cela permet d'éviter que chaque plugin recrée son propre design system.

---

# 9. Command Palette

Ajouter une command palette native :

```text
Ctrl / Cmd + K
```

Fonctions :

```text
Search plugin
Search page
Navigate
Run allowed action
Open settings
Search resources
```

Exemple :

```text
> Open CRM
> Create invoice
> Search customer
> Plugin settings
> Restart worker
```

Les résultats doivent être filtrés par les permissions XCore.

---

# 10. Notifications

Créer un modèle de notification basé sur l'Event Bus XCore.

Exemple :

```text
XCore Event Bus
      │
      ▼
Notification Service
      │
      ▼
XUI Notification Center
```

Un plugin peut publier :

```text
invoice.overdue
deployment.failed
plugin.updated
approval.required
```

XUI expose alors :

- notification bell ;
- unread count ;
- toast ;
- notification center ;
- notification detail.

Les permissions restent contrôlées côté runtime.

---

# 11. Activity Center

Ajouter une projection UI des événements importants :

```text
Recent activity

CRM
A customer was updated

Finance
Invoice #382 created

System
Worker restarted

Marketplace
Plugin updated
```

Cette fonctionnalité doit s'appuyer sur les événements XCore et non sur un mécanisme d'audit parallèle inventé par XUI.

---

# 12. Gestion des mutations et sécurité

## 12.1 `mount_xui_page` doit être GET-only

Le helper de page ne doit pas pouvoir accepter accidentellement :

```python
methods=("GET", "POST")
```

Le rendu de page doit rester une opération de lecture.

Les mutations doivent utiliser des routes explicites.

## 12.2 Ne pas masquer les erreurs d'authentification

Le système doit différencier :

```text
Unauthenticated
Forbidden
Authentication backend failure
Internal error
```

Une panne du backend d'authentification ne doit pas être transformée silencieusement en "utilisateur non connecté".

## 12.3 CSRF

Conserver la protection CSRF pour les sessions cookie.

Tester soigneusement la compatibilité middleware/request body et limiter l'utilisation d'APIs internes Starlette.

---

# 13. Packaging et distribution

## Objectif principal

Un développeur externe doit pouvoir installer XUI sans sibling repository manuel.

Cible :

```bash
uv add xui
```

ou :

```bash
pip install xui
```

Le package doit embarquer tout ce qui est nécessaire à son fonctionnement documenté.

---

# 14. Résolution de la dépendance `microframe`

Problème actuel :

```text
XUI
 └── microframe local sibling repo
```

Le nom PyPI `microframe` est en collision avec un projet tiers.

Solution proposée :

```text
xcore-microframe
```

ou un namespace/package officiel propre à XCore.

Le module importé peut rester distinct si nécessaire.

Après migration :

```toml
dependencies = [
    "fastapi>=...",
    "httpx>=...",
    "xcore-microframe>=1,<2",
]
```

Objectif :

```bash
pip install xui
```

fonctionne dans un environnement propre.

---

# 15. Tests de distribution

Il ne suffit pas que les tests du repository passent.

Le CI doit tester le package distribué.

Pipeline :

```text
Source
  ↓
Build wheel
  ↓
Fresh environment
  ↓
Install wheel
  ↓
Smoke tests
  ↓
Integration tests
```

Tests minimum :

```python
import xui

from xui import UIContext
from xui import mount_xui_page
```

Puis un mini plugin FastAPI/XCore réel.

---

# 16. CLI XCore : ne pas créer un nouveau générateur

Le CLI XCore permet déjà de créer un plugin.

Nous devons simplement étendre cette primitive.

Actuellement :

```bash
xcore init plugin my-plugin
```

À faire :

```bash
xcore init plugin my-plugin --ui xui
```

Le CLI ajoute automatiquement :

```text
ui/
templates/
static/
```

et les métadonnées nécessaires.

---

# 17. Ajouter `xcore ui init`

Pour les plugins existants :

```bash
cd my-plugin

xcore ui init
```

Le CLI :

1. détecte le plugin ;
2. vérifie le manifest ;
3. ajoute la structure UI ;
4. ajoute la dépendance XUI ;
5. ajoute la configuration UI ;
6. génère une page exemple ;
7. ajoute les tests de base.

Cela permet de transformer progressivement des plugins backend-only en plugins avec UI.

---

# 18. Scaffolding cible

Exemple :

```text
my-plugin/
├── manifest.yaml
├── plugin.py
├── routes/
├── services/
├── tests/
│
├── ui/
│   ├── pages/
│   ├── components/
│   └── templates/
│
├── static/
│   ├── css/
│   └── js/
│
└── pyproject.toml
```

Le plugin reste libre de personnaliser son UI.

---

# 19. Trois modes de plugin UI

Le manifest doit clairement supporter :

```text
none
xui
spa
hybrid
```

Exemple :

```yaml
ui:
  enabled: true
  mode: hybrid
```

Cela permet :

```text
Plugin
├── /admin      → XUI
├── /settings   → XUI
└── /editor     → React/Vue/etc.
```

sans que XCore impose un framework frontend.

---

# 20. XUI comme Control Plane UI

Le positionnement recommandé :

```text
                    XCORE
                      │
        ┌─────────────┴──────────────┐
        │                            │
   CONTROL PLANE                APPLICATION UI
        │                            │
       XUI                     SPA / Hybrid
        │                            │
  Plugin config                   Product UI
  RBAC management                 Complex flows
  Runtime status                  Rich interactions
  Service settings
  Registry
  Administration
```

XUI n'a pas besoin de remplacer les applications frontend riches.

Il doit exceller dans les interfaces natives de plateforme.

---

# 21. Ce que XUI ne doit PAS devenir

Ne pas transformer XUI en :

- clone de React ;
- state manager généraliste ;
- nouveau backend framework ;
- ORM ;
- nouveau plugin runtime ;
- event bus ;
- microfrontend framework complet.

Le périmètre doit rester :

> **UI integration layer for XCore.**

---

# 22. Architecture cible

```text
                          XCORE PLATFORM
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
      Runtime                   XUI                  Registry
        │                        │                        │
   ┌────┼────┐         ┌────────┼────────┐          Marketplace
   │    │    │         │        │        │          Trust
 Auth  RBAC Sandbox   Pages  Surfaces  Commands
   │    │    │         │        │        │
   └────┼────┘         └────────┼────────┘
        │                       │
        └───────────────┬───────┘
                        │
                     Plugins
                        │
          ┌─────────────┼─────────────┐
          │             │             │
         CRM          Finance         HR
```

---

# 23. Roadmap proposée

## Phase 0 — Stabilisation

Priorité : **P0**

- [ ] corriger la distribution `microframe` ;
- [ ] stabiliser les imports et APIs publiques ;
- [ ] rendre `mount_xui_page` GET-only ;
- [ ] corriger la gestion des exceptions d'auth ;
- [ ] renforcer les tests ;
- [ ] ajouter package smoke tests ;
- [ ] clarifier la matrice de compatibilité XCore/XUI.

## Phase 1 — Distribution

Priorité : **P0**

- [ ] package PyPI autonome ;
- [ ] wheel/sdist propres ;
- [ ] CI de publication ;
- [ ] GitHub Releases ;
- [ ] installation dans environnement vierge ;
- [ ] documentation d'installation à jour.

## Phase 2 — Intégration CLI

Priorité : **P0**

- [ ] `xcore init plugin --ui xui` ;
- [ ] `xcore ui init` ;
- [ ] génération du manifest UI ;
- [ ] scaffold UI standard ;
- [ ] tests générés automatiquement.

## Phase 3 — UI Contract

Priorité : **P1**

- [ ] `ui.mode` ;
- [ ] navigation metadata ;
- [ ] pages ;
- [ ] surfaces ;
- [ ] actions ;
- [ ] permissions UI ;
- [ ] compatibilité XUI/XCore.

## Phase 4 — Platform UX

Priorité : **P1**

- [ ] command palette ;
- [ ] notification center ;
- [ ] activity center ;
- [ ] plugin status ;
- [ ] shared UI packages versionnés ;
- [ ] design tokens XCore.

## Phase 5 — Écosystème

Priorité : **P1/P2**

- [ ] UI metadata dans XCore Registry ;
- [ ] résolution automatique des dépendances UI ;
- [ ] intégration XCoreHub ;
- [ ] validation de compatibilité plugin/XUI ;
- [ ] surfaces UI marketplace ;
- [ ] UI packages distribuables.

---

# 24. Critères de réussite

Un développeur doit pouvoir faire :

```bash
xcore init plugin crm --ui xui
cd crm
xcore run
```

et obtenir automatiquement :

```text
Plugin backend
+
XUI
+
Navigation
+
RBAC
+
CSRF
+
Shared components
```

Un plugin existant doit pouvoir faire :

```bash
xcore ui init
```

sans être recréé.

Un utilisateur doit pouvoir installer un plugin depuis XCoreHub et obtenir automatiquement :

```text
Backend
+
UI
+
Permissions
+
Dependencies
+
Compatibility
```

---

# 25. Décisions d'architecture à valider avec XCore

Avant implémentation, les contrats suivants doivent être définis officiellement dans XCore :

```text
Auth
RBAC
Tenant
PluginContext
Plugin Caller
Lifecycle
Navigation
UI Contract
UI Packages
Events
Notifications
```

En particulier, XUI ne doit pas évoluer indépendamment de ces contrats.

---

# 26. Principe directeur

Le but final n'est pas :

> "Ajouter une UI à XCore."

Le but est :

> **Permettre à XCore de composer des plugins backend + UI comme une seule plateforme cohérente, sécurisée et extensible.**

La formule cible :

```text
XCore Runtime
+
XUI
+
Plugin Contract
+
Registry
+
Marketplace
=
Extensible Application Platform
```

---

## Priorité recommandée

### P0
**Distribution + intégration CLI + sécurité + stabilité**

### P1
**UI Contract + Surfaces + Navigation + Command Palette + Notifications**

### P2
**Marketplace UI + packages versionnés + contribution avancée des plugins**

---

## Hors périmètre immédiat

Le développement de l'interface produit DONNA n'est pas concerné par cette roadmap.

DONNA peut consommer XCore/XUI plus tard, mais son frontend produit doit rester une application distincte.

---

**Dernière mise à jour : 31 août 2026**
