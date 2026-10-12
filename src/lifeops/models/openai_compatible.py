"""OpenAI-compatible chat adapter for local and explicitly configured hosted endpoints."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from typing import Any


class ProviderError(RuntimeError):
    """A provider failed or returned an invalid response."""


class OpenAICompatibleAdapter:
    """Minimal stdlib client; API keys are read from environment variables only."""
    def __init__(self, base_url: str, model: str, api_key_env: str = "",
                 timeout_seconds: int = 60, params: dict[str, Any] | None = None):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must use HTTP or HTTPS")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout_seconds = max(1, min(int(timeout_seconds), 600))
        self.params = params or {}

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        key = os.environ.get(self.api_key_env) if self.api_key_env else None
        if self.api_key_env and not key:
            raise ProviderError("Required provider API-key environment variable is not set")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {"model": self.model, "messages": messages, **self.params}
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = "Bearer " + key
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"Provider returned HTTP {exc.code}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Provider returned an invalid chat-completion response") from exc
        except Exception as exc:
            raise ProviderError(f"Provider request failed: {type(exc).__name__}") from exc

    def is_available(self) -> bool:
        return bool(self.base_url and self.model)

    def info(self) -> dict[str, Any]:
        return {"adapter": type(self).__name__, "base_url": self.base_url,
                "model": self.model, "available": self.is_available()}
