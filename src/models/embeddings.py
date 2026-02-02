"""Mistral embeddings client for generating event embeddings.

Uses Mistral's mistral-embed model which produces 1024-dimensional embeddings.
This allows using the same API key as the LLM (Mistral).
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from langchain_mistralai import MistralAIEmbeddings

from src.config import settings
from src.data.models import Event

logger = logging.getLogger(__name__)


# ========================================
# EMBEDDING-SPECIFIC ERRORS
# ========================================


class EmbeddingError(Exception):
    """Base exception for embedding errors."""

    pass


class EmbeddingRateLimitError(EmbeddingError):
    """Rate limit exceeded for embedding API."""

    pass


class EmbeddingAuthError(EmbeddingError):
    """Authentication error for embedding API."""

    pass


def _handle_embedding_error(error: Exception, context: str = "embedding") -> None:
    """Convert raw exceptions to clear error messages.

    Args:
        error: The original exception
        context: Description of what was being done

    Raises:
        EmbeddingRateLimitError: If rate limited
        EmbeddingAuthError: If authentication failed
        EmbeddingError: For other errors with clear message
    """
    error_str = str(error).lower()

    # Rate limit errors
    if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
        msg = f"Mistral embedding API rate limit exceeded during {context}. Wait a few minutes and try again."
        logger.error(f"[EMBED] {msg}")
        raise EmbeddingRateLimitError(msg) from error

    # Payment/quota errors
    if "402" in error_str or "payment required" in error_str or "quota" in error_str:
        msg = f"Mistral embedding API quota exhausted during {context}. Check your Mistral account billing."
        logger.error(f"[EMBED] {msg}")
        raise EmbeddingRateLimitError(msg) from error

    # Authentication errors
    if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
        msg = f"Mistral embedding API authentication failed during {context}. Check your MISTRAL_API_KEY."
        logger.error(f"[EMBED] {msg}")
        raise EmbeddingAuthError(msg) from error

    # Network/connection errors
    if "connection" in error_str or "timeout" in error_str or "network" in error_str:
        msg = f"Network error connecting to Mistral embedding API during {context}: {error}"
        logger.error(f"[EMBED] {msg}")
        raise EmbeddingError(msg) from error

    # Unknown error - still provide context
    msg = f"Embedding error during {context}: {error}"
    logger.error(f"[EMBED] {msg}")
    raise EmbeddingError(msg) from error


# Global embedding cache for query embeddings
_EMBEDDING_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_MINUTES = 120  # 2 hours
_CACHE_MAX_SIZE = 500


class EventEmbedder:
    """Generate embeddings for cultural events using Mistral.

    Uses Mistral's mistral-embed model which produces 1024-dimensional embeddings.
    This allows using the same API key as the LLM.
    """

    def __init__(
        self,
        model: str = "mistral-embed",
        api_key: str | None = None,
    ) -> None:
        """Initialize Mistral embeddings client.

        Args:
            model: Mistral embedding model name
            api_key: Mistral API key (defaults to settings)
        """
        self.model = model
        self.api_key = api_key or settings.mistral_api_key
        self.embeddings = MistralAIEmbeddings(
            model=model,
            api_key=self.api_key,
        )
        logger.info(f"Initialized EventEmbedder with model: {model}")

    def embed_event(self, event: Event) -> list[float]:
        """Generate embedding for a single event.

        Args:
            event: Event to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingRateLimitError: If rate limited
            EmbeddingAuthError: If authentication failed
            EmbeddingError: For other errors
        """
        text = event.to_text()
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            _handle_embedding_error(e, f"embed_event({event.event_id})")

    def embed_events(self, events: list[Event]) -> list[list[float]]:
        """Generate embeddings for multiple events in batch.

        Args:
            events: List of events to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingRateLimitError: If rate limited
            EmbeddingAuthError: If authentication failed
            EmbeddingError: For other errors
        """
        if not events:
            return []

        texts = [event.to_text() for event in events]
        logger.info(f"Generating embeddings for {len(texts)} events")

        try:
            embeddings = self.embeddings.embed_documents(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            _handle_embedding_error(e, f"embed_events({len(events)} events)")

    def embed_query(self, query: str, use_cache: bool = True) -> list[float]:
        """Generate embedding for a search query with caching.

        Args:
            query: Search query text
            use_cache: Whether to use embedding cache (default: True)

        Returns:
            Query embedding vector
        """
        global _EMBEDDING_CACHE

        # Normalize query for cache key (SHA-256 for security compliance)
        normalized = query.lower().strip()
        cache_key = hashlib.sha256(normalized.encode()).hexdigest()

        # Check cache
        if use_cache and cache_key in _EMBEDDING_CACHE:
            entry = _EMBEDDING_CACHE[cache_key]
            cached_at = entry["cached_at"]
            if datetime.now() - cached_at < timedelta(minutes=_CACHE_TTL_MINUTES):
                logger.debug(f"[EMBED-CACHE] HIT for query: {query[:40]}...")
                return entry["embedding"]
            else:
                # Expired
                del _EMBEDDING_CACHE[cache_key]

        # Cache miss - generate embedding
        try:
            embedding = self.embeddings.embed_query(query)
        except Exception as e:
            _handle_embedding_error(e, f"embed_query('{query[:30]}...')")

        # Store in cache
        if use_cache:
            # Evict oldest if full
            if len(_EMBEDDING_CACHE) >= _CACHE_MAX_SIZE:
                oldest_key = min(_EMBEDDING_CACHE.keys(), key=lambda k: _EMBEDDING_CACHE[k]["cached_at"])
                del _EMBEDDING_CACHE[oldest_key]
                logger.debug("[EMBED-CACHE] Evicted oldest entry")

            _EMBEDDING_CACHE[cache_key] = {"embedding": embedding, "cached_at": datetime.now(), "query": query[:50]}
            logger.debug(f"[EMBED-CACHE] SET for query: {query[:40]}...")

        return embedding


def main() -> None:
    """CLI entry point for testing embeddings."""
    logging.basicConfig(level=logging.INFO)

    # Test with sample event
    from datetime import datetime
    from src.data.models import EventLocation

    sample_event = Event(
        event_id="test-1",
        title="Concert de Jazz",
        description="Un concert de jazz moderne au coeur de Paris",
        category="Music",
        location=EventLocation(
            city="Paris",
            postal_code="75001",
        ),
        start_date=datetime(2026, 6, 15, 20, 0),
    )

    embedder = EventEmbedder()

    # Test single embedding
    logger.info("Testing single event embedding...")
    embedding = embedder.embed_event(sample_event)
    logger.info(f"Embedding dimension: {len(embedding)}")
    logger.info(f"Sample values: {embedding[:5]}")

    # Test query embedding
    logger.info("\nTesting query embedding...")
    query = "concert de musique à Paris"
    query_embedding = embedder.embed_query(query)
    logger.info(f"Query embedding dimension: {len(query_embedding)}")


if __name__ == "__main__":
    main()
