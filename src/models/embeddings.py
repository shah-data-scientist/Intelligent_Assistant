"""Mistral embeddings client for generating event embeddings."""

import logging
from typing import Any

from langchain_mistralai import MistralAIEmbeddings

from src.config import settings
from src.data.models import Event

logger = logging.getLogger(__name__)


class EventEmbedder:
    """Generate embeddings for cultural events using Mistral."""

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
        """
        text = event.to_text()
        embedding = self.embeddings.embed_query(text)
        return embedding

    def embed_events(self, events: list[Event]) -> list[list[float]]:
        """Generate embeddings for multiple events in batch.

        Args:
            events: List of events to embed

        Returns:
            List of embedding vectors
        """
        if not events:
            return []

        texts = [event.to_text() for event in events]
        logger.info(f"Generating embeddings for {len(texts)} events")

        embeddings = self.embeddings.embed_documents(texts)
        logger.info(f"Generated {len(embeddings)} embeddings")

        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Query embedding vector
        """
        embedding = self.embeddings.embed_query(query)
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
