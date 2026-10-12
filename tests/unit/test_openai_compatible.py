import pytest
from lifeops.models.openai_compatible import OpenAICompatibleAdapter, ProviderError


def test_adapter_validates_url():
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter("file:///tmp", "model")


def test_adapter_reports_configuration_without_network():
    adapter = OpenAICompatibleAdapter("https://example.invalid/v1", "model")
    assert adapter.is_available()
    assert adapter.info()["model"] == "model"


def test_missing_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("LIFEOPS_TEST_KEY", raising=False)
    adapter = OpenAICompatibleAdapter(
        "https://example.invalid/v1", "model", api_key_env="LIFEOPS_TEST_KEY"
    )
    with pytest.raises(ProviderError):
        adapter.generate("hello")
