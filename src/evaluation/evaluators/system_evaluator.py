"""System-wide evaluation orchestrator.

Orchestrates retrieval and generation evaluation for end-to-end system assessment.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.evaluation.datasets.golden_dataset import GoldenDataset
from src.evaluation.evaluators.retrieval_evaluator import RetrievalEvaluator
from src.evaluation.evaluators.generation_evaluator import GenerationEvaluator
from src.retrieval.retriever import EventRetriever
from src.retrieval.chain import RAGChain
from src.evaluation.metrics.generation import LLMAsJudge
from src.config import settings

logger = logging.getLogger(__name__)


class EvaluationReport(BaseModel):
    """Complete evaluation report."""

    timestamp: str
    dataset_version: str
    total_queries: int

    # System info
    faiss_index_events: int | None = None
    llm_model: str | None = None
    embedding_model: str | None = None

    # Retrieval metrics
    retrieval_metrics: dict[str, Any]

    # Generation metrics
    generation_metrics: dict[str, Any]

    # Latency analysis
    latency_analysis: dict[str, Any]

    # Overall status
    overall_status: dict[str, Any]

    # Detailed results
    per_query_results: list[dict[str, Any]]


class SystemEvaluator:
    """End-to-end system evaluation runner."""

    def __init__(
        self,
        retriever: EventRetriever | None = None,
        rag_chain: RAGChain | None = None,
        judge_backend: str = "mistral",
        **judge_kwargs: Any
    ):
        """Initialize system evaluator.

        Args:
            retriever: EventRetriever instance (creates one if None)
            rag_chain: RAGChain instance (creates one if None)
            judge_backend: LLM backend for LLM-as-a-Judge
            **judge_kwargs: Additional kwargs for judge
        """
        # Initialize components if not provided
        if retriever is None:
            from src.models.vector_store import EventVectorStore
            vector_store = EventVectorStore()
            try:
                vector_store.load_index()
                logger.info(f"Loaded FAISS index: {len(vector_store.event_ids)} events")
            except Exception as e:
                logger.warning(f"Could not load FAISS index: {e}. Retrieval evaluation will fail.")
            retriever = EventRetriever(vector_store=vector_store)

        if rag_chain is None:
            rag_chain = RAGChain()

        self.retrieval_evaluator = RetrievalEvaluator(retriever)
        self.generation_evaluator = GenerationEvaluator(
            rag_chain,
            judge_backend=judge_backend,
            **judge_kwargs
        )

        logger.info(f"Initialized SystemEvaluator with judge backend: {judge_backend}")

    def run_full_evaluation(
        self,
        golden_dataset_path: str | Path | None = None,
        retrieval_k: int = 5,
        session_id: str | None = None
    ) -> EvaluationReport:
        """Run complete system evaluation.

        Args:
            golden_dataset_path: Path to golden dataset (uses default if None)
            retrieval_k: Number of docs to retrieve
            session_id: Session ID for generation evaluation

        Returns:
            EvaluationReport with all metrics and results
        """
        # Generate unique session ID to avoid chat history contamination
        if session_id is None:
            import uuid
            session_id = f"eval_{uuid.uuid4().hex[:12]}"

        # Load golden dataset
        if golden_dataset_path is None:
            golden_dataset_path = settings.golden_dataset_path

        logger.info(f"Loading golden dataset from: {golden_dataset_path}")
        golden_dataset = GoldenDataset.load(golden_dataset_path)

        logger.info(f"\n{'='*60}")
        logger.info(f"Starting Full System Evaluation")
        logger.info(f"{'='*60}")
        logger.info(f"Dataset: {golden_dataset.total_queries} queries")
        logger.info(f"Retrieval k: {retrieval_k}")
        logger.info(f"Session ID: {session_id}")

        # Run retrieval evaluation
        logger.info(f"\n{'-'*60}")
        logger.info("Phase 1: Retrieval Evaluation")
        logger.info(f"{'-'*60}")
        retrieval_results = self.retrieval_evaluator.evaluate_dataset(
            golden_dataset,
            k=retrieval_k
        )

        # Run generation evaluation
        logger.info(f"\n{'-'*60}")
        logger.info("Phase 2: Generation Quality Evaluation")
        logger.info(f"{'-'*60}")
        generation_results = self.generation_evaluator.evaluate_dataset(
            golden_dataset,
            session_id=session_id
        )

        # Combine per-query results
        combined_results = []
        for i in range(len(golden_dataset.queries)):
            combined = {
                **retrieval_results["per_query_results"][i],
                **generation_results["per_query_results"][i],
            }
            combined_results.append(combined)

        # Latency analysis
        latencies = [r.get("latency_ms", 0) for r in combined_results if "error" not in r]
        latencies.sort()

        latency_analysis = {}
        if latencies:
            latency_analysis = {
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p50_latency_ms": latencies[len(latencies) // 2],
                "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[-1],
                "p99_latency_ms": latencies[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[-1],
                "sla_compliance_rate": sum(1 for lat in latencies if lat < settings.evaluation_latency_sla_ms) / len(latencies),
            }

        # Overall status
        quality_score = generation_results["aggregated_metrics"].get("avg_quality_score", 0.0)
        avg_latency = latency_analysis.get("avg_latency_ms", 0)

        quality_pass = quality_score >= settings.evaluation_quality_sla
        latency_pass = avg_latency < settings.evaluation_latency_sla_ms
        overall_pass = quality_pass and latency_pass

        overall_status = {
            "quality_score": quality_score,
            "quality_sla": settings.evaluation_quality_sla,
            "quality_pass": quality_pass,
            "avg_latency_ms": avg_latency,
            "latency_sla_ms": settings.evaluation_latency_sla_ms,
            "latency_pass": latency_pass,
            "overall_pass": overall_pass,
        }

        # Create evaluation report
        report = EvaluationReport(
            timestamp=datetime.now().isoformat(),
            dataset_version=golden_dataset.version,
            total_queries=golden_dataset.total_queries,
            retrieval_metrics=retrieval_results["aggregated_metrics"],
            generation_metrics=generation_results["aggregated_metrics"],
            latency_analysis=latency_analysis,
            overall_status=overall_status,
            per_query_results=combined_results
        )

        # Log summary
        logger.info(f"\n{'='*60}")
        logger.info("Evaluation Complete - Summary")
        logger.info(f"{'='*60}")
        logger.info(f"Quality Score: {quality_score:.3f} (SLA: {settings.evaluation_quality_sla}) - {'✅ PASS' if quality_pass else '❌ FAIL'}")
        logger.info(f"Avg Latency: {avg_latency:.0f}ms (SLA: {settings.evaluation_latency_sla_ms}ms) - {'✅ PASS' if latency_pass else '❌ FAIL'}")
        logger.info(f"Overall: {'✅ PASS' if overall_pass else '❌ FAIL'}")
        logger.info(f"{'='*60}\n")

        return report
