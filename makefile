
# ============================================================
# 🎨 CSS (Tailwind du PROJET — cotton-ui.css reste figé/vendoré tel quel,
#    voir xui/static/cotton-ui/NOTICE.md ; ceci compile templates/static/app.css
#    depuis tailwind-src.css en scannant templates/ et xui/components/)
# ============================================================
TAILWIND_VERSION := v4.0.12
TAILWIND_BIN := .bin/tailwindcss

$(TAILWIND_BIN):
	@mkdir -p .bin
	@echo "téléchargement de tailwindcss $(TAILWIND_VERSION) (linux-x64, binaire standalone officiel tailwindlabs)…"
	@curl -sfL -o $(TAILWIND_BIN) \
		"https://github.com/tailwindlabs/tailwindcss/releases/download/$(TAILWIND_VERSION)/tailwindcss-linux-x64"
	@chmod +x $(TAILWIND_BIN)

css: $(TAILWIND_BIN) ## Régénérer templates/static/app.css depuis tailwind-src.css
	@$(TAILWIND_BIN) -i tailwind-src.css -o templates/static/app.css

css-watch: $(TAILWIND_BIN) ## Idem, en watch pendant le dev
	@$(TAILWIND_BIN) -i tailwind-src.css -o templates/static/app.css --watch

theme: $(TAILWIND_BIN) ## Régénérer templates/static/theme.css depuis theme.css (servi par mount_theme())
	@mkdir -p templates/static
	@$(TAILWIND_BIN) -i theme.css -o templates/static/theme.css

theme-watch: $(TAILWIND_BIN) ## Idem, en watch pendant le dev
	@$(TAILWIND_BIN) -i theme.css -o templates/static/theme.css --watch

# ============================================================
# 🧹 Nettoyage
# ============================================================
clean: ## Supprimer __pycache__, *.pyc, *.pyo
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	@find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.backup" \) -exec rm -f {} +
