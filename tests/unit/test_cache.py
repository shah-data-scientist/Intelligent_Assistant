"""
FILE: test_cache.py
STATUS: Active
RESPONSIBILITY: Unit tests for query caching.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.retrieval.cache import QueryCache


class TestQueryCache:
    """Test QueryCache class."""

    def test_init_default_values(self):
        """Test cache initialization with default values."""
        cache = QueryCache()
        assert cache.ttl == timedelta(minutes=60)
        assert cache.max_size == 1000
        assert len(cache._cache) == 0

    def test_init_custom_values(self):
        """Test cache initialization with custom values."""
        cache = QueryCache(ttl_minutes=30, max_size=500)
        assert cache.ttl == timedelta(minutes=30)
        assert cache.max_size == 500

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = QueryCache()
        result = {"answer": "Test answer", "sources": []}

        cache.set("test query", "session_1", result)
        cached = cache.get("test query", "session_1")

        assert cached is not None
        assert cached["answer"] == "Test answer"

    def test_get_miss(self):
        """Test cache miss returns None."""
        cache = QueryCache()
        result = cache.get("nonexistent query", "session_1")
        assert result is None

    def test_session_isolation(self):
        """Test that different sessions have isolated caches."""
        cache = QueryCache()

        cache.set("test query", "session_1", {"answer": "Answer 1"})
        cache.set("test query", "session_2", {"answer": "Answer 2"})

        result_1 = cache.get("test query", "session_1")
        result_2 = cache.get("test query", "session_2")

        assert result_1["answer"] == "Answer 1"
        assert result_2["answer"] == "Answer 2"

    def test_case_insensitive(self):
        """Test that queries are case-insensitive."""
        cache = QueryCache()

        cache.set("Test Query", "session_1", {"answer": "Test"})
        result = cache.get("test query", "session_1")

        assert result is not None
        assert result["answer"] == "Test"

    def test_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        cache = QueryCache()

        cache.set("  test query  ", "session_1", {"answer": "Test"})
        result = cache.get("test query", "session_1")

        assert result is not None
        assert result["answer"] == "Test"

    def test_cache_expiry(self):
        """Test that expired entries are not returned."""
        cache = QueryCache(ttl_minutes=1)  # 1 minute TTL

        cache.set("test query", "session_1", {"answer": "Test"})

        # Mock datetime to simulate time passing
        with patch("src.retrieval.cache.datetime") as mock_dt:
            # Set "now" to 2 minutes in the future
            mock_dt.now.return_value = datetime.now() + timedelta(minutes=2)

            result = cache.get("test query", "session_1")
            assert result is None

    def test_max_size_eviction(self):
        """Test that oldest entry is evicted when cache is full."""
        cache = QueryCache(max_size=3)

        cache.set("query1", "session", {"answer": "1"})
        cache.set("query2", "session", {"answer": "2"})
        cache.set("query3", "session", {"answer": "3"})

        # Add fourth entry - should evict oldest
        cache.set("query4", "session", {"answer": "4"})

        assert cache.get("query1", "session") is None  # Evicted
        assert cache.get("query2", "session") is not None
        assert cache.get("query4", "session") is not None

    def test_clear(self):
        """Test clearing the cache."""
        cache = QueryCache()

        cache.set("query1", "session", {"answer": "1"})
        cache.set("query2", "session", {"answer": "2"})

        cache.clear()

        assert cache.get("query1", "session") is None
        assert cache.get("query2", "session") is None
        assert len(cache._cache) == 0

    def test_get_stats(self):
        """Test cache statistics."""
        cache = QueryCache(ttl_minutes=30, max_size=500)

        cache.set("query1", "session", {"answer": "1"})
        cache.set("query2", "session", {"answer": "2"})
        cache.get("query1", "session")  # Hit
        cache.get("query1", "session")  # Hit

        stats = cache.get_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 500
        assert stats["total_hits"] == 2
        assert stats["ttl_minutes"] == 30

    def test_hit_counter(self):
        """Test that hit counter increments."""
        cache = QueryCache()

        cache.set("test query", "session", {"answer": "Test"})

        # Access multiple times
        for _ in range(5):
            cache.get("test query", "session")

        stats = cache.get_stats()
        assert stats["total_hits"] == 5


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_different_queries_different_keys(self):
        """Test that different queries produce different keys."""
        cache = QueryCache()

        key1 = cache._generate_key("query1", "session")
        key2 = cache._generate_key("query2", "session")

        assert key1 != key2

    def test_different_sessions_different_keys(self):
        """Test that different sessions produce different keys."""
        cache = QueryCache()

        key1 = cache._generate_key("query", "session1")
        key2 = cache._generate_key("query", "session2")

        assert key1 != key2

    def test_same_query_and_session_same_key(self):
        """Test that same query and session produce same key."""
        cache = QueryCache()

        key1 = cache._generate_key("query", "session")
        key2 = cache._generate_key("query", "session")

        assert key1 == key2

    def test_key_is_md5_hash(self):
        """Test that generated key is valid MD5 hash."""
        cache = QueryCache()
        key = cache._generate_key("test", "session")

        # MD5 hash is 32 hex characters
        assert len(key) == 32
        assert all(c in "0123456789abcdef" for c in key)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
