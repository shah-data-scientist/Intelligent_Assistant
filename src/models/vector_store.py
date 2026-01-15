"""FAISS vector store for event embeddings with metadata filtering."""

import logging
import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from src.config import settings
from src.data.models import Event
from src.data.storage import EventStorage
from src.models.embeddings import EventEmbedder

logger = logging.getLogger(__name__)


class EventVectorStore:
    """FAISS-based vector store for event embeddings with metadata filtering."""

    def __init__(
        self,
        index_path: str | None = None,
        embedder: EventEmbedder | None = None,
        storage: EventStorage | None = None,
    ) -> None:
        """Initialize vector store.

        Args:
            index_path: Path to FAISS index directory
            embedder: EventEmbedder instance (creates new if None)
            storage: EventStorage instance (creates new if None)
        """
        self.index_path = Path(index_path or settings.faiss_index_path)
        self.embedder = embedder or EventEmbedder()
        self.storage = storage or EventStorage()

        self.index: faiss.Index | None = None
        self.event_ids: list[str] = []
        self.dimension = settings.vector_dimension

        logger.info(f"Initialized EventVectorStore with index path: {self.index_path}")

    def build_index(self, events: list[Event] | None = None) -> dict[str, Any]:
        """Build FAISS index from events.

        Args:
            events: List of events to index (fetches from storage if None)

        Returns:
            Statistics about index building
        """
        stats = {
            "events_indexed": 0,
            "dimension": self.dimension,
            "index_type": "IndexFlatIP",  # Inner Product for cosine similarity
        }

        # Get events from storage if not provided
        if events is None:
            logger.info("Fetching events from storage...")
            events = self.storage.get_all_events()
            logger.info(f"Fetched {len(events)} events from storage")

        if not events:
            logger.warning("No events to index")
            return stats

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(events)} events...")
        embeddings = self.embedder.embed_events(events)

        # Convert to numpy array and normalize for cosine similarity
        embeddings_array = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings_array)  # Normalize for cosine similarity

        # Update dimension if needed
        if embeddings_array.shape[1] != self.dimension:
            logger.warning(
                f"Embedding dimension mismatch: expected {self.dimension}, "
                f"got {embeddings_array.shape[1]}"
            )
            self.dimension = embeddings_array.shape[1]
            stats["dimension"] = self.dimension

        # Create FAISS index (Inner Product for normalized vectors = cosine similarity)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings_array)

        # Store event IDs for retrieval
        self.event_ids = [event.event_id for event in events]

        # Update storage with FAISS indices
        logger.info("Updating storage with FAISS indices...")
        for idx, event in enumerate(events):
            self.storage.update_faiss_index(event.event_id, idx)

        stats["events_indexed"] = len(events)
        logger.info(f"Built FAISS index with {len(events)} events")

        return stats

    def save_index(self) -> None:
        """Save FAISS index and metadata to disk."""
        if self.index is None:
            raise ValueError("No index to save. Build index first.")

        self.index_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_file = self.index_path / "index.faiss"
        faiss.write_index(self.index, str(index_file))
        logger.info(f"Saved FAISS index to {index_file}")

        # Save metadata (event IDs)
        metadata_file = self.index_path / "metadata.pkl"
        with open(metadata_file, "wb") as f:
            pickle.dump(
                {
                    "event_ids": self.event_ids,
                    "dimension": self.dimension,
                },
                f,
            )
        logger.info(f"Saved metadata to {metadata_file}")

    def load_index(self) -> None:
        """Load FAISS index and metadata from disk."""
        index_file = self.index_path / "index.faiss"
        metadata_file = self.index_path / "metadata.pkl"

        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")

        # Load FAISS index
        self.index = faiss.read_index(str(index_file))
        logger.info(f"Loaded FAISS index from {index_file}")

        # Load metadata
        with open(metadata_file, "rb") as f:
            metadata = pickle.load(f)
            self.event_ids = metadata["event_ids"]
            self.dimension = metadata["dimension"]

        logger.info(f"Loaded metadata: {len(self.event_ids)} events, dim={self.dimension}")

    def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Event, float]]:
        """Search for similar events using semantic similarity.

        Args:
            query: Search query text
            k: Number of results to return
            metadata_filter: Optional metadata filters (e.g., {"city": "Paris"})

        Returns:
            List of (Event, similarity_score) tuples
        """
        if self.index is None:
            raise ValueError("No index loaded. Build or load index first.")

        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)

        # Search FAISS index (get more results if filtering needed)
        search_k = k * 10 if metadata_filter else k
        distances, indices = self.index.search(query_array, search_k)

        # Retrieve events from storage
        results: list[tuple[Event, float]] = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:  # FAISS returns -1 for no result
                continue

            event_id = self.event_ids[idx]
            event = self.storage.get_event(event_id)

            if event is None:
                logger.warning(f"Event not found in storage: {event_id}")
                continue

            # Apply metadata filtering
            if metadata_filter:
                if not self._matches_filter(event, metadata_filter):
                    continue

            results.append((event, float(distance)))

            if len(results) >= k:
                break

        logger.info(f"Found {len(results)} results for query: {query[:50]}")
        return results

    def _matches_filter(self, event: Event, filters: dict[str, Any]) -> bool:
        """Check if event matches metadata filters.

        Args:
            event: Event to check
            filters: Metadata filters

        Returns:
            True if event matches all filters
        """
        for key, value in filters.items():
            if value is None:
                continue

            if key == "city" and event.location and event.location.city:
                # Case-insensitive partial match
                if value.lower() not in event.location.city.lower():
                    return False
            elif key == "category" and event.category:
                if value.lower() not in event.category.lower():
                    return False
            elif key == "year" and event.start_date:
                if event.start_date.year != value:
                    return False
            elif key == "month" and event.start_date:
                if event.start_date.month != value:
                    return False
            # Add more filter types as needed

        return True

    def close(self) -> None:
        """Close storage connection."""
        self.storage.close()

    def __enter__(self) -> "EventVectorStore":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()


def main() -> None:
    """CLI entry point for building FAISS index."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Building FAISS index from stored events...")

    with EventVectorStore() as vector_store:
        # Build index from all events in storage
        stats = vector_store.build_index()

        logger.info("=" * 80)
        logger.info("Index Building Summary:")
        logger.info(f"  Events indexed: {stats['events_indexed']}")
        logger.info(f"  Vector dimension: {stats['dimension']}")
        logger.info(f"  Index type: {stats['index_type']}")
        logger.info("=" * 80)

        # Save index
        vector_store.save_index()
        logger.info("Index saved successfully")

        # Test search
        logger.info("\nTesting search...")
        query = "concert de musique classique"
        results = vector_store.search(query, k=3)

        logger.info(f"\nTop 3 results for '{query}':")
        for i, (event, score) in enumerate(results, 1):
            logger.info(f"{i}. {event.title} (score: {score:.4f})")
            if event.location and event.location.city:
                logger.info(f"   Location: {event.location.city}")
            if event.start_date:
                logger.info(f"   Date: {event.start_date.strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    main()
