"""Debug context mismatch between LLM and Judge."""

from src.retrieval.chain import RAGChain
from src.evaluation.datasets.golden_dataset import GoldenDataset

# Load first query
dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
query = dataset.queries[0]

print("=" * 80)
print("CONTEXT MISMATCH DEBUGGING")
print("=" * 80)
print(f"\nQuery: {query.query}\n")

# Initialize chain
chain = RAGChain()

# Get result
result = chain.query_with_metadata(query.query, session_id="context_debug")
answer = result["answer"]
sources = result["sources"]

print("=" * 80)
print("WHAT THE JUDGE SEES (sources metadata)")
print("=" * 80)
for i, src in enumerate(sources, 1):
    print(f"\nSource {i}:")
    print(f"  Title: {src.get('title', 'N/A')}")
    print(f"  City: {src.get('city', 'N/A')}")
    print(f"  Date: {src.get('date', 'N/A')}")
    print(f"  URL: {src.get('url', 'N/A')}")

print("\n" + "=" * 80)
print("WHAT THE LLM SAW (full context)")
print("=" * 80)
print("\nTo see this, I need to access result['context'] but that's not exposed in query_with_metadata")
print("The LLM sees full event details formatted by format_docs() with addresses, descriptions, etc.")

print("\n" + "=" * 80)
print("THE ANSWER")
print("=" * 80)
print(answer)

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
print("If the answer contains details like:")
print("  - Full addresses (e.g., '141 Rue de Tolbiac')")
print("  - Descriptions")
print("  - Detailed event information")
print("\nBut the judge only sees:")
print("  - Title, City, Date, URL")
print("\nThen the judge will incorrectly flag these as hallucinations!")
print("\nSOLUTION: The judge needs to see the SAME context the LLM saw.")
