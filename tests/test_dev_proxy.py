"""mount_dev_proxy — vérifie sur un vrai serveur HTTP local (pas un mock)
que le forward GET/POST, les headers et le corps traversent correctement.
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from xui.mount import mount_dev_proxy


class _FakeDevServerHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silence les logs d'accès pendant les tests

    def do_GET(self):
        if self.path == "/":
            body = b"<h1>Vite dev server</h1>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("X-Dev-Server", "vite")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"echo:" + body)


@pytest.fixture
def fake_dev_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeDevServerHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    thread.join()


def _build_proxy_app(dev_server: str) -> FastAPI:
    app = FastAPI()
    router = APIRouter()
    mount_dev_proxy(router, dev_server)
    app.include_router(router)
    return app


def test_proxy_forwards_get_and_headers(fake_dev_server):
    client = TestClient(_build_proxy_app(fake_dev_server))
    r = client.get("/")
    assert r.status_code == 200
    assert r.text == "<h1>Vite dev server</h1>"
    assert r.headers.get("x-dev-server") == "vite"


def test_proxy_forwards_post_body(fake_dev_server):
    client = TestClient(_build_proxy_app(fake_dev_server))
    r = client.post("/echo", content=b"hello proxy")
    assert r.status_code == 200
    assert r.text == "echo:hello proxy"


def test_proxy_404_from_upstream_passes_through(fake_dev_server):
    client = TestClient(_build_proxy_app(fake_dev_server))
    r = client.get("/does-not-exist")
    assert r.status_code == 404
