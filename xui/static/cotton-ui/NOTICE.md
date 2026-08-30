# Provenance

`cotton-ui.css`, `cotton-ui.tokens.css`, `cotton-ui.min.js` sont vendorés
tels quels depuis https://github.com/wrabit/django-cotton-ui (MIT, ©
Will Abbott) — déjà compilés (Tailwind CSS v4.0.12), aucune build ici.

Les fichiers `templates/ui/*.html` de ce dépôt sont des PORTS du markup de
ces mêmes composants (cotton -> Jinja2/`<ui.x>`), pas des copies directes :
`<c-vars>` -> `{% uivars %}`, `|get_item:x` -> `[x]`, palette de couleurs
réduite pour la démo. Voir LICENSE dans ce dossier pour les termes MIT.
