# Composants `<ui.x>` et runtime Alpine

## Provenance

Les 50 fichiers `xui/components/*.html` sont des **ports** (traduction de
syntaxe, pas copies d'octets) d'un sous-ensemble de
[django-cotton-ui](https://github.com/wrabit/django-cotton-ui) (MIT © Will
Abbott). Conventions de port : `<c-vars>` → `{% uivars %}`, `|get_item:x` →
`[x]` (Jinja2 subscript natif), `{% comment %}` → `{# #}`. Certains
(`checkbox`, `radio`, `switch`, `range`) sont des réécritures fonctionnelles
originales à même API. Détail par fichier dans le commentaire en tête de
chacun, provenance consolidée dans `xui/components/NOTICE.md` (licence MIT
complète).

Ils sont **pré-enregistrés** : à l'import de `xui`,
`auto_register_ui_components("xui/components")` est appelé
(`xui/__init__.py`), donc tout projet dépendant de xui a accès aux
`<ui.x>` sans copies.

À distinguer des composants **projet-local** : dans le dossier
`templates/components/` d'un projet, les fichiers `.html` sont résolus par
microframe sous le préfixe `<component.x>` (ex. `templates/components/badge.html`
→ `<component.badge>` — voir `templates/base.html` de la démo), tandis que
`<ui.x>` est réservé au registre SDK.

## Runtime client

Trois assets sont requis côté navigateur, **vendorés et auto-hébergés**
(`mount_builtin_assets` → `/xui-static/`, pas de CDN) :

- **Alpine.js core 3.17.0** (`xui/static/alpine/alpinejs.min.js`) — depuis
  ≥ 3.13, `x-teleport` (dialog/drawer/tooltip) est intégré au core, pas de
  plugin séparé.
- **`@alpinejs/collapse`** — animation `x-collapse` de `collapse.html`.
- **`@alpinejs/focus`** — `x-trap` (piège de focus des dialog/drawer).
- **`cotton-ui.min.js`** (npm 1.2.x) — les behaviors Alpine (`accordion`,
  `combobox`, `datePicker`, `dialog`, `calendar`, `dropdownMenu`, `popover`,
  `select`) et `window.CottonUI.positionPopover/watchReposition`.

Le composant `<ui.alpine/>` émet les trois balises `<script defer>` dans le
**bon ordre** (collapse → focus → core). À poser en fin de `<body>`
(typiquement dans le `{% block scripts %}` du layout ou sur les pages qui
ont besoin d'interactivité) :

```html
{% block scripts %}<ui.alpine/>{% endblock %}
```

Les composants « inline » (`tabs`, `menu`, `select`/`select_native`) n'exigent
qu'Alpine core ; les behaviors du bundle (`accordion`, `dropdownMenu`,
`dialog`, `calendar`, `datePicker`, `combobox`) exigent en plus
`cotton-ui.min.js`. Dans les deux cas, `<ui.alpine/>` après le bundle suffit —
servable aussi sur un plugin SPA pur (cf. `docs/plugins.md`).

Restent exclus du port : `composer`, `theme_builder_widget`, `nav`,
`navbar`, `navlist`, `mode_toggle`, `pagination`, `scrollspy`,
`checkbox/group`, `radio/group`, et le `select/listbox/*` dédié
(`<ui.menu>` + `<ui.menu_item>` couvre le cas riche).

## Index des composants

Tabledes 50 composants par famille. Props = valeurs typiques de `{% uivars %}`.

### Conteneurs & structure

| Composant | Props principales | Notes |
|---|---|---|
| `<ui.card>` | `padding`, `variant`, `title`, `subheading`, `header` | carte avec slots |
| `<ui.alert>` | `variant` (info/success/warning/error), `title`, `dismissible` | bannière |
| `<ui.badge>` | `color`, `size`, `variant`, `inset`, `href`, `icon_leading/trailing` | pastille |
| `<ui.description>` | `class` | texte descriptif |
| `<ui.error>` | `message`, `errors`, `name`, `class` | affiche erreur champ/globale |
| `<ui.progress>` | `value`, `color`, `size`, `show_value` | barre de progression |
| `<ui.spinner>` | `size`, `color` | loader |
| `<ui.table>` | `class` | wrapper table stylisée (slots) |

### Avatar & peau

| Composant | Props principales |
|---|---|
| `<ui.avatar>` | `src`, `alt`, `initials`, `size`, `color` |
| `<ui.avatar_group>` | `class` |

### Fil d'Ariane

| Composant | Props principales |
|---|---|
| `<ui.breadcrumbs>` | `separator` |
| `<ui.breadcrumb_item>` | `href`, `current` |

### Formulaire — wrap & champ natifs

| Composant | Props principales | Notes |
|---|---|---|
| `<ui.field>` | `variant`, `label`, `description(+_trailing)`, `error`, `badge` | wrapper avec lien label |
| `<ui.label>` | `for_`, `badge` | `<label>` stylisé |
| `<ui.input>` | `type`, `name`, `value`, `placeholder`, `size`, `disabled`, `readonly`, `left_addon`, `right_addon` | et `id`, `required`… |
| `<ui.textarea>` | `autoresize`, `size`, `height`, `resizable` | |
| `<ui.checkbox>` | `value`, `label`, `description`, `name`, `checked`, `disabled` | |
| `<ui.radio>` | `value`, `label`, `description`, `name`, `checked`, `disabled` | |
| `<ui.switch>` | `name`, `checked`, `disabled`, `value` | toggle (hidden input) |
| `<ui.range>` | `name`, `value`, `min`, `max`, `step`, `show_value` | slider |

### Boutons

| Composant | Props principales |
|---|---|
| `<ui.button>` | `variant` (default/primary/subtle/danger/ghost/text), `size`, `href`, `type`, `outlined` |

Rendu `<a>` si `href`, sinon `<button>`. `type="button"` par défaut : sans
lui, un `type="submit"` passerait en double avec le markup original.

### Accordéon & collapse

| Composant | Props principales |
|---|---|
| `<ui.accordion>` | `type` (single/multiple), `collapsible`, `disabled`, `icon_open/closed` |
| `<ui.accordion_item>` | `header`, `expanded`, `disabled`, `icon_position`, `accent` |
| `<ui.collapse>` | `trigger_text`, `trigger`, `expanded`, `chevron`, `icon` |

### Tabs

| Composant | Props principales |
|---|---|
| `<ui.tabs>` | `default_tab`, `variant` (default/segmented), `size`, `accent`, `fill` |
| `<ui.tab>` | `name`, `icon` |

Les `<ui.tab>` s'auto-enregistrent via `x-init` dans le `x-data` du parent
(`register(name)`), premier `name` actif si `default_tab` vide. Aucun
behavior bundle requis.

### Dropdown & menu

| Composant | Props principales | Notes |
|---|---|---|
| `<ui.dropdown>` | `position`, `align`, `offset`, `trigger_text`, `min_width`, `auto_position`, `trigger` | behavior `dropdownMenu` |
| `<ui.dropdown_item>` | `icon`, `kbd`, `variant` (danger…), `disabled`, `href` | |
| `<ui.dropdown_group>` | `label` | |
| `<ui.dropdown_separator>` | | |
| `<ui.menu>` | `name`, `placeholder`, `value`, `disabled`, `size`, `required`, `trigger`, `content` | select riche inline |
| `<ui.menu_trigger>` | `placeholder`, `size` | |
| `<ui.menu_content>` | `max_height` | |
| `<ui.menu_group>` | `label` | |
| `<ui.menu_item>` | `value`, `label`, `description`, `group`, `disabled`, `icon` | |
| `<ui.menu_search>` | `placeholder` | |

### Select

| Composant | Props principales | Notes |
|---|---|---|
| `<ui.select>` | `variant` (native/listbox), `label`, `name`, `placeholder`, `value`, `required`, `size` | wrapper `select_native` ou `menu` |
| `<ui.select_native>` | `name`, `placeholder`, `value`, `required`, `disabled`, `size` | `<select>` HTML |
| `<ui.select_option>` | `value`, `disabled`, `selected` | `<option>` |

### Combobox

| Composant | Props principales |
|---|---|
| `<ui.combobox>` | `label`, `description(+_trailing)`, `error`, `badge`, `name`, `options`, `selected`, `placeholder`, `max_tags`, `writable`, `searchable`, `close_after_selecting`, `autoclose`, `disabled` |

Sérialise côté serveur (hidden inputs `name[]`) ; `options`/`selected` se
passent en `{{ ['Python'] }}`.

### Popover & tooltip

| Composant | Props principales | Notes |
|---|---|---|
| `<ui.popover>` | `position`, `open_on`, `offset`, `open_delay`, `close_delay`, `trigger` | useCounterpositioning |
| `<ui.tooltip>` | `position`, `offset`, `content`, `arrow`, `delay` | |

### Dialog & drawer

| Composant | Props principales | Notes |
|---|---|---|
| `<ui.dialog>` | `open`, `dismissable`, `size`, `trigger`, `header`, `footer` | teleporté, focus piégé |
| `<ui.dialog_title>` | | aria-labelledby délégué |
| `<ui.dialog_description>` | | |
| `<ui.drawer>` | `title`, `description`, `content`, `open`, `side`, `size`, `dismissible`, `close_button`, `header`, `footer` | sheet latéral |

`trigger` accepte du HTML (guillemets échappés `&quot;`). Behaviors du
bundle ; `x-trap` via focus plugin.

### Toast (point de montage)

| Composant | Props principales |
|---|---|
| `<ui.toast>` | `position`, `appearance`, `duration` |

À poser **une fois** en fin de `<body>` (dans le layout de base). Enregistre
`Alpine.store('toasts')` sur `alpine:init` (une seule fois, idempotent) et
écoute l'événement window `toast` :

```html
<ui.button @click="$dispatch('toast', { variant:'success', title:'OK', message:'Créé.' })" variant="primary">Succès</ui.button>
```

Champs du détail : `variant` (info/success/warning/error), `appearance`
(soft/solid/outline), `position` (6 positions), `title`, `message`,
`duration` (0 = persistant), `class`. Rendu d'une pile `fixed` par coin, avec
transitions entrée/sortie.

### Calendrier & datepicker

| Composant | Props principales | Notes |
|---|---|---|
| `<ui.calendar>` | `selected`, `mode` (single/range…), `min`, `max`, `min_date`, `max_date`, `disabled_days`, `disabled_dates`, `required`, `value_format`, `full`, `name`, `fromName`, `toName` | behavior `calendar` |
| `<ui.datepicker>` | `open`, `value`, `mode`, `format`, `value_format`, `locale`, `close_on_complete`, `trap`, `min`/`max`/`min_date`/`max_date`/`disabled_days`/`disabled_dates`, `required`, `name`, `fromName`, `toName`, `label`… | behavior `datePicker`, dépliant + `<ui.calendar>` |

> **Réactivité** : le behavior `calendar` n'expose réactivement que
> `mode`, `min`, `max`, `value_format`. `required`/`min_date`/`max_date`/
> `disabled_days`/`disabled_dates` sont consommées à l'init seulement — elles
> se passent en `="{{ }}"`
> (`datepicker.html` / `calendar.html`), les conversions côté serveur étant
> équivalentes aux bindings Alpine.

### Système (alpine)

| Composant | Props |
|---|---|
| `<ui.alpine/>` | — (émet les 3 `defer`) |

## Conventions d'utilisation

### `="{{ expr }}"` (évalué serveur) vs `:attr="expr"` (Alpine)

Dans le préprocesseur, `:attr="expr"` (attribut à deux-points) devient un
binding **Alpine runtime** : le nom doit exister dans un scope `x-data`
parent. `attr="{{ expr }}"` est résolu **côté serveur** (vraie valeur
Python : `None`, booléen, chaîne) et passé comme prop au composant.

- Pour les props consommées par le composant (uivars), préférer
  `="{{ }}"` → valeur réelle, convertie par Jinja (ex. `None` → `null`,
  `True` → `true`).
- Le `:` ne s'utilise que pour les noms **présents dans un scope Alpine**
  (ex. `:disabled="disabled"` dans un composant dont le `x-data` expose
  `disabled`).
- **Ne jamais** écrire `"{{ 'true' if x else 'false' }}"` : la chaîne
  `"false"` est truthy en Jinja, `{% if x %}` serait toujours vrai.

Exemples de la démo :

```html
<ui.datepicker name="rdv" label="Date" mode="single"/>
<ui.combobox name="skills" label="Compétences"
  options="{{ ['Python', 'FastAPI'] }}" selected="{{ ['Python'] }}"/>
<ui.select variant="native" name="dept" placeholder="Choisir…">
  <ui.select_option value="eng">Ingénierie</ui.select_option>
</ui.select>
```

### Directives isolation (Alpine v3)

Les directives `@click` / `x-*` ne sont initialisées que dans une
sous-arborescence `[x-data]`. Un bouton qui `$dispatch('toast', …)` sans
scope parent ne s'exécuterait jamais — envelopper dans un `<span x-data>`
racine ou placer le contenu dans le `x-data` d'un composant.

### Attention au prose dans les templates

Écrire `<ui.alpine/>` ou `<ui.tabs>` en prose **non échappée** fait que le
préprocesseur le parse comme un vrai composant (scripts dupliqués en plein
texte, onglets fantômes). Dans le texte narratif, toujours échapper :
`&lt;ui.alpine/&gt;`.

## Assets statiques livrés (xui/static)

| Chemin | Contenu | Provenance |
|---|---|---|
| `cotton-ui/cotton-ui.min.js` | behaviors Alpine + positionnement | django-cotton-ui 1.2.x (MIT, `NOTICE.md` + `LICENSE`) |
| `cotton-ui/cotton-ui.css` | styles compilés (Tailwind v4.0.12) — inclut `[x-cloak]{display:none!important}` (SDK-wide) | idem |
| `cotton-ui/cotton-ui.tokens.css` | tokens de design | idem |
| `alpine/*.min.js` | core + collapse + focus, 3.17.0 | CDN officiels (MIT, `NOTICE.md`) |

Chargés via `mount_builtin_assets(app)` → URL `/xui-static/...` (le layout
démo les référence en `<head>`/fin de `<body>`).