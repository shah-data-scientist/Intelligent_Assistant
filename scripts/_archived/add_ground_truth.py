"""Helper script to add ground truth annotations to golden dataset.

This script helps identify relevant events for queries missing ground truth.
"""

import logging
from src.data.storage import EventStorage
from src.evaluation.datasets.golden_dataset import GoldenDataset
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load dataset and storage
    dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
    storage = EventStorage()
    all_events = storage.get_all_events()

    logger.info(f"Total events in database: {len(all_events)}")
    logger.info(f"Total queries in dataset: {len(dataset.queries)}")

    # Find queries without ground truth
    queries_without_gt = [q for q in dataset.queries if not q.relevance_ground_truth]
    logger.info(f"Queries without ground truth: {len(queries_without_gt)}")

    # For each query, suggest relevant events
    for query in queries_without_gt:
        print(f"\n{'='*80}")
        print(f"Query ID: {query.id}")
        print(f"Query: {query.query}")
        print(f"Language: {query.language}")
        print(f"Type: {query.query_type}")
        print(f"Expected categories: {query.expected_categories}")
        print(f"Expected filters: {query.expected_filters}")
        print(f"{'='*80}")

        # Filter events based on expected criteria
        relevant_events = []

        for event in all_events:
            score = 0.0
            reasons = []

            # Check category match
            expected_cats = query.expected_categories
            if expected_cats and event.category:
                for cat in expected_cats:
                    if cat.lower() in event.category.lower():
                        score += 0.4
                        reasons.append(f"Category match: {event.category}")
                        break

            # Check city match
            expected_city = query.expected_filters.get("city")
            if expected_city and event.location and event.location.city:
                if expected_city.lower() in event.location.city.lower():
                    score += 0.3
                    reasons.append(f"City match: {event.location.city}")

            # Check month match
            expected_month = query.expected_filters.get("month")
            if expected_month and event.start_date:
                if event.start_date.month == expected_month:
                    score += 0.2
                    reasons.append(f"Month match: {event.start_date.month}")

            # Check for keyword matches in title/description
            query_lower = query.query.lower()
            for keyword in query.expected_entities:
                if keyword.lower() in (event.title + " " + (event.description or "")).lower():
                    score += 0.1
                    reasons.append(f"Keyword '{keyword}' in title/description")
                    break

            if score > 0:
                relevant_events.append((event, score, reasons))

        # Sort by score and show top 5
        relevant_events.sort(key=lambda x: x[1], reverse=True)

        if relevant_events:
            print(f"\nTop {min(5, len(relevant_events))} relevant events:")
            for i, (event, score, reasons) in enumerate(relevant_events[:5], 1):
                print(f"\n{i}. Event ID: {event.event_id}")
                print(f"   Title: {event.title}")
                print(f"   Category: {event.category}")
                print(f"   City: {event.location.city if event.location else 'N/A'}")
                print(f"   Date: {event.start_date.strftime('%Y-%m-%d') if event.start_date else 'N/A'}")
                print(f"   Relevance Score: {score:.2f}")
                print(f"   Reasons: {'; '.join(reasons)}")
        else:
            print("\n[WARN] No obviously relevant events found. This might be an edge case or no-results query.")

        # Auto-add ground truth if we found high-quality matches
        if relevant_events and relevant_events[0][1] >= 0.5:
            # Add top 2-3 events with score >= 0.5
            ground_truth = []
            for event, score, _ in relevant_events[:3]:
                if score >= 0.5:
                    ground_truth.append({
                        "event_id": event.event_id,
                        "relevance_score": round(min(score, 1.0), 2)
                    })

            # Update query with ground truth
            from src.evaluation.datasets.golden_dataset import RelevanceGroundTruth
            query.relevance_ground_truth = [
                RelevanceGroundTruth(**gt) for gt in ground_truth
            ]
            print(f"\n[OK] AUTO-ADDED {len(ground_truth)} events to ground truth")
            for gt in ground_truth:
                print(f"  - Event ID: {gt['event_id']}, Score: {gt['relevance_score']}")
        else:
            print(f"\n[SKIP] No high-quality matches found (keeping empty ground truth for edge case)")

    # Save updated dataset
    print(f"\n{'='*80}")
    queries_with_gt = [q for q in dataset.queries if q.relevance_ground_truth]
    print(f"Saving updated dataset...")
    print(f"Queries with ground truth: {len(queries_with_gt)}/{len(dataset.queries)}")
    dataset.save("data/evaluation/golden_dataset.json")
    logger.info("[OK] Dataset saved successfully")

if __name__ == "__main__":
    main()
