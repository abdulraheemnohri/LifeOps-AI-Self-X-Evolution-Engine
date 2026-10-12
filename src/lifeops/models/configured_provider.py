"""Load the active model configuration without performing network I/O.

Settings are intentionally credential-free: API tokens are resolved by the adapter
from environment variables and are never stored in the SQLite settings row.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from lifeops.models.provider_catalog import PROVIDER_PRESETS, create_provider_adapter
from lifeops.storage.models import Setting


SETTING_KEY = "model_provider"


def read_model_settings(db: Session) -> dict[str, Any]:
    """Return a validated, safe copy of persisted model settings."""
    row = db.get(Setting, SETTING_KEY)
    value = row.value if row is not None and isinstance(row.value, dict) else {}
    provider_id = str(value.get("provider_id", "ollama")).strip().lower()
    if provider_id not in PROVIDER_PRESETS:
        provider_id = "ollama"
    model = str(value.get("model", "")).strip()
    endpoint = str(value.get("base_url_override", "")).strip()
    try:
        timeout = int(value.get("timeout_seconds", 60))
    except (TypeError, ValueError):
        timeout = 60
    timeout = min(120, max(1, timeout))
    # Ignore a malformed persisted override instead of letting it redirect traffic.
    if endpoint and not is_safe_endpoint_override(endpoint):
        endpoint = ""
    return {
        "provider_id": provider_id,
        "model": model,
        "base_url_override": endpoint,
        "timeout_seconds": timeout,
    }


def is_safe_endpoint_override(endpoint: str) -> bool:
    """Allow explicit HTTP loopback endpoints only (SSRF protection)."""
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and port is not None
        and 1 <= port <= 65535
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
    )


def build_configured_adapter(db: Session):
    """Build the adapter from stored settings; return None until a model is chosen."""
    config = read_model_settings(db)
    if not config["model"]:
        return None
    return create_provider_adapter(
        config["provider_id"],
        config["model"],
        base_url_override=config["base_url_override"] or None,
        timeout_seconds=config["timeout_seconds"],
    )
