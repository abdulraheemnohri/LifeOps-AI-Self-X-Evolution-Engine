"""Tests for model runtime adapters: mock, LiteRT fallback, and Ollama.

The Ollama tests use a real in-process HTTP server that mimics the native
Ollama API (/api/generate, /api/tags, / 200 "Ollama is running"), so the
adapter's actual HTTP code paths are exercised without needing an installed
Ollama binary.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from lifeops.models.adapters import (LiteRTLMAdapter, MockModelAdapter,
                                     ModelUnavailableError, OllamaAdapter)


class _FakeOllama(BaseHTTPRequestHandler):
    """Minimal stand-in for the Ollama daemon."""
    models_served = ["llama3.2:latest", "phi3:mini"]

    def log_message(self, *args):  # silence
        pass

    def do_GET(self):
        if self.path == "/":
            body = b"Ollama is running"
            self.send_response(200)
        elif self.path == "/api/tags":
            body = json.dumps({"models": [{"name": n} for n in self.models_served]}).encode()
            self.send_response(200)
        else:
            self.send_response(404)
            body = b"not found"
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/generate":
            resp = json.dumps({
                "model": payload.get("model", ""),
                "response": f"fake-reply-to:{payload.get('prompt', '')}",
                "done": True,
            }).encode()
            self.send_response(200)
        elif self.path == "/api/error":
            self.send_response(500)
            resp = b"boom"
        else:
            self.send_response(404)
            resp = b"not found"
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)


@pytest.fixture(scope="module")
def fake_ollama():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


# ------------------------------------------------------------------ mock/litert
def test_mock_adapter_always_available():
    adapter = MockModelAdapter()
    assert adapter.is_available() is True
    assert "hello" in adapter.generate("hello")
    assert adapter.info()["adapter"] == "MockModelAdapter"


def test_litert_falls_back_without_binary():
    adapter = LiteRTLMAdapter(binary_path="definitely-not-installed-xyz")
    assert adapter.is_available() is False
    assert "LiteRT Local Response" in adapter.generate("ping")


def test_litert_available_when_binary_present(tmp_path):
    # /bin/sh always exists on POSIX; shutil.which resolves absolute path too
    adapter = LiteRTLMAdapter(binary_path="/bin/sh")
    assert adapter.is_available() is True


# ------------------------------------------------------------------ ollama core
def test_ollama_generate_against_fake_server(fake_ollama):
    adapter = OllamaAdapter(model_name="llama3.2", base_url=fake_ollama)
    out = adapter.generate("hi there", system_prompt="be nice")
    assert out == "fake-reply-to:hi there"


def test_ollama_passes_options_and_system(fake_ollama):
    adapter = OllamaAdapter(model_name="phi3:mini", base_url=fake_ollama,
                            generation_params={"temperature": 0.2, "seed": None})
    # Our fake echoes only the prompt, but ensure no crash with options attached
    assert adapter.generate("x") == "fake-reply-to:x"


def test_ollama_list_models(fake_ollama):
    adapter = OllamaAdapter(base_url=fake_ollama)
    assert adapter.list_models() == ["llama3.2:latest", "phi3:mini"]


def test_ollama_is_available_true(fake_ollama):
    assert OllamaAdapter(base_url=fake_ollama).is_available() is True


def test_ollama_unreachable_raises_and_reports_unavailable():
    # Port 1 is reserved/unused -> connection refused
    adapter = OllamaAdapter(base_url="http://127.0.0.1:1", timeout_seconds=2)
    assert adapter.is_available() is False
    assert adapter.list_models() == []
    with pytest.raises(ModelUnavailableError):
        adapter.generate("anything")


def test_ollama_info(fake_ollama):
    info = OllamaAdapter(base_url=fake_ollama, model_name="m").info()
    assert info["adapter"] == "OllamaAdapter"
    assert info["model"] == "m"
    assert info["available"] is True
    assert info["base_url"] == fake_ollama


# ------------------------------------------------------------------ settings wiring
def test_api_get_adapter_selects_ollama():
    from lifeops.api.routers.agents import _get_adapter
    settings = {"model": {"runtime": "ollama", "model_path": "llama3.2",
                          "ollama_base_url": "http://localhost:11434"}}
    adapter = _get_adapter(settings)
    assert isinstance(adapter, OllamaAdapter)
    assert adapter.model_name == "llama3.2"
    assert adapter.base_url == "http://localhost:11434"


def test_web_get_adapter_selects_runtime():
    from lifeops.web.app_ui import _model_adapter
    assert isinstance(_model_adapter({"model": {"runtime": "mock"}}), MockModelAdapter)
    assert isinstance(_model_adapter({"model": {"runtime": "litert", "model_path": "/m.x"}}, ), LiteRTLMAdapter)
    assert isinstance(_model_adapter({"model": {"runtime": "ollama"}}), OllamaAdapter)


def test_settings_validate_rejects_unknown_runtime():
    from lifeops.services.settings_service import SettingsService
    ok, err = SettingsService.__new__(SettingsService).validate(
        "model", {"runtime": "gptx"})
    assert ok is False and "mock, litert, ollama" in err
    ok, _ = SettingsService.__new__(SettingsService).validate("model", {"runtime": "ollama"})
    assert ok is True


# ------------------------------------------------------------------ e2e via API
def test_models_runtime_and_test_endpoints_with_fake_ollama(client, fake_ollama):
    # Point settings at the fake server and select ollama runtime
    r = client.put("/api/v1/settings/model", json={"updates": {
        "runtime": "ollama", "model_path": "llama3.2", "ollama_base_url": fake_ollama}})
    assert r.status_code == 200, r.text

    rt = client.get("/api/v1/models/runtime").json()
    assert rt["configured_runtime"] == "ollama"
    assert rt["ollama_reachable"] is True
    assert "ollama" in rt["available_runtimes"]

    res = client.post("/api/v1/models/test", json={"prompt": "hello"}).json()
    assert res["runtime"] == "OllamaAdapter"
    assert res["response"] == "fake-reply-to:hello"
    assert res["error"] is None

    # switch back to mock; unknown runtime must be rejected
    assert client.put("/api/v1/settings/model",
                      json={"updates": {"runtime": "bogus"}}).status_code == 422
    assert client.put("/api/v1/settings/model",
                      json={"updates": {"runtime": "mock"}}).status_code == 200
