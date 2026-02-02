"""Golden dataset loader for evaluation.

This module provides data structures and loaders for the golden evaluation dataset.
Supports both v2.0 (flat queries) and v3.0 (conversations + single_queries) formats.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RelevanceGroundTruth(BaseModel):
    """Ground truth for document relevance."""

    event_id: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str | None = None


class GenerationExpectations(BaseModel):
    """Expected behavior for generation evaluation."""

    must_contain_keywords: list[str] = Field(default_factory=list)
    must_not_contain_keywords: list[str] = Field(default_factory=list)
    must_not_hallucinate: bool = True
    should_ask_clarification: bool = False
    should_refuse_gracefully: bool = False
    expected_language: str | None = None  # "fr" or "en"
    clarification_topics: list[str] = Field(default_factory=list)
    must_reference_specific_event: bool = False


class Query(BaseModel):
    """A single evaluation query with ground truth."""

    id: str
    query: str
    language: str  # "fr" or "en"
    query_type: str  # "simple_search", "complex", "multi_turn", "entity_specific", "edge_case", etc.
    complexity: str = "medium"  # "low", "medium", "high"
    expected_entities: list[str] = Field(default_factory=list)
    expected_categories: list[str] = Field(default_factory=list)
    expected_filters: dict[str, Any] = Field(default_factory=dict)
    relevance_ground_truth: list[RelevanceGroundTruth] = Field(default_factory=list)
    generation_expectations: GenerationExpectations = Field(default_factory=GenerationExpectations)
    # v3.0 conversation context
    session_id: str | None = None  # For multi-turn conversations
    turn_number: int | None = None
    turn_type: str | None = None  # "initial", "refinement", "follow_up", "topic_shift", "clarification_response"
    previous_turn_id: str | None = None
    context_dependency: str | None = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "Q001",
                "query": "Concerts de jazz à Paris en février",
                "language": "fr",
                "query_type": "simple_search",
                "complexity": "low",
                "expected_entities": ["jazz", "Paris", "février"],
                "expected_categories": ["Musique"],
                "expected_filters": {"city": "Paris", "month": 2, "category": "Musique"},
                "relevance_ground_truth": [{"event_id": "evt_001", "relevance_score": 1.0, "reason": "Exact match"}],
                "generation_expectations": {
                    "must_contain_keywords": ["jazz", "Paris"],
                    "must_not_hallucinate": True,
                    "should_ask_clarification": False,
                    "expected_language": "fr",
                },
            }
        }


# v3.0 Conversation Models
class ExpectedBehavior(BaseModel):
    """Expected behavior for a conversation turn."""

    should_ask_clarification: bool = False
    clarification_topics: list[str] = Field(default_factory=list)
    acceptable_actions: list[str] = Field(default_factory=list)
    reason: str | None = None
    should_use_context: bool = False
    inherited_filters: list[str] = Field(default_factory=list)
    new_filters: dict[str, Any] = Field(default_factory=dict)
    should_reset_filters: bool = False
    references_previous_results: bool = False
    expected_action: str | None = None


class ConversationTurn(BaseModel):
    """A single turn in a multi-turn conversation."""

    turn_id: str
    turn_number: int
    turn_type: str  # "initial", "refinement", "follow_up", "topic_shift", "clarification_response"
    query: str
    previous_turn: str | None = None
    context_dependency: str | None = None
    expected_behavior: ExpectedBehavior = Field(default_factory=ExpectedBehavior)
    expected_filters: dict[str, Any] = Field(default_factory=dict)
    generation_expectations: GenerationExpectations = Field(default_factory=GenerationExpectations)


class Conversation(BaseModel):
    """A multi-turn conversation scenario."""

    session_id: str
    description: str
    test_focus: list[str] = Field(default_factory=list)
    language: str
    turns: list[ConversationTurn]


class GoldenDatasetMetadata(BaseModel):
    """Metadata for the golden dataset."""

    version: str
    created_at: str
    description: str | None = None
    total_queries: int | None = None


class GoldenDataset(BaseModel):
    """Complete golden dataset structure.

    Supports both v2.0 (flat queries) and v3.0 (conversations + single_queries) formats.
    """

    version: str
    created_at: str
    description: str | None = None
    # v2.0 format
    queries: list[Query] = Field(default_factory=list)
    # v3.0 format
    conversations: list[Conversation] = Field(default_factory=list)
    single_queries: list[dict[str, Any]] = Field(default_factory=list)
    schema_notes: dict[str, Any] = Field(default_factory=dict)
    evaluation_guidelines: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Convert v3.0 format to unified queries list after initialization."""
        if not self.queries and (self.conversations or self.single_queries):
            self._flatten_v3_to_queries()

    def _flatten_v3_to_queries(self) -> None:
        """Flatten v3.0 conversations and single_queries into unified queries list."""
        flattened = []

        # Process conversations - each turn becomes a Query
        for conv in self.conversations:
            for turn in conv.turns:
                query = Query(
                    id=turn.turn_id,
                    query=turn.query,
                    language=conv.language,
                    query_type=turn.turn_type,
                    complexity="medium",
                    expected_filters=turn.expected_filters,
                    generation_expectations=turn.generation_expectations,
                    session_id=conv.session_id,
                    turn_number=turn.turn_number,
                    turn_type=turn.turn_type,
                    previous_turn_id=turn.previous_turn,
                    context_dependency=turn.context_dependency,
                )
                flattened.append(query)

        # Process single_queries
        for sq in self.single_queries:
            gen_exp_data = sq.get("generation_expectations", {})
            gen_exp = GenerationExpectations(
                must_contain_keywords=gen_exp_data.get("must_contain_keywords", []),
                must_not_contain_keywords=gen_exp_data.get("must_not_contain_keywords", []),
                must_not_hallucinate=gen_exp_data.get("must_not_hallucinate", True),
                should_ask_clarification=gen_exp_data.get("should_ask_clarification", False),
                expected_language=gen_exp_data.get("expected_language"),
                clarification_topics=gen_exp_data.get("clarification_topics", []),
            )
            query = Query(
                id=sq["id"],
                query=sq["query"],
                language=sq.get("language", "fr"),
                query_type=sq.get("query_type", "single"),
                complexity=sq.get("complexity", "medium"),
                expected_filters=sq.get("expected_filters", {}),
                generation_expectations=gen_exp,
            )
            flattened.append(query)

        self.queries = flattened
        logger.info(
            f"Flattened v3.0 dataset: {len(self.conversations)} conversations + "
            f"{len(self.single_queries)} single queries → {len(flattened)} total queries"
        )

    @property
    def total_queries(self) -> int:
        """Get total number of queries."""
        return len(self.queries)

    @classmethod
    def load(cls, dataset_path: str | Path) -> "GoldenDataset":
        """Load golden dataset from JSON file.

        Args:
            dataset_path: Path to golden dataset JSON file

        Returns:
            GoldenDataset instance

        Raises:
            FileNotFoundError: If dataset file doesn't exist
            ValueError: If JSON is invalid or doesn't match schema

        Example:
            >>> dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
            >>> len(dataset.queries)
            50
        """
        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            raise FileNotFoundError(f"Golden dataset not found: {dataset_path}")

        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            dataset = cls(**data)
            logger.info(f"Loaded golden dataset: {dataset.total_queries} queries from {dataset_path}")
            return dataset

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in golden dataset: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load golden dataset: {e}")

    def save(self, dataset_path: str | Path) -> None:
        """Save golden dataset to JSON file.

        Args:
            dataset_path: Path where to save the dataset

        Example:
            >>> dataset.save("data/evaluation/golden_dataset.json")
        """
        dataset_path = Path(dataset_path)
        dataset_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved golden dataset: {self.total_queries} queries to {dataset_path}")

    def get_subset(self, n: int | None = None, query_type: str | None = None) -> "GoldenDataset":
        """Get a subset of the dataset.

        Args:
            n: Number of queries to include (None = all)
            query_type: Filter by query type (None = all types)

        Returns:
            New GoldenDataset with subset of queries

        Example:
            >>> mini = dataset.get_subset(n=10)
            >>> len(mini.queries)
            10
            >>> edge_cases = dataset.get_subset(query_type="edge_case")
        """
        queries = self.queries

        # Filter by type if specified
        if query_type is not None:
            queries = [q for q in queries if q.query_type == query_type]

        # Limit number if specified
        if n is not None:
            queries = queries[:n]

        return GoldenDataset(
            version=self.version,
            created_at=self.created_at,
            description=f"Subset of {self.description or 'golden dataset'} (n={len(queries)})",
            queries=queries,
        )

    def get_by_id(self, query_id: str) -> Query | None:
        """Get a specific query by ID.

        Args:
            query_id: Query ID to find

        Returns:
            Query if found, None otherwise

        Example:
            >>> query = dataset.get_by_id("Q001")
            >>> query.query
            "Concerts de jazz à Paris"
        """
        for query in self.queries:
            if query.id == query_id:
                return query
        return None

    def get_statistics(self) -> dict[str, Any]:
        """Get dataset statistics.

        Returns:
            Dictionary with statistics about the dataset

        Example:
            >>> stats = dataset.get_statistics()
            >>> stats["total_queries"]
            50
            >>> stats["by_type"]["simple_search"]
            10
        """
        by_type = {}
        by_language = {}
        by_complexity = {}

        for query in self.queries:
            # Count by type
            by_type[query.query_type] = by_type.get(query.query_type, 0) + 1
            # Count by language
            by_language[query.language] = by_language.get(query.language, 0) + 1
            # Count by complexity
            by_complexity[query.complexity] = by_complexity.get(query.complexity, 0) + 1

        return {
            "total_queries": self.total_queries,
            "by_type": by_type,
            "by_language": by_language,
            "by_complexity": by_complexity,
            "avg_expected_entities": (
                sum(len(q.expected_entities) for q in self.queries) / self.total_queries
                if self.total_queries > 0
                else 0
            ),
            "queries_with_ground_truth": sum(1 for q in self.queries if len(q.relevance_ground_truth) > 0),
        }

    @classmethod
    def create_empty(cls, version: str = "1.0") -> "GoldenDataset":
        """Create an empty golden dataset.

        Args:
            version: Dataset version

        Returns:
            Empty GoldenDataset

        Example:
            >>> dataset = GoldenDataset.create_empty()
            >>> dataset.queries = [...]
            >>> dataset.save("dataset.json")
        """
        return cls(
            version=version, created_at=datetime.now().isoformat(), description="Golden evaluation dataset", queries=[]
        )
