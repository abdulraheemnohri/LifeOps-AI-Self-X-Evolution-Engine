"""Explicitly configured webhook integration with strict HTTPS allow-listing."""
from __future__ import annotations
import json
import urllib.request
from urllib.parse import urlparse


class WebhookError(RuntimeError):
    pass


class WebhookIntegration:
    def __init__(self, endpoint: str, allowed_hosts: set[str], timeout_seconds: int = 10):
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Webhook endpoint must be an HTTPS URL")
        host = parsed.hostname.lower()
        normalized = {item.lower() for item in allowed_hosts}
        if host not in normalized:
            raise ValueError("Webhook host is not in the configured allow-list")
        if parsed.username or parsed.password:
            raise ValueError("Credentials must not be embedded in webhook URLs")
        self.endpoint = endpoint
        self.timeout_seconds = max(1, min(int(timeout_seconds), 30))

    def send_json(self, payload: dict) -> int:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint, data=data,
            headers={"Content-Type": "application/json", "User-Agent": "LifeOps-SelfX/0.1"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return int(response.status)
        except Exception as exc:
            raise WebhookError(f"Webhook delivery failed: {type(exc).__name__}") from exc
