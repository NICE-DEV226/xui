"""xui.urls — déclaration de pages façon Django `urlpatterns` (docs/spec-v1.md
§6/§15) : `mount_xui_pages` ne fait que dérouler la liste en appels
`mount_xui_page` au montage, `reverse()` est un lookup statique, pas un
résolveur de requête."""

from types import ModuleType
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from xui import mount_xui_pages, path, reverse
from xui.urls import _names


@pytest.fixture(autouse=True)
def _clean_registry():
    # `_names` est un registre process-wide (comme NavRegistry) — on l'isole
    # entre tests pour que l'ordre d'exécution n'influence pas les collisions.
    _names.clear()
    yield
    _names.clear()


class _NoOpAuthBackend:
    """Backend minimal : aucun token ne décode jamais, donc chaque requête
    reste anonyme — mais un backend EST enregistré, comme dans une vraie
    app. Sans lui, `_resolve_user` lève un 503 ("auth backend non
    disponible"), plus une simple absence de connexion — voir
    `xui.context.resolve_user_or_anonymous` (docs/XUI_EVOLUTION_ROADMAP.md
    §12.2) qui ne convertit plus ce cas en anonyme silencieux."""

    async def extract_token(self, request):
        return None

    async def decode_token(self, token):
        return None

    async def has_permission(self, payload, permission):
        return False


@pytest.fixture(autouse=True)
def _auth_backend():
    from xcore.kernel.api.auth import register_auth_backend, unregister_auth_backend

    register_auth_backend(_NoOpAuthBackend())
    yield
    unregister_auth_backend()


def _ctx() -> Any:
    class PluginCtx(ModuleType):
        pass

    ctx = PluginCtx("ctx")
    ctx.name = "landing"
    ctx.tenant_id = None
    ctx.caller = None
    ctx.get_service = lambda self, _name: None
    return ctx


class _FakeEngine:
    async def render(self, template: str, ctx_dict: dict) -> str:
        return f"<h1>{template}</h1>"


def _index_view(ctx):
    return {"title": "Accueil"}


def _pricing_view(ctx):
    return {"title": "Tarifs"}


def build_app() -> FastAPI:
    app = FastAPI()
    router = APIRouter()
    urlpatterns = [
        path("/", _index_view, template="landing/index.html", name="landing.index"),
        path("/pricing", _pricing_view, template="landing/pricing.html", name="landing.pricing"),
    ]
    mount_xui_pages(router, _ctx(), _FakeEngine(), urlpatterns, login_path="/login")
    app.include_router(router)
    return app


def test_each_declared_route_is_mounted_and_renders():
    client = TestClient(build_app())
    r = client.get("/")
    assert r.status_code == 200 and "landing/index.html" in r.text

    r = client.get("/pricing")
    assert r.status_code == 200 and "landing/pricing.html" in r.text


def test_reverse_resolves_declared_names():
    build_app()  # mount_xui_pages() peuple le registre en tournant
    assert reverse("landing.index") == "/"
    assert reverse("landing.pricing") == "/pricing"


def test_reverse_unknown_name_raises_keyerror():
    build_app()
    with pytest.raises(KeyError):
        reverse("landing.nope")


def test_duplicate_name_pointing_elsewhere_raises():
    router = APIRouter()
    urlpatterns = [
        path("/", _index_view, template="a.html", name="dup"),
        path("/other", _pricing_view, template="b.html", name="dup"),
    ]
    with pytest.raises(ValueError):
        mount_xui_pages(router, _ctx(), _FakeEngine(), urlpatterns)


def test_remounting_same_name_and_path_is_idempotent():
    # Cas d'un hot-reload de plugin : mêmes urlpatterns remontées à l'identique
    # ne doivent pas lever (contrairement à NavRegistry, pas besoin d'un
    # unregister_plugin ici — voir le docstring de mount_xui_pages).
    urlpatterns = [path("/", _index_view, template="a.html", name="same")]
    router = APIRouter()
    mount_xui_pages(router, _ctx(), _FakeEngine(), urlpatterns)
    mount_xui_pages(router, _ctx(), _FakeEngine(), urlpatterns)  # ne doit pas planter
    assert reverse("same") == "/"
