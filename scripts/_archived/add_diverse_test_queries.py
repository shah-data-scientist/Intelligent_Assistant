"""Add diverse test queries to evaluation dataset."""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.datasets.golden_dataset import GoldenDataset, Query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# New diverse test queries
NEW_QUERIES = [
    # Price-focused queries
    Query(
        id="Q_FREE_001",
        query="Événements culturels gratuits à Paris ce week-end",
        language="fr",
        query_type="price_filter",
        complexity="medium",
        expected_filters={"price": "free", "city": "Paris", "time": "weekend"},
        relevance_ground_truth=[]  # To be filled
    ),
    Query(
        id="Q_FREE_002",
        query="Free concerts in February",
        language="en",
        query_type="price_filter",
        complexity="medium",
        expected_filters={"price": "free", "category": "concerts", "month": 2},
        relevance_ground_truth=[]
    ),

    # Accessibility-focused queries
    Query(
        id="Q_ACCESS_001",
        query="Spectacles accessibles en fauteuil roulant à Paris",
        language="fr",
        query_type="accessibility",
        complexity="medium",
        expected_categories=["theater"],
        expected_filters={"accessibility": "wheelchair", "city": "Paris"},
        relevance_ground_truth=[]
    ),
    Query(
        id="Q_ACCESS_002",
        query="Theater with subtitles or sign language interpretation",
        language="en",
        query_type="accessibility",
        complexity="high",
        expected_categories=["theater"],
        expected_filters={"accessibility": "subtitles OR sign language"},
        relevance_ground_truth=[]
    ),

    # Genre diversity - Electronic/Pop/Rock
    Query(
        id="Q_GENRE_ELEC_001",
        query="Concerts électroniques ou techno à Paris",
        language="fr",
        query_type="genre_search",
        complexity="simple",
        expected_categories=["concerts"],
        expected_filters={"genre": "electronic OR techno", "city": "Paris"},
        relevance_ground_truth=[]
    ),
    Query(
        id="Q_GENRE_POP_001",
        query="Pop or rock concerts in Île-de-France",
        language="en",
        query_type="genre_search",
        complexity="simple",
        expected_categories=["concerts"],
        expected_filters={"genre": "pop OR rock"},
        relevance_ground_truth=[]
    ),

    # Suburb/regional queries
    Query(
        id="Q_SUBURB_001",
        query="Événements culturels à Versailles en novembre",
        language="fr",
        query_type="location_specific",
        complexity="medium",
        expected_filters={"city": "Versailles", "month": 11},
        relevance_ground_truth=[]
    ),
    Query(
        id="Q_SUBURB_002",
        query="Theater shows in suburbs (banlieue) of Paris",
        language="en",
        query_type="location_specific",
        complexity="medium",
        expected_categories=["theater"],
        expected_filters={"location": "suburbs"},
        relevance_ground_truth=[]
    ),

    # Multi-lingual queries
    Query(
        id="Q_LANG_001",
        query="Events with English descriptions or in English",
        language="en",
        query_type="language",
        complexity="high",
        expected_filters={"language": "English"},
        relevance_ground_truth=[]
    ),

    # Age-specific queries
    Query(
        id="Q_AGE_001",
        query="Spectacles pour tout public (enfants et adultes)",
        language="fr",
        query_type="age_filter",
        complexity="medium",
        expected_filters={"age": "all ages"},
        relevance_ground_truth=[]
    ),
    Query(
        id="Q_AGE_002",
        query="Adult-only comedy shows in Paris",
        language="en",
        query_type="age_filter",
        complexity="high",
        expected_categories=["comedy"],
        expected_filters={"age": "adults only", "city": "Paris"},
        relevance_ground_truth=[]
    ),

    # Combined criteria (complex)
    Query(
        id="Q_COMPLEX_001",
        query="Free accessible workshops for families on weekends",
        language="en",
        query_type="multi_criteria",
        complexity="high",
        expected_categories=["workshops"],
        expected_filters={"price": "free", "accessibility": "yes", "audience": "families", "time": "weekends"},
        relevance_ground_truth=[]
    ),
    Query(
        id="Q_COMPLEX_002",
        query="Outdoor summer concerts in Paris suburbs with parking",
        language="en",
        query_type="multi_criteria",
        complexity="high",
        expected_categories=["concerts"],
        expected_filters={"location": "outdoor", "season": "summer", "area": "suburbs", "parking": "available"},
        relevance_ground_truth=[]
    ),

    # Negative criteria
    Query(
        id="Q_NEG_001",
        query="Classical music NOT opera",
        language="en",
        query_type="negative_filter",
        complexity="medium",
        expected_categories=["classical"],
        expected_filters={"exclude": "opera"},
        relevance_ground_truth=[]
    ),

    # Time-specific queries
    Query(
        id="Q_TIME_001",
        query="Evening concerts starting after 19:00",
        language="en",
        query_type="time_filter",
        complexity="medium",
        expected_categories=["concerts"],
        expected_filters={"time": "evening", "start_time": "after 19:00"},
        relevance_ground_truth=[]
    ),
    Query(
        id="Q_TIME_002",
        query="Matinée performances on weekends",
        language="en",
        query_type="time_filter",
        complexity="medium",
        expected_filters={"time": "matinée", "day": "weekends"},
        relevance_ground_truth=[]
    ),

    # Venue-specific queries
    Query(
        id="Q_VENUE_001",
        query="Events at Théâtre du Châtelet",
        language="en",
        query_type="venue_specific",
        complexity="simple",
        expected_filters={"venue": "Théâtre du Châtelet"},
        relevance_ground_truth=[]
    ),

    # Festival/series queries
    Query(
        id="Q_SERIES_001",
        query="Nuit Blanche events in October",
        language="en",
        query_type="event_series",
        complexity="simple",
        expected_filters={"event_series": "Nuit Blanche", "month": 10},
        relevance_ground_truth=[]
    ),
]


