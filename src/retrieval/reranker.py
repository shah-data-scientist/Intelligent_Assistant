"""Cross-encoder reranking for improved document ordering."""

import logging
from typing import List, Tuple
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class DocumentReranker:
    """Rerank retrieved documents using cross-encoder for better precision."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"):
        """Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        logger.info(f"DocumentReranker initialized with model: {model_name}")

    def _load_model(self):
        """Lazy load the cross-encoder model."""
        if self.model is None:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder model loaded successfully")

    def rerank(
        self,
        query: str,
        documents: List[Tuple[any, float]],
        top_k: int = None
    ) -> List[Tuple[any, float]]:
        """Rerank documents using cross-encoder.

        Args:
            query: Search query
            documents: List of (document, score) tuples from initial retrieval
            top_k: Number of top documents to return (None = return all)

        Returns:
            Reranked list of (document, new_score) tuples
        """
        if not documents:
            return documents

        # Lazy load model
        self._load_model()

        # Extract document texts and original objects
        doc_objects = []
        doc_texts = []
        for doc, score in documents:
            doc_objects.append(doc)
            # Handle both Event objects and LangChain Documents
            if hasattr(doc, 'to_text'):
                doc_texts.append(doc.to_text(include_metadata_prefix=False))
            elif hasattr(doc, 'page_content'):
                doc_texts.append(doc.page_content)
            else:
                doc_texts.append(str(doc))

        # Create query-document pairs
        pairs = [[query, text] for text in doc_texts]

        # Get cross-encoder scores
        logger.debug(f"Reranking {len(pairs)} documents with cross-encoder")
        scores = self.model.predict(pairs)

        # Combine with original documents and sort by new scores
        reranked = list(zip(doc_objects, scores))
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Return top k if specified
        if top_k is not None:
            reranked = reranked[:top_k]

        logger.debug(f"Reranking complete, returning {len(reranked)} documents")
        return reranked


# Global singleton instance (lazy loaded)
_global_reranker = None


def get_reranker() -> DocumentReranker:
    """Get global reranker instance.

    Returns:
        DocumentReranker singleton
    """
    global _global_reranker
    if _global_reranker is None:
        _global_reranker = DocumentReranker()
    return _global_reranker
