"""Test query refinement with critical keyword preservation."""

import logging
from src.retrieval.chain import RAGChain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize chain
chain = RAGChain()

# Test queries that should preserve critical keywords
test_queries = [
    "Concerts classiques pour enfants de 6-12 ans le week-end dans le 75",
    "Jazz shows NOT classical music in Paris",
    "Free accessible events with wheelchair access",
    "Theater with subtitles and audio description",
    "Contemporary art from Finnish artists"
]

print("="*80)
print("QUERY REFINEMENT TEST - Critical Keyword Preservation")
print("="*80)

for query in test_queries:
    print(f"\nOriginal: {query}")
    refined = chain.refinement_chain.invoke({"question": query})
    print(f"Refined:  {refined}")

    # Check if critical keywords are preserved
    keywords_check = []
    if "classique" in query.lower() or "classical" in query.lower():
        if "classique" in refined.lower() or "classical" in refined.lower():
            keywords_check.append("✅ Genre preserved (classique/classical)")
        else:
            keywords_check.append("❌ Genre LOST (classique/classical)")

    if "jazz" in query.lower():
        if "jazz" in refined.lower():
            keywords_check.append("✅ Genre preserved (jazz)")
        else:
            keywords_check.append("❌ Genre LOST (jazz)")

    if "enfants" in query.lower() or "children" in query.lower():
        if "enfants" in refined.lower() or "children" in refined.lower():
            keywords_check.append("✅ Age group preserved")
        else:
            keywords_check.append("❌ Age group LOST")

    if "accessible" in query.lower():
        if "accessible" in refined.lower():
            keywords_check.append("✅ Accessibility preserved")
        else:
            keywords_check.append("❌ Accessibility LOST")

    if keywords_check:
        for check in keywords_check:
            print(f"  {check}")

print("\n" + "="*80)