def add_to_dataset():
    """Add new diverse queries to the golden dataset."""
    dataset_path = Path("data/evaluation/golden_dataset.json")

    # Load existing dataset
    logger.info(f"Loading existing dataset from {dataset_path}")
    dataset = GoldenDataset.load(str(dataset_path))

    logger.info(f"Current dataset has {len(dataset.queries)} queries")

    # Add new queries
    for new_query in NEW_QUERIES:
        # Check if query ID already exists
        if any(q.id == new_query.id for q in dataset.queries):
            logger.warning(f"Query {new_query.id} already exists, skipping")
            continue

        dataset.queries.append(new_query)
        logger.info(f"Added query {new_query.id}: {new_query.query}")

    logger.info(f"New dataset has {len(dataset.queries)} queries")

    # Save updated dataset
    backup_path = dataset_path.parent / f"{dataset_path.stem}_backup{dataset_path.suffix}"
    logger.info(f"Creating backup at {backup_path}")
    dataset_path.rename(backup_path)

    logger.info(f"Saving updated dataset to {dataset_path}")
    dataset.save(str(dataset_path))

    logger.info("\n" + "="*80)
    logger.info("DATASET EXPANSION SUMMARY")
    logger.info("="*80)
    logger.info(f"Added {len(NEW_QUERIES)} new diverse queries")
    logger.info(f"Total queries: {len(dataset.queries)}")

    # Statistics
    complexity_counts = {}
    type_counts = {}
    for q in dataset.queries:
        complexity_counts[q.complexity] = complexity_counts.get(q.complexity, 0) + 1
        type_counts[q.query_type] = type_counts.get(q.query_type, 0) + 1

    logger.info("\nBy complexity:")
    for complexity, count in sorted(complexity_counts.items()):
        logger.info(f"  {complexity}: {count}")

    logger.info("\nBy type (new types):")
    for qtype, count in sorted(type_counts.items()):
        if qtype in ['price_filter', 'accessibility', 'language', 'negative_filter',
                     'time_filter', 'venue_specific', 'event_series']:
            logger.info(f"  {qtype}: {count}")

    logger.info("="*80)


if __name__ == "__main__":
    add_to_dataset()
