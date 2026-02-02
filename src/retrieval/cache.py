"""Simple in-memory caching for query results."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class QueryCache:
    """In-memory cache for query results with TTL."""

    def __init__(self, ttl_minutes: int = 60, max_size: int = 1000):
        """Initialize cache.

        Args:
            ttl_minutes: Time-to-live in minutes (default: 60)
            max_size: Maximum number of cached entries (default: 1000)
        """
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"Initialized QueryCache with TTL={ttl_minutes}min, max_size={max_size}")

    def _generate_key(self, query: str, session_id: str) -> str:
        """Generate cache key from query and session.

        Args:
            query: User query string
            session_id: Session identifier

        Returns:
            Cache key (hash)
        """
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()

        # Create key from query AND session_id to ensure private caches
        key_string = f"{session_id}:{normalized_query}"

        # Generate MD5 hash
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, query: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired.

        Args:
            query: User query string
            session_id: Session identifier

        Returns:
            Cached result dict or None if not found/expired
        """
        key = self._generate_key(query, session_id)

        if key not in self._cache:
            logger.debug(f"Cache MISS for query: {query[:50]}...")
            return None

        entry = self._cache[key]
        cached_at = entry["cached_at"]
        expires_at = cached_at + self.ttl

        # Check if expired
        if datetime.now() > expires_at:
            logger.debug(f"Cache EXPIRED for query: {query[:50]}...")
            del self._cache[key]
            return None

        logger.info(f"Cache HIT for query: {query[:50]}...")
        entry["hits"] = entry.get("hits", 0) + 1
        return entry["result"]

    def set(self, query: str, session_id: str, result: Dict[str, Any]) -> None:
        """Cache a query result.

        Args:
            query: User query string
            session_id: Session identifier
            result: Result to cache
        """
        # If cache is full, remove oldest entry
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["cached_at"])
            logger.debug(f"Cache FULL, evicting oldest entry: {oldest_key}")
            del self._cache[oldest_key]

        key = self._generate_key(query, session_id)

        self._cache[key] = {"result": result, "cached_at": datetime.now(), "query": query, "hits": 0}
        logger.debug(f"Cache SET for query: {query[:50]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({count} entries removed)")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats (size, hit counts, etc.)
        """
        total_hits = sum(entry.get("hits", 0) for entry in self._cache.values())

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "ttl_minutes": self.ttl.total_seconds() / 60,
        }
