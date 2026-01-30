"""Enrich golden dataset with conversational patterns and proper annotations.

This script:
1. Adds 15-20 new queries based on feedback analysis
2. Adds "reason" field to ground truth annotations
3. Links conversational multi-turn queries
4. Adds edge cases and failure modes

Usage:
    python scripts/enrich_golden_dataset.py
    python scripts/enrich_golden_dataset.py --dry-run  # Preview changes without saving
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_golden_dataset(path: str) -> dict[str, Any]:
    """Load existing golden dataset."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_new_queries() -> list[dict[str, Any]]:
    """Generate new queries based on feedback analysis.

    Returns 15-20 new queries focusing on:
    - Conversational multi-turn chains
    - Accessibility edge cases
    - Bilingual variations
    - Free events filtering
    - Nationality/ethnicity specific queries
    """
    new_queries = [
        # Q119: Finnish artists query (from conversational pattern)
        {
            "id": "Q119",
            "query": "Tell me about Finnish artists and exhibitions",
            "language": "en",
            "query_type": "entity_specific",
            "complexity": "medium",
            "expected_entities": ["Finnish", "artists", "exhibitions"],
            "expected_categories": ["Arts", "Musique"],
            "expected_filters": {},
            "conversational_context": {
                "parent_query_id": "Q001",
                "turn_number": 2,
                "chain_description": "Follow-up to jazz concerts query, testing nationality-specific search"
            },
            "relevance_ground_truth": [],  # To be populated from actual search
            "generation_expectations": {
                "must_contain_keywords": ["Finnish", "artist"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "en"
            },
            "annotation_comments": "Real user query from eval sessions. Tests nationality filtering and bilingual capability."
        },

        # Q120: Accessibility query (from conversational pattern)
        {
            "id": "Q120",
            "query": "Événements gratuits accessibles aux personnes à mobilité réduite",
            "language": "fr",
            "query_type": "metadata_heavy",
            "complexity": "high",
            "expected_entities": ["gratuits", "accessibles", "mobilité réduite"],
            "expected_categories": [],
            "expected_filters": {
                "conditions": "free",
                "accessibility": "wheelchair"
            },
            "conversational_context": {
                "parent_query_id": "Q119",
                "turn_number": 3,
                "chain_description": "Follow-up testing accessibility and price filtering"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["gratuit", "accessible"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": True,  # May have no results
                "expected_language": "fr"
            },
            "annotation_comments": "Real user query. Tests edge case where accessibility data is sparse (0% coverage). Should handle gracefully with no results or suggest verification."
        },

        # Q121: Free events general query
        {
            "id": "Q121",
            "query": "Free concerts this weekend",
            "language": "en",
            "query_type": "simple_search",
            "complexity": "medium",
            "expected_entities": ["free", "concerts", "weekend"],
            "expected_categories": ["Musique"],
            "expected_filters": {
                "conditions": "free",
                "temporal": "weekend"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["free", "concert"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "en"
            },
            "annotation_comments": "Tests free event filtering and temporal interpretation (weekend)"
        },

        # Q122: Bilingual equivalent of Q121
        {
            "id": "Q122",
            "query": "Concerts gratuits ce week-end",
            "language": "fr",
            "query_type": "simple_search",
            "complexity": "medium",
            "expected_entities": ["gratuits", "concerts", "week-end"],
            "expected_categories": ["Musique"],
            "expected_filters": {
                "conditions": "free",
                "temporal": "weekend"
            },
            "bilingual_equivalent": "Q121",
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["gratuit", "concert"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "fr"
            },
            "annotation_comments": "Bilingual pair with Q121. Should return 70%+ overlap in results."
        },

        # Q123: Family-friendly events
        {
            "id": "Q123",
            "query": "Activités pour enfants à Paris ce weekend",
            "language": "fr",
            "query_type": "metadata_heavy",
            "complexity": "medium",
            "expected_entities": ["enfants", "Paris", "weekend"],
            "expected_categories": ["Spectacles", "Loisirs"],
            "expected_filters": {
                "city": "Paris",
                "age_range": "children",
                "temporal": "weekend"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["enfant", "Paris"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "fr"
            },
            "annotation_comments": "Tests age range filtering. Age data coverage is 40-57%, so some events may lack age info."
        },

        # Q124: Specific venue query
        {
            "id": "Q124",
            "query": "What's happening at Jass Club Paris this month?",
            "language": "en",
            "query_type": "entity_specific",
            "complexity": "medium",
            "expected_entities": ["Jass Club", "Paris", "this month"],
            "expected_categories": ["Musique"],
            "expected_filters": {
                "venue": "Jass Club",
                "city": "Paris",
                "temporal": "current_month"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["Jass Club", "Paris"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "en"
            },
            "annotation_comments": "Venue-specific query. Jass Club is common in dataset (many events at 141 Rue de Tolbiac)."
        },

        # Q125: Broad geographic query
        {
            "id": "Q125",
            "query": "Tous les événements en Île-de-France",
            "language": "fr",
            "query_type": "simple_search",
            "complexity": "low",
            "expected_entities": ["Île-de-France"],
            "expected_categories": [],
            "expected_filters": {
                "region": "Île-de-France"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": [],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "fr"
            },
            "annotation_comments": "Broad query - should return many events. Tests system's handling of large result sets."
        },

        # Q126: No results expected
        {
            "id": "Q126",
            "query": "Japanese opera for 5-year-olds in Bondy on February 29",
            "language": "en",
            "query_type": "entity_specific",
            "complexity": "high",
            "expected_entities": ["Japanese", "opera", "5-year-olds", "Bondy", "February 29"],
            "expected_categories": ["Spectacles"],
            "expected_filters": {
                "city": "Bondy",
                "date": "2026-02-29",
                "age_max": 5
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": [],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": True,
                "expected_language": "en"
            },
            "annotation_comments": "Edge case: no results expected (overly specific, Feb 29 doesn't exist in 2026). Tests graceful failure handling."
        },

        # Q127: Ambiguous temporal query
        {
            "id": "Q127",
            "query": "Expositions cette semaine",
            "language": "fr",
            "query_type": "simple_search",
            "complexity": "low",
            "expected_entities": ["expositions", "cette semaine"],
            "expected_categories": ["Arts"],
            "expected_filters": {
                "temporal": "this_week"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["exposition"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "fr"
            },
            "annotation_comments": "Tests temporal parsing for relative dates ('cette semaine' = this week)."
        },

        # Q128: Multiple filters
        {
            "id": "Q128",
            "query": "Free outdoor music festivals in Paris this summer",
            "language": "en",
            "query_type": "metadata_heavy",
            "complexity": "high",
            "expected_entities": ["free", "outdoor", "music", "festivals", "Paris", "summer"],
            "expected_categories": ["Musique"],
            "expected_filters": {
                "city": "Paris",
                "conditions": "free",
                "temporal": "summer",
                "event_type": "festival"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["free", "music", "Paris"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "en"
            },
            "annotation_comments": "Complex multi-filter query. Tests combination of price, season, location, and event type."
        },

        # Q129: Negation query
        {
            "id": "Q129",
            "query": "Événements à Paris mais pas de concerts",
            "language": "fr",
            "query_type": "simple_search",
            "complexity": "medium",
            "expected_entities": ["Paris", "pas de concerts"],
            "expected_categories": ["Arts", "Spectacles", "Loisirs"],
            "expected_filters": {
                "city": "Paris",
                "exclude_category": "Musique"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["Paris"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "fr"
            },
            "annotation_comments": "Tests negation handling ('pas de concerts' = no concerts). Should exclude music category."
        },

        # Q130: Conversational refinement
        {
            "id": "Q130",
            "query": "Something closer to the 13th arrondissement",
            "language": "en",
            "query_type": "entity_specific",
            "complexity": "high",
            "expected_entities": ["13th arrondissement"],
            "expected_categories": [],
            "expected_filters": {
                "arrondissement": "75013",
                "proximity": "nearby"
            },
            "conversational_context": {
                "parent_query_id": "Q001",
                "turn_number": 4,
                "chain_description": "Refinement query assuming context from previous jazz query. Tests geographic proximity."
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": [],
                "must_not_hallucinate": True,
                "should_ask_clarification": True,  # May need context from previous query
                "should_refuse_gracefully": False,
                "expected_language": "en"
            },
            "annotation_comments": "Conversational refinement. Requires context from previous query to understand what 'something' refers to."
        },

        # Q131: Specific date range
        {
            "id": "Q131",
            "query": "Concerts du 15 au 20 février",
            "language": "fr",
            "query_type": "simple_search",
            "complexity": "medium",
            "expected_entities": ["concerts", "15", "20", "février"],
            "expected_categories": ["Musique"],
            "expected_filters": {
                "start_date": "2026-02-15",
                "end_date": "2026-02-20"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["concert"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "fr"
            },
            "annotation_comments": "Tests specific date range parsing (du...au = from...to)."
        },

        # Q132: Price range query
        {
            "id": "Q132",
            "query": "Affordable theater shows under 20 euros",
            "language": "en",
            "query_type": "metadata_heavy",
            "complexity": "medium",
            "expected_entities": ["affordable", "theater", "under 20 euros"],
            "expected_categories": ["Spectacles"],
            "expected_filters": {
                "max_price": 20
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["theater"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": True,  # Price data may not be available
                "expected_language": "en"
            },
            "annotation_comments": "Tests price range filtering. Price data coverage unknown, may need graceful handling."
        },

        # Q133: Vague query
        {
            "id": "Q133",
            "query": "Something fun this weekend",
            "language": "en",
            "query_type": "simple_search",
            "complexity": "low",
            "expected_entities": ["fun", "weekend"],
            "expected_categories": [],
            "expected_filters": {
                "temporal": "weekend"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": [],
                "must_not_hallucinate": True,
                "should_ask_clarification": True,  # Very vague query
                "should_refuse_gracefully": False,
                "expected_language": "en"
            },
            "annotation_comments": "Very vague query. Tests system's ability to handle ambiguity and potentially ask for clarification."
        },

        # Q134: Cultural event specific
        {
            "id": "Q134",
            "query": "Expositions d'art contemporain à Versailles",
            "language": "fr",
            "query_type": "entity_specific",
            "complexity": "medium",
            "expected_entities": ["expositions", "art contemporain", "Versailles"],
            "expected_categories": ["Arts"],
            "expected_filters": {
                "city": "Versailles",
                "event_type": "exposition"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["exposition", "Versailles"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "fr"
            },
            "annotation_comments": "Tests specific city outside Paris (Versailles) and art subcategory (contemporary)."
        },

        # Q135: Night events
        {
            "id": "Q135",
            "query": "Late night events in Paris after 10 PM",
            "language": "en",
            "query_type": "metadata_heavy",
            "complexity": "medium",
            "expected_entities": ["late night", "Paris", "after 10 PM"],
            "expected_categories": [],
            "expected_filters": {
                "city": "Paris",
                "start_time_after": "22:00"
            },
            "relevance_ground_truth": [],
            "generation_expectations": {
                "must_contain_keywords": ["Paris"],
                "must_not_hallucinate": True,
                "should_ask_clarification": False,
                "should_refuse_gracefully": False,
                "expected_language": "en"
            },
            "annotation_comments": "Tests time-of-day filtering. Event start times may not always be available in metadata."
        }
    ]

    logger.info(f"Generated {len(new_queries)} new queries")
    return new_queries


def add_reasons_to_ground_truth(queries: list[dict]) -> int:
    """Add 'reason' field to ground truth annotations where missing.

    Returns:
        Number of annotations updated
    """
    updated_count = 0

    for query in queries:
        if "relevance_ground_truth" in query:
            for truth in query["relevance_ground_truth"]:
                if truth.get("reason") is None:
                    # Generate a generic reason based on relevance score
                    score = truth.get("relevance_score", 0.0)
                    if score >= 0.9:
                        truth["reason"] = "Exact match for query criteria"
                    elif score >= 0.7:
                        truth["reason"] = "Good match with minor detail mismatch"
                    elif score >= 0.5:
                        truth["reason"] = "Partial match, some criteria met"
                    else:
                        truth["reason"] = "Marginal relevance, limited match"

                    updated_count += 1

    logger.info(f"Added 'reason' field to {updated_count} ground truth annotations")
    return updated_count


def enrich_dataset(input_path: str, output_path: str, dry_run: bool = False) -> dict[str, Any]:
    """Enrich golden dataset with new queries and annotations.

    Args:
        input_path: Path to existing golden dataset
        output_path: Path to save enriched dataset
        dry_run: If True, preview changes without saving

    Returns:
        Enriched dataset dict
    """
    logger.info(f"Loading dataset from {input_path}")
    dataset = load_golden_dataset(input_path)

    # Get statistics before enrichment
    original_query_count = len(dataset.get("queries", []))
    logger.info(f"Original dataset: {original_query_count} queries")

    # Add new queries
    new_queries = get_new_queries()
    dataset["queries"].extend(new_queries)

    # Add reasons to ground truth
    updated_annotations = add_reasons_to_ground_truth(dataset["queries"])

    # Update metadata
    if "metadata" not in dataset:
        dataset["metadata"] = {}

    dataset["metadata"]["last_updated"] = datetime.utcnow().isoformat()
    dataset["metadata"]["total_queries"] = len(dataset["queries"])
    dataset["metadata"]["enrichment_date"] = datetime.utcnow().isoformat()
    dataset["metadata"]["new_queries_added"] = len(new_queries)
    dataset["metadata"]["annotations_updated"] = updated_annotations

    # Summary
    logger.info(f"\nEnrichment Summary:")
    logger.info(f"  Original queries: {original_query_count}")
    logger.info(f"  New queries added: {len(new_queries)}")
    logger.info(f"  Total queries: {len(dataset['queries'])}")
    logger.info(f"  Annotations updated: {updated_annotations}")

    # Save or preview
    if dry_run:
        logger.info("\nDRY RUN - No changes saved")
        logger.info(f"Preview of first new query: {new_queries[0]['id']} - {new_queries[0]['query']}")
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        logger.info(f"\nEnriched dataset saved to: {output_path}")

    return dataset


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Enrich golden dataset with conversational patterns and annotations"
    )
    parser.add_argument(
        "--input",
        default="data/evaluation/golden_dataset.json",
        help="Input golden dataset path"
    )
    parser.add_argument(
        "--output",
        default="data/evaluation/golden_dataset.json",
        help="Output path for enriched dataset"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving"
    )
    args = parser.parse_args()

    try:
        enrich_dataset(args.input, args.output, dry_run=args.dry_run)
        return 0

    except Exception as e:
        logger.error(f"Enrichment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
