"""SecurityHeadersMiddleware — en-têtes de sécurité + CSP souple (report-only).

Le SDK fonctionne hors xcore ; le test vérifie le contrat du middleware
indépendamment des plugins (même dispatch que test_csrf.py)."""

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from xui.security import DEFAULT_CSP, SecurityHeadersMiddleware


def build_app() -> Starlette:
    app = Starlette(routes=[Route("/", lambda r: PlainTextResponse("ok"))])
    app.add_middleware(SecurityHeadersMiddleware, report_only=True)
    return app


def test_headers_securite_presentes():
    r = TestClient(build_app()).get("/")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_csp_report_only_par_defaut():
    r = TestClient(build_app()).get("/")
    assert r.headers.get("content-security-policy-report-only") == DEFAULT_CSP
    assert "content-security-policy" not in r.headers  # pas en mode bloquant


def test_csp_stricte_quand_report_only_false():
    app = Starlette(routes=[Route("/", lambda r: PlainTextResponse("ok"))])
    app.add_middleware(SecurityHeadersMiddleware, report_only=False)
    r = TestClient(app).get("/")
    assert r.headers["content-security-policy"] == DEFAULT_CSP
    assert "content-security-policy-report-only" not in r.headers


def test_exclude_paths_pas_couverts():
    app = Starlette(routes=[Route("/xui-static/a.js", lambda r: PlainTextResponse("js"))])
    app.add_middleware(SecurityHeadersMiddleware, report_only=True, exclude_paths=["/xui-static"])
    r = TestClient(app).get("/xui-static/a.js")
    assert "content-security-policy" not in r.headers
    assert "x-content-type-options" not in r.headers


def test_csp_personnalisee():
    app = Starlette(routes=[Route("/", lambda r: PlainTextResponse("ok"))])
    app.add_middleware(SecurityHeadersMiddleware, report_only=True, csp="default-src 'none'")
    r = TestClient(app).get("/")
    assert r.headers["content-security-policy-report-only"] == "default-src 'none'"