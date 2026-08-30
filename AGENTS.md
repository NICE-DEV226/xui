# AGENTS.md

## What this repo is
- `xui` is a Python SDK (not an app) for server-rendered pages (`mode: xui`) used by `xcore` plugins. FastAPI-based, Python ≥3.12, managed with **uv**. `main.py` is only a demo app wiring xcore + microframe + xui; it is NOT part of the installed package.
- Reference plugin is `plugins/crm_app`: pages via `mount_xui_page`, mutations as explicit POST routes in `get_router()`.
- Sibling repos matter: `../xcore` (kernel; installed here from PyPI `xcoreruntime`) and `../microframe` (the real Jinja2 engine, installed editable).

## Setup / environment
- Use `uv` everywhere (`.venv` + `uv.lock`). The committed `makefile` is stale — copied from the sibling xcore repo, it targets `poetry` and a non-existent `xcore/` path. Ignore it.
- The PyPI package `microframe` is an unrelated numpy project (name collision). The real engine must be installed editable from the sibling repo: `uv pip install -e ../microframe`. It is already linked into `.venv` via a `.pth`.
- `xui.egg-info/` is committed and expected to stay in sync: regenerate it after touching `[tool.setuptools.package-data]` (SOURCES.txt must list `xui/components/*` and `static/cotton-ui/*`).

## Commands
- Tests: `uv run pytest` (config in `pyproject.toml`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`). No lint/typecheck/lint config exists in this repo.
- Dev server: `uv run uvicorn main:app --reload` (binds 0.0.0.0:8000 in the stale makefile).

## Architecture rules (each was hard-won; see `main.py` and module docstrings)
- **No generic dispatch.** spec-v1 §15 forbids the `<action>`/`<remote>` dispatcher — never call `bind_engine()` / `register_action_routes()`. Every mutation is an explicit route declared by the plugin; CSRF is validated centrally by `xui.csrf.CSRFMiddleware` (wired in `main.py` on the protected path prefix).
- **Startup order (easy to get wrong):** `app.add_middleware(CSRFMiddleware, ...)` must be called *before* the app starts, with a **lazy** `get_token` callable — the engine only exists after `await xcore.boot(app)` inside `lifespan()`. `xcore.setup(app)` must also run before startup, never in lifespan. `mount_template_static` + `mount_builtin_assets` go inside lifespan.
- The spec (`docs/spec-v1.md`) describes kernel slots that do NOT exist in the installed kernel (`NavRegistry`/`UIPackageRegistry` on KernelContext, module-scanning `mount_ui`). `xui` deliberately implements them as module singletons (`xui.nav.registry`, `xui.packages.registry`) and per-route `mount_xui_page()`. In-code comments flag these divergences — don't "fix" code toward the spec.
- Resolve UI package exports at render time (`ui_packages.get(...)` in the view), never cache at module import — hot-reload would leave stale references.
- Rendering delegates to microframe `TemplateEngine` + `ComponentRegistry`. `<ui.x>` components ship pre-built in `xui/components/*.html` and `xui/static/cotton-ui/` (ported/vendored from django-cotton-ui; see NOTICE.md) — no build step.
- `mount_dev_proxy` is HTTP-only (no WebSocket pass-through), so Vite HMR does not work through it.

## Style
- All comments/docstrings in this codebase are written in **French** — match that when editing.

## Test quirks
- `tests/test_dev_proxy.py` runs a real threaded HTTP server on a random port (not a mock).