"""Debug faithfulness scores by examining actual responses."""

import logging
from src.evaluation.datasets.golden_dataset import GoldenDataset
from src.retrieval.chain import RAGChain
from src.evaluation.llm_backends import MistralBackend
from src.evaluation.metrics.generation import LLMAsJudge

logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Load first 3 queries
dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
queries = dataset.queries[:3]

# Initialize RAG chain
chain = RAGChain()

# Initialize judge
judge_backend = MistralBackend()
judge = LLMAsJudge(backend=judge_backend)

print("="*80)
print("FAITHFULNESS DEBUGGING")
print("="*80)

for i, query in enumerate(queries, 1):
    print(f"\n{'='*80}")
    print(f"Query {i}: {query.query}")
    print(f"Type: {query.query_type}")
    print(f"{'='*80}\n")

    # Generate response
    result = chain.query_with_metadata(query.query, session_id="faithfulness_debug")
    answer = result["answer"]
    sources = result["sources"]

    print(f"ANSWER:\n{answer}\n")
    print(f"\nSOURCES ({len(sources)} events):")
    for j, source in enumerate(sources, 1):
        print(f"{j}. {source['title']} in {source.get('city', 'N/A')}")
        print(f"   URL: {source.get('url', 'N/A')}")

    # Prepare context for faithfulness check
    context = "\n\n".join([
        f"Source {j}: {source['title']}"
        for j, source in enumerate(sources, 1)
    ])

    # Evaluate faithfulness
    try:
        faithfulness_result = judge.evaluate_faithfulness(
            question=query.query,
            answer=answer,
            context=context
        )

        print(f"\n--- FAITHFULNESS EVALUATION ---")
        print(f"Score: {faithfulness_result['score']:.2f}")
        print(f"Reasoning: {faithfulness_result.get('reasoning', 'N/A')}")

        if faithfulness_result['score'] < 0.7:
            print("\n⚠️ LOW FAITHFULNESS - Potential Issues:")
            print("- Check if answer includes information not in sources")
            print("- Check if URLs/dates/details are hallucinated")
            print("- Check if answer properly cites sources")

    except Exception as e:
        logger.error(f"Faithfulness evaluation failed: {e}")
        print(f"\nERROR: Could not evaluate faithfulness: {e}")

    print(f"\n{'='*80}\n")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("If faithfulness is consistently low, common causes:")
print("1. Context not being passed correctly to LLM")
print("2. Source attribution not working as expected")
print("3. LLM ignoring grounding instructions")
print("4. Evaluation context doesn't match what was provided to LLM")
