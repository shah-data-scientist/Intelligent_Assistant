"""FAISS vector store for event embeddings with metadata filtering."""

import logging
import pickle
from pathlib import Path
from typing import Any, List, Dict, Tuple

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from src.config import settings
from src.data.models import Event
from src.data.storage import EventStorage
from src.models.embeddings import EventEmbedder
from src.utils.geo import CityLocator, haversine_distance
from src.utils.language import tokenize_for_bm25, LanguageCode

logger = logging.getLogger(__name__)


class EventVectorStore:
    """Hybrid vector store (FAISS + BM25) for event retrieval."""

    def __init__(
        self,
        index_path: str | None = None,
        embedder: EventEmbedder | None = None,
        storage: EventStorage | None = None,
        default_language: LanguageCode = "fr"
    ) -> None:
        """Initialize vector store.

        Args:
            index_path: Path to FAISS index directory
            embedder: EventEmbedder instance (creates new if None)
            storage: EventStorage instance (creates new if None)
            default_language: Default language for BM25 tokenization (default: "fr")
        """
        self.index_path = Path(index_path or settings.faiss_index_path)
        self.embedder = embedder or EventEmbedder()
        self.storage = storage or EventStorage()
        self.city_locator = CityLocator()  # Initialize geospatial locator
        self.default_language = default_language  # For language-aware BM25

        self.index: faiss.Index | None = None
        self.bm25: BM25Okapi | None = None
        self.event_ids: list[str] = []
        self.dimension = settings.vector_dimension

        logger.info(f"Initialized EventVectorStore with index path: {self.index_path}")

    def build_index(self, events: list[Event] | None = None) -> dict[str, Any]:
        """Build FAISS and BM25 indices from events.

        Args:
            events: List of events to index (fetches from storage if None)

        Returns:
            Statistics about index building
        """
        stats = {
            "events_indexed": 0,
            "dimension": self.dimension,
            "index_type": "Hybrid (FAISS + BM25)",
        }

        # Get events from storage if not provided
        if events is None:
            logger.info("Fetching events from storage...")
            events = self.storage.get_all_events()
            logger.info(f"Fetched {len(events)} events from storage")

        if not events:
            logger.warning("No events to index")
            return stats

        # --- FAISS Indexing ---
        logger.info(f"Generating embeddings for {len(events)} events...")
        embeddings = self.embedder.embed_events(events)

        # Convert to numpy array and normalize for cosine similarity
        embeddings_array = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings_array)

        # Update dimension if needed
        if embeddings_array.shape[1] != self.dimension:
            self.dimension = embeddings_array.shape[1]
            stats["dimension"] = self.dimension

        # Create FAISS index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings_array)

        # --- BM25 Indexing ---
        logger.info("Building BM25 index...")
        tokenized_corpus = [self._tokenize_event(e) for e in events]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Store event IDs for retrieval
        self.event_ids = [event.event_id for event in events]

        # Update storage with FAISS indices
        for idx, event in enumerate(events):
            self.storage.update_faiss_index(event.event_id, idx)

        stats["events_indexed"] = len(events)
        logger.info(f"Built Hybrid Index with {len(events)} events")

        return stats

    def _tokenize_event(self, event: Event, language: LanguageCode | None = None) -> list[str]:
        """Create token list for BM25 from event fields with language-aware processing.

        This method now uses language-aware tokenization including:
        - Accent normalization (café → cafe)
        - Stopword removal (le, la, the, a, etc.)
        - Stemming (concerts → concert)

        Args:
            event: Event to tokenize
            language: Language code ("fr" or "en"), uses default_language if None

        Returns:
            List of processed tokens
        """
        lang = language or self.default_language

        # Combine event text fields
        text = f"{event.title} {event.description or ''} {event.scraped_content or ''}"
        if event.location and event.location.city:
            text += f" {event.location.city}"
        if event.tags:
            text += f" {' '.join(event.tags)}"

        # Use language-aware tokenization (normalize, stopword removal, stemming)
        return tokenize_for_bm25(text, lang)

    def save_index(self) -> None:
        """Save FAISS index, BM25 index, and metadata to disk."""
        if self.index is None:
            raise ValueError("No index to save. Build index first.")

        self.index_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_file = self.index_path / "index.faiss"
        faiss.write_index(self.index, str(index_file))
        
        # Save BM25 index and Metadata
        metadata_file = self.index_path / "metadata.pkl"
        with open(metadata_file, "wb") as f:
            pickle.dump(
                {
                    "event_ids": self.event_ids,
                    "dimension": self.dimension,
                    "bm25": self.bm25
                },
                f,
            )
        logger.info(f"Saved indices to {self.index_path}")

    def load_index(self) -> None:
        """Load FAISS index and metadata from disk."""
        index_file = self.index_path / "index.faiss"
        metadata_file = self.index_path / "metadata.pkl"

        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")

        self.index = faiss.read_index(str(index_file))
        
        with open(metadata_file, "rb") as f:
            metadata = pickle.load(f)
            self.event_ids = metadata["event_ids"]
            self.dimension = metadata["dimension"]
            self.bm25 = metadata.get("bm25") # Optional for backward compatibility

        logger.info(f"Loaded Hybrid Index: {len(self.event_ids)} events")

    def search_raw(
        self,
        query: str,
        k: int = 100,
        language: LanguageCode | None = None
    ) -> list[tuple[Event, float]]:
        """Search and return RAW similarity results (no filtering, no sorting).

        REFACTORED (Phase 2 & 4): This method makes the vector_store "dumb".
        It ONLY does semantic search (vector + BM25 fusion + keyword boosting).
        NO filtering, NO geo-sorting, NO post-processing.

        ENHANCED (Phase 10): Now supports language-aware BM25 tokenization.

        Filtering is now done in RetrievalOrchestrator using SearchFilters.matches().

        Args:
            query: Search query string
            k: Number of raw candidates to return (default: 100)
            language: Language code for BM25 tokenization (default: self.default_language)

        Returns:
            List of (Event, score) tuples, sorted by similarity
        """
        lang = language or self.default_language
        if self.index is None:
            raise ValueError("No index loaded.")

        # 1. Vector Search
        query_embedding = self.embedder.embed_query(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)

        search_k = k * 2  # Fetch extra for deduplication
        v_distances, v_indices = self.index.search(query_array, search_k)

        vector_results = {}
        for idx, dist in zip(v_indices[0], v_distances[0]):
            if idx != -1:
                vector_results[self.event_ids[idx]] = float(dist)

        # 2. BM25 Search (with language-aware tokenization)
        bm25_results = {}
        if self.bm25:
            # Use same language-aware tokenization as indexing
            tokenized_query = tokenize_for_bm25(query, lang)
            doc_scores = self.bm25.get_scores(tokenized_query)
            top_n = np.argsort(doc_scores)[::-1][:search_k]
            for idx in top_n:
                if doc_scores[idx] > 0:
                    bm25_results[self.event_ids[idx]] = doc_scores[idx]

        # 3. Keyword Boosting (BEFORE fusion)
        boost_keywords = self._extract_significant_keywords(query)
        if boost_keywords:
            logger.debug(f"Applying keyword boosting for: {boost_keywords}")
            vector_results = self._apply_keyword_boost(vector_results, boost_keywords)
            bm25_results = self._apply_keyword_boost(bm25_results, boost_keywords)

        # 4. RRF Fusion
        fused_scores_list = self._reciprocal_rank_fusion(vector_results, bm25_results)

        # 5. Fetch Events (NO filtering, just deduplication)
        results = []
        seen_event_keys = set()

        for event_id, score in fused_scores_list:
            event = self.storage.get_event(event_id)
            if not event:
                continue

            # Deduplicate by Title + City + Date
            event_date = event.start_date.date() if event.start_date else "no-date"
            event_key = f"{event.title}|{event.location.city if event.location else ''}|{event_date}".lower()

            if event_key in seen_event_keys:
                continue

            seen_event_keys.add(event_key)
            results.append((event, score))

            if len(results) >= k:
                break

        logger.debug(f"search_raw returning {len(results)} unique events")
        return results

    def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        enable_hybrid: bool = True,
        candidate_pool: int | None = None
    ) -> list[tuple[Event, float]]:
        """Search using Hybrid Fusion (Vector + BM25) + Geo Priority.

        LEGACY METHOD: This method is kept for backward compatibility.
        New code should use search_raw() + RetrievalOrchestrator instead.

        Args:
            query: Search query
            k: Number of results
            metadata_filter: Filters to apply (legacy)
            enable_hybrid: Enable hybrid search (unused, always True)
            candidate_pool: Size of candidate pool

        Returns:
            List of (Event, score) tuples
        """
        if self.index is None:
            raise ValueError("No index loaded.")

        # 1. Vector Search
        query_embedding = self.embedder.embed_query(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        # Retrieve more candidates for filtering/fusion
        # Default to a safe large number if not specified
        search_k = candidate_pool or (k * 200)
        v_distances, v_indices = self.index.search(query_array, search_k)
        
        vector_results = {}
        for idx, dist in zip(v_indices[0], v_distances[0]):
            if idx != -1:
                vector_results[self.event_ids[idx]] = float(dist)

        # 2. BM25 Search (if available)
        bm25_results = {}
        if self.bm25:
            tokenized_query = query.lower().split()
            # Get raw scores
            doc_scores = self.bm25.get_scores(tokenized_query)
            # Get top N indices
            top_n = np.argsort(doc_scores)[::-1][:search_k]
            for idx in top_n:
                if doc_scores[idx] > 0:
                    bm25_results[self.event_ids[idx]] = doc_scores[idx]

        # 2.5 KEYWORD BOOSTING (BEFORE fusion) - REFACTORED
        # Boost vector and BM25 scores separately BEFORE combining them
        # This preserves the RRF score distribution
        boost_keywords = self._extract_significant_keywords(query)
        if boost_keywords:
            logger.debug(f"Applying keyword boosting for: {boost_keywords}")
            vector_results = self._apply_keyword_boost(vector_results, boost_keywords)
            bm25_results = self._apply_keyword_boost(bm25_results, boost_keywords)

        # 3. Fusion (RRF) - operates on boosted scores
        fused_scores_list = self._reciprocal_rank_fusion(vector_results, bm25_results)
        # No need to sort here, RRF already returns sorted list

        # 4. Fetch Events & Filter
        candidates = []
        seen_event_keys = set()
        
        for event_id, score in fused_scores_list:
            event = self.storage.get_event(event_id)
            if not event: continue
            
            # Apply Filters
            if metadata_filter and not self._matches_filter(event, metadata_filter):
                continue
            
            # Deduplicate by Title + City + Date
            # Use date only (not time) for broader deduplication
            event_date = event.start_date.date() if event.start_date else "no-date"
            event_key = f"{event.title}|{event.location.city if event.location else ''}|{event_date}".lower()
            
            if event_key in seen_event_keys:
                continue
                
            seen_event_keys.add(event_key)
            candidates.append((event, score))
            
            # Stop if we have enough unique candidates (fetch extra for reranking if needed)
            # We want at least k unique ones, but fetch more for broad listings
            if len(candidates) >= 100: 
                break

        # 5. Apply Geo Priority Logic (if city filter exists)
        if metadata_filter and "city" in metadata_filter:
            return self._apply_geo_priority(candidates, metadata_filter["city"], k)

        # Return top k unique results
        return candidates[:k]

    def _extract_significant_keywords(self, query: str) -> List[str]:
        """Extract significant keywords from query for boosting.

        Filters out:
        - Very short words (<4 chars)
        - Common French stop words
        - Generic words

        Returns:
            List of significant keywords
        """
        # French stop words to exclude
        stop_words = {
            "dans", "pour", "avec", "sans", "sous", "vers", "chez", "plus",
            "cette", "cela", "tous", "tout", "vous", "nous", "leur", "sont",
            "mais", "elle", "leur", "même", "peut", "fait", "très", "bien",
            "the", "and", "for", "with", "from", "that", "this", "have",
            "events", "événements", "event", "événement"  # Too generic
        }

        words = query.lower().split()
        keywords = [
            w for w in words
            if len(w) >= 4 and w not in stop_words
        ]
        return keywords

    def _apply_keyword_boost(
        self,
        results: Dict[str, float],
        keywords: List[str],
        boost_factor: float = 1.5
    ) -> Dict[str, float]:
        """Apply keyword boost to search results.

        Args:
            results: Dict of event_id -> score
            keywords: List of keywords to check
            boost_factor: Multiplier for matching docs (default: 1.5x)

        Returns:
            Dict with boosted scores
        """
        boosted = {}
        for event_id, score in results.items():
            event = self.storage.get_event(event_id)
            if event:
                text = f"{event.title} {event.description or ''}".lower()
                # Check if ANY keyword matches
                if any(kw in text for kw in keywords):
                    boosted[event_id] = score * boost_factor
                else:
                    boosted[event_id] = score
            else:
                boosted[event_id] = score
        return boosted

    def _reciprocal_rank_fusion(
        self,
        vector_results: Dict[str, float],
        bm25_results: Dict[str, float],
        k: int = 60
    ) -> List[Tuple[str, float]]:
        """Combine results using Reciprocal Rank Fusion.

        REFACTORED: Now operates on pre-boosted scores.

        Args:
            vector_results: Vector search results (possibly boosted)
            bm25_results: BM25 search results (possibly boosted)
            k: RRF parameter (default: 60)

        Returns:
            Sorted list of (event_id, fused_score) tuples
        """
        fusion_scores = {}

        # Rank Vector Results
        sorted_vector = sorted(vector_results.items(), key=lambda x: x[1], reverse=True)
        for rank, (doc_id, _) in enumerate(sorted_vector):
            if doc_id not in fusion_scores:
                fusion_scores[doc_id] = 0
            fusion_scores[doc_id] += 1 / (k + rank + 1)

        # Rank BM25 Results
        if bm25_results:
            sorted_bm25 = sorted(bm25_results.items(), key=lambda x: x[1], reverse=True)
            for rank, (doc_id, _) in enumerate(sorted_bm25):
                if doc_id not in fusion_scores:
                    fusion_scores[doc_id] = 0
                fusion_scores[doc_id] += 1 / (k + rank + 1)

        # Sort by fused score
        return sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)

    def _apply_geo_priority(self, candidates: List[Tuple[Event, float]], target_city: str, k: int):
        """Prioritize exact city matches, then nearby events sorted by distance."""
        # Skip prioritization if it's a broad regional term
        if target_city.lower().strip() in ["ile de france", "ile-de-france", "idf", "paris region"]:
            return candidates[:k]

        target_coords = self.city_locator.get_coords(target_city)
        if not target_coords:
            return candidates[:k] # Fallback

        exact_matches = []
        nearby_matches = []

        for event, score in candidates:
            if event.location and event.location.city and target_city.lower() in event.location.city.lower():
                exact_matches.append((event, score))
            else:
                dist = float('inf')
                if event.location and event.location.coordinates:
                    # Handle coordinates as dict (Pydantic model)
                    lat = event.location.coordinates.get("lat")
                    lon = event.location.coordinates.get("lon")
                    if lat is not None and lon is not None:
                        dist = haversine_distance(
                            target_coords[0], target_coords[1],
                            lat, lon
                        )
                nearby_matches.append((event, score, dist))

        # Sort nearby by distance first
        nearby_matches.sort(key=lambda x: x[2])
        
        # Combine
        final_results = exact_matches + [(e, s) for e, s, d in nearby_matches]
        return final_results[:k]

    def _matches_filter(self, event: Event, filters: dict[str, Any]) -> bool:
        """Check if event matches metadata filters."""
        for key, value in filters.items():
            if value is None: continue

            if key == "city":
                # Geo-spatial filtering
                target_city = value.lower().strip()
                logger.debug(f"Filtering by city: {target_city}")
                
                # Skip filtering if it's a broad regional term rather than a specific city
                if target_city in ["ile de france", "ile-de-france", "idf", "paris region"]:
                    logger.debug("Skipping city filter for regional term")
                    continue
                    
                target_coords = self.city_locator.get_coords(target_city)
                logger.debug(f"Target coords for {target_city}: {target_coords}")
                
                if target_coords:
                    # Radius search (Expanded to 50km for neighbor fallback)
                    # Check for coordinates in event.location
                    if not event.location or not event.location.coordinates:
                        # Fallback to string match if no coords
                        if not event.location or not event.location.city: return False
                        if value.lower() not in event.location.city.lower(): return False
                    else:
                        # Check distance
                        lat = event.location.coordinates.get("lat")
                        lon = event.location.coordinates.get("lon")
                        
                        if lat is None or lon is None:
                             return False

                        dist = haversine_distance(
                            target_coords[0], target_coords[1],
                            lat, lon
                        )
                        if dist > 50.0: return False # 50km radius
                else:
                    if not event.location or not event.location.city: return False
                    if value.lower() not in event.location.city.lower(): return False

            elif key == "is_free" and value is True:
                if not event.conditions or "gratuit" not in event.conditions.lower(): return False

            elif key == "age" and isinstance(value, (int, float)):
                if event.age_min is not None and event.age_min > value: return False
                if event.age_max is not None and event.age_max < value: return False

            elif key == "category" and event.category:
                if value.lower() not in event.category.lower() and event.category.lower() not in value.lower(): 
                    return False
            elif key == "year" and event.start_date:
                if isinstance(value, list):
                    if event.start_date.year not in value: return False
                elif event.start_date.year != value: return False
            elif key == "month" and event.start_date:
                if isinstance(value, list):
                    if event.start_date.month not in value: return False
                elif event.start_date.month != value: return False
            elif key == "day" and event.start_date:
                if isinstance(value, list):
                    if event.start_date.day not in value: return False
                elif event.start_date.day != value: return False

            # Date Range Filtering
            elif key == "date_min" and event.start_date:
                # Value should be a datetime.date object or string ISO format
                if isinstance(value, str):
                    from datetime import date
                    try:
                        value = date.fromisoformat(value)
                    except ValueError:
                        continue
                
                # Ensure value is a date or datetime object before comparing
                from datetime import date, datetime
                if not isinstance(value, (date, datetime)):
                    continue

                # Handle comparison between datetime and date
                event_date = event.start_date.date() if hasattr(event.start_date, 'date') else event.start_date
                if event_date < value: return False

            elif key == "date_max" and event.start_date:
                if isinstance(value, str):
                    from datetime import date
                    try:
                        value = date.fromisoformat(value)
                    except ValueError:
                        continue
                
                # Ensure value is a date or datetime object before comparing
                from datetime import date, datetime
                if not isinstance(value, (date, datetime)):
                    continue

                # Handle comparison between datetime and date
                event_date = event.start_date.date() if hasattr(event.start_date, 'date') else event.start_date
                if event_date > value: return False

        return True

    def close(self) -> None:
        self.storage.close()

    def __enter__(self) -> "EventVectorStore":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with EventVectorStore() as vector_store:
        vector_store.build_index()
        vector_store.save_index()

if __name__ == "__main__":
    main()