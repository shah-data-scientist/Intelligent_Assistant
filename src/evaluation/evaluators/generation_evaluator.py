"""Generation quality evaluation component.

Evaluates generation quality against golden dataset using LLM-as-a-Judge.
"""

import logging
import time
import uuid
from typing import Any

from src.evaluation.metrics.generation import LLMAsJudge
from src.evaluation.datasets.golden_dataset import GoldenDataset, Query
from src.retrieval.chain import RAGChain

logger = logging.getLogger(__name__)


class GenerationEvaluator:
    """Evaluate generation quality against golden dataset."""

    def __init__(
        self, rag_chain: RAGChain, judge: LLMAsJudge | None = None, judge_backend: str = "mistral", **judge_kwargs: Any
    ):
        """Initialize generation evaluator.

        Args:
            rag_chain: RAGChain instance to evaluate
            judge: Pre-configured LLMAsJudge (optional)
            judge_backend: Backend type if judge not provided
            **judge_kwargs: Additional kwargs for judge initialization
        """
        self.rag_chain = rag_chain
        self.judge = judge or LLMAsJudge(backend_type=judge_backend, **judge_kwargs)
        logger.info(f"Initialized GenerationEvaluator with judge backend: {self.judge.backend.get_name()}")

    def evaluate_query(self, query: Query, session_id: str = "evaluation_session") -> dict[str, Any]:
        """Evaluate generation quality for a single query.

        Args:
            query: Query from golden dataset
            session_id: Session ID for RAG chain

        Returns:
            Dictionary with generation quality metrics
        """
        start_time = time.time()

        try:
            # Generate answer with simple retry for rate limits
            try:
                result = self.rag_chain.query_with_metadata(question=query.query, session_id=session_id)
            except Exception as e:
                logger.warning(f"Initial query failed: {e}. Retrying in 5s...")
                time.sleep(5)
                result = self.rag_chain.query_with_metadata(question=query.query, session_id=session_id)

            latency_ms = (time.time() - start_time) * 1000

            answer = result.get("answer", "")
            sources = result.get("sources", [])

            # Format sources for judge - use full_text if available (same as LLM saw)
            sources_text = []
            for src in sources:
                # Use full event text if available for accurate faithfulness evaluation
                if "full_text" in src and src["full_text"]:
                    sources_text.append(src["full_text"])
                else:
                    # Fallback to basic metadata if full_text not available
                    source_text = f"Title: {src.get('title', 'N/A')}\n"
                    source_text += f"City: {src.get('city', 'N/A')}\n"
                    source_text += f"Date: {src.get('date', 'N/A')}\n"
                    source_text += f"URL: {src.get('url', 'N/A')}"
                    sources_text.append(source_text)

            # Evaluate with LLM-as-a-Judge
            evaluation = self.judge.evaluate_generation(query=query.query, answer=answer, sources=sources_text)

            # Check against expectations
            expectations = query.generation_expectations
            keywords_present = all(kw.lower() in answer.lower() for kw in expectations.must_contain_keywords)

            metrics_result = {
                "query_id": query.id,
                "query": query.query,
                "query_type": query.query_type,
                "answer": answer,
                "num_sources": len(sources),
                "latency_ms": latency_ms,
                "faithfulness_score": evaluation["faithfulness_score"],
                "relevancy_score": evaluation["relevancy_score"],
                "language_consistent": evaluation["language_consistent"],
                "quality_score": evaluation["quality_score"],
                "keywords_present": keywords_present,
                "expected_language_match": (
                    expectations.expected_language is None
                    or evaluation["language_details"]["answer_language"] == expectations.expected_language
                ),
                "faithfulness_details": evaluation["faithfulness_details"],
                "relevancy_details": evaluation["relevancy_details"],
            }

            logger.debug(
                f"Query {query.id}: quality={metrics_result['quality_score']:.2f}, " f"latency={latency_ms:.0f}ms"
            )

            return metrics_result

        except Exception as e:
            logger.error(f"Generation evaluation failed for query {query.id}: {e}")
            return {
                "query_id": query.id,
                "query": query.query,
                "query_type": query.query_type,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
            }

    def evaluate_dataset(self, golden_dataset: GoldenDataset, session_id: str | None = None) -> dict[str, Any]:
        """Evaluate generation quality across entire golden dataset.

        Args:
            golden_dataset: GoldenDataset to evaluate against
            session_id: Base session ID (ignored - each conversation gets its own session)

        Returns:
            Dictionary with aggregated metrics and per-query results
        """
        logger.info(f"Starting generation evaluation on {golden_dataset.total_queries} queries")

        per_query_results = []
        total_latency = 0.0
        faithfulness_scores = []
        relevancy_scores = []
        quality_scores = []
        language_consistent_count = 0

        # Track active sessions to reset RAG chain state between conversations
        current_session_id = None

        for i, query in enumerate(golden_dataset.queries, 1):
            # Use query's session_id for multi-turn conversations
            # Generate unique session_id for single queries (no session_id)
            query_session_id = query.session_id or f"eval_single_{uuid.uuid4().hex[:8]}"

            # Log when we switch to a new conversation
            if query_session_id != current_session_id:
                if current_session_id is not None:
                    logger.info(f"Switching to new session: {query_session_id}")
                    # Clear previous session's filters to avoid bleeding
                    if current_session_id in self.rag_chain._session_filters:
                        del self.rag_chain._session_filters[current_session_id]
                current_session_id = query_session_id

            logger.debug(
                f"Evaluating query {i}/{golden_dataset.total_queries}: {query.id} (session: {query_session_id})"
            )

            result = self.evaluate_query(query, session_id=query_session_id)
            per_query_results.append(result)

            # Accumulate metrics
            if "error" not in result:
                total_latency += result["latency_ms"]
                faithfulness_scores.append(result["faithfulness_score"])
                relevancy_scores.append(result["relevancy_score"])
                quality_scores.append(result["quality_score"])
                if result["language_consistent"]:
                    language_consistent_count += 1

            # Pace the evaluation to respect API limits
            time.sleep(5)

        # Calculate aggregated metrics
        num_successful = len([r for r in per_query_results if "error" not in r])

        aggregated = {
            "total_queries": golden_dataset.total_queries,
            "successful_queries": num_successful,
            "avg_latency_ms": total_latency / num_successful if num_successful > 0 else 0,
        }

        if num_successful > 0:
            aggregated.update(
                {
                    "avg_faithfulness": sum(faithfulness_scores) / len(faithfulness_scores),
                    "avg_relevancy": sum(relevancy_scores) / len(relevancy_scores),
                    "avg_quality_score": sum(quality_scores) / len(quality_scores),
                    "language_consistency_rate": language_consistent_count / num_successful,
                }
            )
        else:
            aggregated.update(
                {
                    "avg_faithfulness": 0.0,
                    "avg_relevancy": 0.0,
                    "avg_quality_score": 0.0,
                    "language_consistency_rate": 0.0,
                }
            )

        logger.info(
            f"Generation evaluation complete: "
            f"quality={aggregated['avg_quality_score']:.2f}, "
            f"faithfulness={aggregated['avg_faithfulness']:.2f}, "
            f"avg_latency={aggregated['avg_latency_ms']:.0f}ms"
        )

        return {"aggregated_metrics": aggregated, "per_query_results": per_query_results}
