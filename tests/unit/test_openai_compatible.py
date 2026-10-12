import json
from urllib.error import HTTPError

import pytest

from lifeops.models.openai_compatible import OpenAICompatibleAdapter, ProviderError


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp",
        "ftp://example.com",
        "https://user:password@example.com/v1",
        "https://example.com/v1?token=secret",
        "https://example.com/v1#fragment",
    ],
)
def test_adapter_rejects_unsafe_or_invalid_urls(url):
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter(url, "model")


def test_adapter_requires_model():
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter("https://example.invalid/v1", " ")


def test_adapter_reports_configuration_without_network():
    adapter = OpenAICompatibleAdapter("https://example.invalid/v1", "model")
    assert adapter.is_available()
    assert adapter.info()["model"] == "model"
    assert adapter.info()["configured_api_key_env"] is False


def test_missing_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("LIFEOPS_TEST_KEY", raising=False)
    adapter = OpenAICompatibleAdapter(
        "https://example.invalid/v1", "model", api_key_env="LIFEOPS_TEST_KEY"
    )
    with pytest.raises(ProviderError, match="environment variable"):
        adapter.generate("hello")


def test_generate_sends_chat_request_and_reads_text(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "Hello back"}}]}
            ).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("LIFEOPS_TEST_KEY", "test-secret")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    adapter = OpenAICompatibleAdapter(
        "https://example.invalid/v1",
        "safe-model",
        api_key_env="LIFEOPS_TEST_KEY",
        timeout_seconds=900,
        params={"temperature": 0.2, "model": "attacker-model", "stream": True},
    )

    assert adapter.generate("Question", "System") == "Hello back"
    assert captured["url"] == "https://example.invalid/v1/chat/completions"
    assert captured["body"]["model"] == "safe-model"
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Question"},
    ]
    assert captured["body"]["temperature"] == 0.2
    assert captured["body"]["stream"] is False
    assert captured["timeout"] == 600
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert "test-secret" not in str(adapter.info())


def test_http_errors_do_not_leak_provider_body(monkeypatch):
    def fake_urlopen(*_args, **_kwargs):
        raise HTTPError(
            "https://provider.invalid", 401, "Unauthorized", {}, None
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    adapter = OpenAICompatibleAdapter("https://provider.invalid/v1", "model")
    with pytest.raises(ProviderError, match="HTTP 401") as exc:
        adapter.generate("hello")
    assert "provider.invalid" not in str(exc.value)


def test_malformed_provider_response_is_sanitized(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"choices": []}'

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    adapter = OpenAICompatibleAdapter("https://provider.invalid/v1", "model")
    with pytest.raises(ProviderError, match="invalid chat-completion"):
        adapter.generate("hello")


def test_empty_prompt_is_rejected_before_network():
    adapter = OpenAICompatibleAdapter("https://provider.invalid/v1", "model")
    with pytest.raises(ValueError, match="prompt"):
        adapter.generate(" ")
