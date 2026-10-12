"""Small shared helpers for the API routers."""
from typing import Any, Dict, List

from fastapi import HTTPException


def raise_lookup(exc: LookupError):
    raise HTTPException(status_code=404, detail=str(exc))


def raise_value(exc: ValueError):
    raise HTTPException(status_code=422, detail=str(exc))


def paginate_params(page: int = 1, page_size: int = 50):
    return max(1, page), max(1, min(200, page_size))


def paged(result, serialize=lambda o: o) -> Dict[str, Any]:
    return {
        "items": [serialize(i) for i in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }
