"""Retriever component for cultural events RAG system."""

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from pydantic import ConfigDict

from src.models.vector_store import EventVectorStore
from src.data.models import Event

logger = logging.getLogger(__name__)


class EventRetriever(BaseRetriever):
    """LangChain compatible retriever for cultural events."""

    vector_store: Any  # EventVectorStore instance
    k: int = 5
    _cache: dict = {}  # Simple in-memory cache

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Retrieve documents relevant to the query.

        Args:
            query: Search query
            run_manager: Callback manager

        Returns:
            List of LangChain Documents
        """
        # Check cache
        if query in self._cache:
            logger.info("Cache hit for query")
            return self._cache[query]

        # For now, we perform simple semantic search.
        # In the future, we can add query analysis to extract metadata filters.
        results = self.vector_store.search(query, k=self.k)

        documents = []
        for event, score in results:
            doc = self._event_to_document(event, score)
            documents.append(doc)

        logger.info(f"Retrieved {len(documents)} documents for query: {query[:50]}...")
        
        # Update cache (limit size to avoid memory leaks - simple FIFO)
        if len(self._cache) > 1000:
            self._cache.pop(next(iter(self._cache)))
        self._cache[query] = documents
        
        return documents

    def _event_to_document(self, event: Event, score: float) -> Document:
        """Convert an Event object to a LangChain Document.

        Args:
            event: Event object
            score: Similarity score

        Returns:
            LangChain Document
        """
        # Create a rich text representation for the LLM
        page_content = event.to_text()

        # Include metadata for filtering and reference
        metadata = {
            "event_id": event.event_id,
            "title": event.title,
            "category": event.category,
            "city": event.location.city if event.location else None,
            "start_date": event.start_date.isoformat() if event.start_date else None,
            "url": event.url,
            "score": score,
        }

        return Document(page_content=page_content, metadata=metadata)

    def search_with_filters(
        self, query: str, k: int = 5, metadata_filter: dict[str, Any] | None = None
    ) -> list[Document]:
        """Search with explicit metadata filters.

        Args:
            query: Search query
            k: Number of results
            metadata_filter: Dictionary of filters (e.g., {"city": "Paris"})

        Returns:
            List of LangChain Documents
        """
        results = self.vector_store.search(query, k=k, metadata_filter=metadata_filter)
        
        documents = []
        for event, score in results:
            documents.append(self._event_to_document(event, score))
            
        return documents
