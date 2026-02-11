"""Tests for the cache module."""

import time
from app.cache import MemoryCache


class TestMemoryCache:
    def test_set_and_get(self):
        cache = MemoryCache(default_ttl=60)
        cache.set("https://example.com", 30, [], "data")
        result = cache.get("https://example.com", 30, [])
        assert result == "data"

    def test_miss_returns_none(self):
        cache = MemoryCache()
        assert cache.get("https://example.com", 30, []) is None

    def test_expired_returns_none(self):
        cache = MemoryCache(default_ttl=1)
        cache.set("https://example.com", 30, [], "data", ttl=0)
        time.sleep(0.1)
        assert cache.get("https://example.com", 30, []) is None

    def test_different_params_different_keys(self):
        cache = MemoryCache()
        cache.set("https://example.com", 30, [], "data30")
        cache.set("https://example.com", 60, [], "data60")
        assert cache.get("https://example.com", 30, []) == "data30"
        assert cache.get("https://example.com", 60, []) == "data60"

    def test_cleanup(self):
        cache = MemoryCache()
        cache.set("https://example.com", 30, [], "data", ttl=0)
        time.sleep(0.1)
        cache.cleanup()
        assert cache.get("https://example.com", 30, []) is None
