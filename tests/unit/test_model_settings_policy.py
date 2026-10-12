"""Security and persistence tests for the model provider settings layer."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lifeops.models.provider_catalog import PROVIDER_PRESETS, create_provider_adapter
from lifeops.models.configured_provider import (
    SETTING_KEY,
    build_configured_adapter,
    is_safe_endpoint_override,
    read_model_settings,
)
from lifeops.storage.models import Base, Setting


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_provider_preset_catalog_uses_http_s_endpoints():
    from urllib.parse import urlsplit

    assert {"ollama", "lm_studio", "vllm", "groq", "cerebras", "openrouter", "gemini", "huggingface"} <= set(PROVIDER_PRESETS)
    for provider in PROVIDER_PRESETS.values():
        assert urlsplit(provider["base_url"]).scheme in {"http", "https"}


def test_endpoint_override_policy_allows_only_explicit_loopback_http():
    assert is_safe_endpoint_override("http://127.0.0.1:11434/v1")
    assert is_safe_endpoint_override("http://localhost:1234/v1")
    assert is_safe_endpoint_override("http://[::1]:8000/v1")
    for unsafe in (
        "https://example.com/v1",
        "http://192.168.1.5:1234/v1",
        "http://127.0.0.1/v1",
        "http://127.0.0.1:99999/v1",
        "http://user:pass@127.0.0.1:1234/v1",
        "http://127.0.0.1:1234/v1?token=secret",
        "http://127.0.0.1:1234/v1#fragment",
        "file:///etc/passwd",
        "http://127.0.0.1:1234/v1\\nHost: example.com",
    ):
        assert not is_safe_endpoint_override(unsafe), unsafe


def test_adapter_factory_rejects_unknown_provider_and_never_needs_key_input():
    try:
        create_provider_adapter("unknown-provider", "model")
    except ValueError as exc:
        assert "Unknown provider" in str(exc)
    else:
        raise AssertionError("unknown provider should be rejected")

    adapter = create_provider_adapter("ollama", "qwen2.5")
    assert adapter.base_url == "http://127.0.0.1:11434/v1"
    assert adapter.api_key_env == ""


def test_read_settings_normalizes_values_and_discards_unsafe_override():
    with make_session() as db:
        db.add(Setting(key=SETTING_KEY, value={
            "provider_id": "not-a-provider",
            "model": "  qwen2.5  ",
            "base_url_override": "http://192.168.1.5:1234/v1",
            "timeout_seconds": 900,
            "api_key": "must-not-be-used",
        }))
        db.commit()

        settings = read_model_settings(db)

    assert settings == {
        "provider_id": "ollama",
        "model": "qwen2.5",
        "base_url_override": "",
        "timeout_seconds": 120,
    }
    assert "api_key" not in settings


def test_adapter_is_not_constructed_until_model_is_selected():
    with make_session() as db:
        assert build_configured_adapter(db) is None
        db.add(Setting(key=SETTING_KEY, value={
            "provider_id": "ollama",
            "model": "qwen2.5",
            "timeout_seconds": 15,
        }))
        db.commit()
        adapter = build_configured_adapter(db)

    assert adapter is not None
    assert adapter.model == "qwen2.5"
    assert adapter.timeout_seconds == 15
