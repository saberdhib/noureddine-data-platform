"""API-key authentication (governance P-03 spirit).

Protected endpoints require the ``X-API-Key`` header to match the ``API_KEY``
environment variable. Missing/empty/wrong key -> HTTP 401.
"""
from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    expected = os.getenv("API_KEY", "noureddine-dev-key")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key (header X-API-Key).",
            headers={"WWW-Authenticate": "API-Key"},
        )
    return x_api_key
