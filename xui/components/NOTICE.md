# Provenance

La plupart des fichiers `.html` de ce dossier sont des **ports** (traduction
de syntaxe, pas des copies d'octets) d'un sous-ensemble de composants de
[django-cotton-ui](https://github.com/wrabit/django-cotton-ui) (MIT,
© Will Abbott) : `<c-vars>` → `{% uivars %}`, `|get_item:x` → `[x]`,
`{% comment %}` → `{# #}`. Voir le commentaire en tête de chaque fichier
pour son statut exact — certains (`checkbox.html`, `radio.html`,
`switch.html`, `range.html`) sont des réécritures fonctionnelles originales
(même API, logique et markup propres à xui), pas des ports.

Licence du matériau source porté : MIT, texte complet dans
`templates/static/cotton-ui/LICENSE` de ce dépôt (copie identique reproduite
ici par souci de proximité avec les fichiers concernés) :

## Portage interactif (2026)

Nouvel apport : les familles interactives suivantes, portées à l'identique
de la syntaxe (markup/JSON/JS des templates d'origine conservés au plus près) :

- `accordion.html`, `accordion_item.html`, `collapse.html`
- `dropdown.html`, `dropdown_item.html`, `dropdown_group.html`, `dropdown_separator.html`
- `menu.html` (+ `menu_trigger`, `menu_item`, `menu_content`, `menu_group`, `menu_search`)
- `popover.html`, `tooltip.html`
- `dialog.html`, `dialog_title.html`, `dialog_description.html`, `drawer.html`
- `toast.html`, `calendar.html`, `datepicker.html`, `combobox.html`
- `select.html`, `select_native.html`, `select_option.html`

Conventions appliquées au port :
- split `index/impl` **fusionné** en un seul fichier (`datepicker.html`,
  `combobox.html`, `select.html` — même principe que `input.html`) : le split
  d'origine ne servait qu'à intégrer automatiquement le wrapper field, que le
  composant fusionné gère lui-même de façon conditionnelle ;
- `select/listbox/*` est resté **exclu** : ses items sont le composant
  générique `<ui.menu_item>` (le select riche ↔ `variant="listbox"` =
  `<ui.menu>`), les composants listbox dédiés (triggers/cliché + behavior
  dédié absent du bundle `cotton-ui.min.js`) n'ont pas de pendant utile.
- restent aussi exclus du périmètre : `composer`, `theme_builder_widget`,
  `nav`, `navbar`, `navlist`, `mode_toggle`, `pagination`, `scrollspy`,
  `checkbox/group`, `radio/group`.

Runtime client requis (non embarqué dans le bundle vendorisé) : Alpine.js
core + les plugins `@alpinejs/focus` (x-trap, utilisé par `drawer`) et
`@alpinejs/collapse` (animation de `collapse.html`). `x-teleport` (dialog,
drawer, tooltip) est intégré au core Alpine ≥ 3.13 — pas de plugin séparé.
Ces assets sont livrés auto-hébergés avec le SDK dans `xui/static/alpine/`
(version 3.17.0, voir `xui/static/alpine/NOTICE.md`) et chargés via le
composant `<ui.alpine/>` à poser en fin de `<body>`.
Les behaviors Alpine (`accordion`, `combobox`, `datePicker`, `dialog`,
`calendar`, `dropdownMenu`, `popover`, `select`…) et l'API
`window.CottonUI.positionPopover/watchReposition` proviennent bien du bundle
`xui/static/cotton-ui/cotton-ui.min.js` (version npm 1.2.x, source-map jointe).

```
MIT License

Copyright (c) 2024 Will Abbott

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
```
