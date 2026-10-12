"""OpenAI-compatible chat adapter for local and explicitly configured hosted endpoints."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit


class ProviderError(RuntimeError):
    """A provider failed or returned an invalid response."""


class OpenAICompatibleAdapter:
    """Small stdlib client; secrets are read from environment variables only."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key_env: str = "",
        timeout_seconds: int = 60,
        params: dict[str, Any] | None = None,
    ):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("base_url must be an HTTP(S) URL without credentials, query, or fragment")
        if not model or not model.strip():
            raise ValueError("model must be a non-empty string")
        if api_key_env and not api_key_env.replace("_", "").isalnum():
            raise ValueError("api_key_env must be an environment-variable name")
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.api_key_env = api_key_env
        self.timeout_seconds = max(1, min(int(timeout_seconds), 600))
        # Caller parameters may tune generation but must not replace protocol fields.
        self.params = dict(params or {})
        for reserved in ("model", "messages", "stream"):
            self.params.pop(reserved, None)

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        key = os.environ.get(self.api_key_env) if self.api_key_env else None
        if self.api_key_env and not key:
            raise ProviderError("Required provider API-key environment variable is not set")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {"model": self.model, "messages": messages, **self.params, "stream": False}
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if key:
            headers["Authorization"] = "Bearer " + key
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ProviderError("Provider returned a non-text chat-completion response")
            return content
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"Provider returned HTTP {exc.code}") from exc
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("Provider returned an invalid chat-completion response") from exc
        except ProviderError:
            raise
        except Exception as exc:
            # Avoid exposing request URLs, headers, or provider response bodies in logs.
            raise ProviderError(f"Provider request failed: {type(exc).__name__}") from exc

    def is_available(self) -> bool:
        """Report whether the adapter is configured; does not perform a network probe."""
        return bool(self.base_url and self.model)

    def info(self) -> dict[str, Any]:
        """Return safe diagnostics without revealing credentials or secret values."""
        return {
            "adapter": type(self).__name__,
            "base_url": self.base_url,
            "model": self.model,
            "configured_api_key_env": bool(self.api_key_env),
            "available": self.is_available(),
        }
