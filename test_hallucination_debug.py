"""Debug script to test what sources are retrieved vs what is generated."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.retrieval.chain import RAGChain
import logging

logging.basicConfig(level=logging.WARNING)

# Test Query Q007 - Japanese art exhibitions
chain = RAGChain()

# Use query_with_sources to get both response and sources
print("="*80)
print("QUERY: Japanese art exhibitions in Île-de-France")
print("="*80)

# Get response
response = chain.query('Japanese art exhibitions in Île-de-France', session_id='debug_hallucination')
print("\n=== GENERATED RESPONSE ===")
print(response)

# Get sources through retriever directly
from src.models.retrieval import EventRetriever
retriever = EventRetriever(vector_store=chain.vector_store)
source_docs = retriever.get_relevant_documents('Japanese art exhibitions in Île-de-France')

print("\n\n=== SOURCE DOCUMENTS ===")
source_docs = source_docs if source_docs else []
print(f"Number of sources: {len(source_docs)}")

for i, doc in enumerate(source_docs[:5], 1):
    print(f"\n--- Source {i} ---")
    print(doc.page_content[:500])
    if len(doc.page_content) > 500:
        print("...")
