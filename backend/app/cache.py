"""Simple in-memory cache with TTL for analysis results."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Optional


class MemoryCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 3600):
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    @staticmethod
    def _make_key(url: str, days: int, sections: list[str]) -> str:
        raw = f"{url}|{days}|{','.join(sorted(sections))}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, url: str, days: int, sections: list[str]) -> Optional[Any]:
        key = self._make_key(url, days, sections)
        if key in self._store:
            value, expiry = self._store[key]
            if time.time() < expiry:
                return value
            del self._store[key]
        return None

    def set(self, url: str, days: int, sections: list[str], value: Any, ttl: Optional[int] = None) -> None:
        key = self._make_key(url, days, sections)
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (value, expiry)

    def cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if now >= exp]
        for k in expired:
            del self._store[k]
