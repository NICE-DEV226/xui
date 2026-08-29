from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from xui.csrf import CSRFMiddleware

TOKEN = "s3cr3t"


async def protected_post(request):
    form = await request.form()
    return PlainTextResponse(f"ok:{form.get('name', '')}")


async def unprotected_post(request):
    return PlainTextResponse("ok")


def build_app() -> Starlette:
    app = Starlette(
        routes=[
            Route("/plugins/crm_app/contacts/new", protected_post, methods=["POST"]),
            Route("/plugins/other/thing", unprotected_post, methods=["POST"]),
        ]
    )
    app.add_middleware(
        CSRFMiddleware,
        get_token=lambda: TOKEN,
        protected_paths=["/plugins/crm_app"],
    )
    return app


def test_post_without_session_cookie_passes_through():
    # Pas de cookie de session = pas d'auth cookie ambiante = pas de risque CSRF
    # (cas Bearer-only, docs/spec-v1.md §10).
    client = TestClient(build_app())
    r = client.post("/plugins/crm_app/contacts/new", data={"name": "x"})
    assert r.status_code == 200


def test_post_with_session_and_valid_token_passes():
    client = TestClient(build_app())
    client.cookies.set("session", "abc")
    r = client.post("/plugins/crm_app/contacts/new", data={"name": "x", "csrf_token": TOKEN})
    assert r.status_code == 200
    assert r.text == "ok:x"


def test_post_with_session_and_missing_token_rejected():
    client = TestClient(build_app())
    client.cookies.set("session", "abc")
    r = client.post("/plugins/crm_app/contacts/new", data={"name": "x"})
    assert r.status_code == 403


def test_post_with_session_and_wrong_token_rejected():
    client = TestClient(build_app())
    client.cookies.set("session", "abc")
    r = client.post("/plugins/crm_app/contacts/new", data={"name": "x", "csrf_token": "nope"})
    assert r.status_code == 403


def test_path_outside_protected_scope_not_checked():
    client = TestClient(build_app())
    client.cookies.set("session", "abc")
    r = client.post("/plugins/other/thing", data={})
    assert r.status_code == 200
