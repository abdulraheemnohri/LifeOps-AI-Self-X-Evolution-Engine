import pytest

from lifeops.models.provider_catalog import (
    PROVIDER_PRESETS,
    create_provider_adapter,
    list_provider_presets,
)


def test_catalog_includes_local_and_hosted_presets():
    assert {"ollama", "lm_studio", "vllm"} <= set(PROVIDER_PRESETS)
    assert {"groq", "cerebras", "openrouter", "gemini", "huggingface"} <= set(PROVIDER_PRESETS)


def test_list_is_safe_and_marks_configuration_only():
    providers = list_provider_presets()
    assert all(item["configuration_only"] for item in providers)
    assert all("secret" not in str(item).lower() for item in providers)
    assert next(p for p in providers if p["id"] == "ollama")["requires_api_key"] is False


def test_factory_uses_preset_and_environment_key_name():
    adapter = create_provider_adapter("groq", "example-model")
    assert adapter.base_url == "https://api.groq.com/openai/v1"
    assert adapter.api_key_env == "GROQ_API_KEY"
    assert adapter.model == "example-model"


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider_adapter("mystery-cloud", "model")


def test_factory_validates_endpoint_override():
    with pytest.raises(ValueError):
        create_provider_adapter("ollama", "model", base_url_override="file:///etc/passwd")


def test_factory_does_not_claim_network_health():
    adapter = create_provider_adapter("ollama", "local-model")
    assert adapter.is_available() is True
    # Adapter availability means configured, not that a server/model was probed.
    assert "health" not in adapter.info()
