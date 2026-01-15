"""Test semantic search relevance across different categories."""

import logging
from src.models.vector_store import EventVectorStore

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def test_semantic_queries():
    queries = [
        "Exposition d'art contemporain à Paris",
        "Pièce de théâtre ou spectacle vivant",
        "Concert de jazz en plein air",
        "Activités sportives et ateliers pour enfants",
        "Conférence sur l'histoire ou la littérature"
    ]

    with EventVectorStore() as vector_store:
        vector_store.load_index()
        
        for query in queries:
            logger.info(f"\n" + "="*50)
            logger.info(f"QUERY: {query}")
            logger.info("="*50)
            
            results = vector_store.search(query, k=3)
            
            if not results:
                logger.info("No results found.")
                continue
                
            for i, (event, score) in enumerate(results, 1):
                logger.info(f"{i}. [{score:.4f}] {event.title}")
                logger.info(f"   Category: {event.category}")
                logger.info(f"   Location: {event.location.city if event.location else 'Unknown'}")
                logger.info(f"   Date: {event.start_date.strftime('%Y-%m-%d') if event.start_date else 'Unknown'}")
                # Brief snippet of description to check relevance
                desc = (event.description or "")[:100] + "..."
                logger.info(f"   Desc: {desc}")

if __name__ == "__main__":
    test_semantic_queries()
