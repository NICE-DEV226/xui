# Provenance

Fichiers Alpine.js vendorés depuis les CDN officiels (MIT, © Caleb Porzio et
contributeurs) — version 3.17.0, builds `cdn.min.js` officiels, aucune
modification. Livrés auto-hébergés avec le SDK (`mount_builtin_assets` → 
`/xui-static/alpine/`) pour que les plugins xcore n'aient pas à dépendre d'un
CDN externe (hors-ligne, CSP, version verrouillée).

- `alpinejs.min.js` : Alpine core. Depuis 3.13, `x-teleport` (utilisé par
  `drawer.html`/`dialog.html`/`tooltip.html`) est intégré au core — aucun
  plugin teleport séparé requis.
- `@alpinejs_collapse.min.js` : plugin `x-collapse` (accordion).
- `@alpinejs_focus.min.js` : plugin `x-trap` (piège de focus des
  dialog/drawer).

Chargement via le composant `<ui.alpine/>` (voir `xui/components/alpine.html`),
qui émet les trois `<script defer>` dans le bon ordre.
