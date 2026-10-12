"""Safe, explicit provider presets for the OpenAI-compatible adapter.

Presets never imply that a provider is free or that a model is installed.
Hosted providers are contacted only when a configured adapter is used.
"""
from __future__ import annotations

from typing import Any

from lifeops.models.openai_compatible import OpenAICompatibleAdapter

PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "ollama": {"base_url": "http://127.0.0.1:11434/v1", "api_key_env": ""},
    "lm_studio": {"base_url": "http://127.0.0.1:1234/v1", "api_key_env": ""},
    "vllm": {"base_url": "http://127.0.0.1:8000/v1", "api_key_env": ""},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "cerebras": {"base_url": "https://api.cerebras.ai/v1", "api_key_env": "CEREBRAS_API_KEY"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key_env": "GEMINI_API_KEY"},
    "huggingface": {"base_url": "https://router.huggingface.co/v1", "api_key_env": "HF_TOKEN"},
}


def list_provider_presets() -> list[dict[str, Any]]:
    """Return safe display metadata; never read or expose credential values."""
    return [
        {
            "id": provider_id,
            "base_url": config["base_url"],
            "requires_api_key": bool(config["api_key_env"]),
            "api_key_env": config["api_key_env"] or None,
            "configuration_only": True,
        }
        for provider_id, config in sorted(PROVIDER_PRESETS.items())
    ]


def create_provider_adapter(
    provider_id: str,
    model: str,
    *,
    base_url_override: str | None = None,
    timeout_seconds: int = 60,
    params: dict[str, Any] | None = None,
) -> OpenAICompatibleAdapter:
    """Construct an adapter for a known preset or an explicitly supplied endpoint."""
    key = provider_id.strip().lower()
    if key not in PROVIDER_PRESETS:
        raise ValueError(f"Unknown provider preset: {key or '(empty)'}")
    preset = PROVIDER_PRESETS[key]
    return OpenAICompatibleAdapter(
        base_url=base_url_override or preset["base_url"],
        model=model,
        api_key_env=preset["api_key_env"],
        timeout_seconds=timeout_seconds,
        params=params,
    )
