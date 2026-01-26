"""Audit database field population and quality metrics for RAG optimization.

This script generates a comprehensive data quality report analyzing:
- Field population rates
- Content length statistics
- Category and city distributions
- Temporal coverage
- Data quality gaps affecting RAG performance

Usage:
    python scripts/audit_data_quality.py
    python scripts/audit_data_quality.py --output data/evaluation/data_quality_report.json
"""

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.storage import EventStorage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def calculate_field_population(events: list) -> dict[str, float]:
    """Calculate population rate for each field."""
    total = len(events)
    if total == 0:
        return {}

    population = {
        "title": sum(1 for e in events if e.title) / total * 100,
        "description": sum(1 for e in events if e.description) / total * 100,
        "scraped_content": sum(1 for e in events if e.scraped_content) / total * 100,
        "category": sum(1 for e in events if e.category) / total * 100,
        "location": sum(1 for e in events if e.location) / total * 100,
        "city": sum(1 for e in events if e.location and e.location.city) / total * 100,
        "coordinates": sum(1 for e in events if e.location and e.location.coordinates) / total * 100,
        "start_date": sum(1 for e in events if e.start_date) / total * 100,
        "end_date": sum(1 for e in events if e.end_date) / total * 100,
        "tags": sum(1 for e in events if e.tags) / total * 100,
        "organizer": sum(1 for e in events if e.organizer) / total * 100,
        "url": sum(1 for e in events if e.url) / total * 100,
        "image_url": sum(1 for e in events if e.image_url) / total * 100,
        "age_min": sum(1 for e in events if e.age_min is not None) / total * 100,
        "age_max": sum(1 for e in events if e.age_max is not None) / total * 100,
        "accessibility": sum(1 for e in events if e.accessibility) / total * 100,
        "conditions": sum(1 for e in events if e.conditions) / total * 100,
    }

    return {k: round(v, 2) for k, v in population.items()}


def calculate_content_length_stats(events: list) -> dict[str, Any]:
    """Calculate content length statistics."""
    title_lengths = [len(e.title) for e in events if e.title]
    desc_lengths = [len(e.description) for e in events if e.description]
    scraped_lengths = [len(e.scraped_content) for e in events if e.scraped_content]

    def safe_avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else 0

    def safe_median(lst):
        if not lst:
            return 0
        sorted_lst = sorted(lst)
        mid = len(sorted_lst) // 2
        if len(sorted_lst) % 2 == 0:
            return (sorted_lst[mid-1] + sorted_lst[mid]) / 2
        return sorted_lst[mid]

    return {
        "title": {
            "avg_length": safe_avg(title_lengths),
            "median_length": safe_median(title_lengths),
            "max_length": max(title_lengths) if title_lengths else 0,
        },
        "description": {
            "avg_length": safe_avg(desc_lengths),
            "median_length": safe_median(desc_lengths),
            "max_length": max(desc_lengths) if desc_lengths else 0,
        },
        "scraped_content": {
            "avg_length": safe_avg(scraped_lengths),
            "median_length": safe_median(scraped_lengths),
            "max_length": max(scraped_lengths) if scraped_lengths else 0,
            "populated_count": len(scraped_lengths),
        },
    }


def calculate_distributions(events: list) -> dict[str, Any]:
    """Calculate category, city, and temporal distributions."""
    categories = Counter(e.category for e in events if e.category)
    cities = Counter(e.location.city for e in events if e.location and e.location.city)

    # Temporal distribution
    years = Counter(e.start_date.year for e in events if e.start_date)
    months = Counter(e.start_date.month for e in events if e.start_date)

    return {
        "categories": dict(categories.most_common(15)),
        "cities": dict(cities.most_common(15)),
        "temporal": {
            "years": dict(years),
            "months": dict(months),
        }
    }


def identify_quality_gaps(events: list) -> list[dict[str, Any]]:
    """Identify data quality gaps affecting RAG performance."""
    gaps = []

    # Gap 1: Missing scraped_content
    missing_scraped = [e for e in events if e.url and not e.scraped_content]
    if missing_scraped:
        gaps.append({
            "issue": "missing_scraped_content",
            "severity": "high",
            "count": len(missing_scraped),
            "percentage": round(len(missing_scraped) / len(events) * 100, 2),
            "impact": "Reduces content richness for semantic search",
            "recommendation": "Use LLM to generate detailed descriptions from title + description + category"
        })

    # Gap 2: Missing tags
    missing_tags = [e for e in events if not e.tags]
    if missing_tags:
        gaps.append({
            "issue": "missing_tags",
            "severity": "medium",
            "count": len(missing_tags),
            "percentage": round(len(missing_tags) / len(events) * 100, 2),
            "impact": "Reduces keyword-based retrieval effectiveness",
            "recommendation": "Extract 5-8 keyword tags from description + scraped_content using LLM"
        })

    # Gap 3: Missing coordinates
    missing_coords = [e for e in events if e.location and e.location.city and not e.location.coordinates]
    if missing_coords:
        gaps.append({
            "issue": "missing_coordinates",
            "severity": "medium",
            "count": len(missing_coords),
            "percentage": round(len(missing_coords) / len(events) * 100, 2),
            "impact": "Reduces geospatial search precision",
            "recommendation": "Geocode city names to lat/lon coordinates"
        })

    # Gap 4: Missing age ranges
    missing_age = [e for e in events if e.age_min is None or e.age_max is None]
    if missing_age:
        gaps.append({
            "issue": "missing_age_ranges",
            "severity": "low",
            "count": len(missing_age),
            "percentage": round(len(missing_age) / len(events) * 100, 2),
            "impact": "Limits family-friendly event filtering",
            "recommendation": "Infer age ranges from description text (family-friendly, children, adults)"
        })

    # Gap 5: Short descriptions
    short_desc = [e for e in events if e.description and len(e.description) < 50]
    if short_desc:
        gaps.append({
            "issue": "short_descriptions",
            "severity": "low",
            "count": len(short_desc),
            "percentage": round(len(short_desc) / len(events) * 100, 2),
            "impact": "Insufficient semantic content for embeddings",
            "recommendation": "Enrich with scraped_content or generate from title + category"
        })

    return gaps


def generate_audit_report(events: list) -> dict[str, Any]:
    """Generate comprehensive audit report."""
    logger.info(f"Analyzing {len(events)} events...")

    report = {
        "audit_metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "total_events": len(events),
            "audit_version": "1.0"
        },
        "field_population": calculate_field_population(events),
        "content_length_stats": calculate_content_length_stats(events),
        "distributions": calculate_distributions(events),
        "quality_gaps": identify_quality_gaps(events),
    }

    # Summary stats
    pop = report["field_population"]
    report["summary"] = {
        "rag_critical_fields": {
            "title": f"{pop['title']}%",
            "description": f"{pop['description']}%",
            "scraped_content": f"{pop['scraped_content']}%",
            "category": f"{pop['category']}%",
            "city": f"{pop['city']}%",
        },
        "enrichment_opportunities": len(report["quality_gaps"]),
        "high_severity_gaps": len([g for g in report["quality_gaps"] if g["severity"] == "high"]),
    }

    return report


def print_summary(report: dict[str, Any]) -> None:
    """Print human-readable summary to console."""
    print("\n" + "="*70)
    print("DATABASE QUALITY AUDIT REPORT")
    print("="*70)
    print(f"\nTotal Events: {report['audit_metadata']['total_events']}")
    print(f"Audit Timestamp: {report['audit_metadata']['timestamp']}")

    print("\n" + "FIELD POPULATION (RAG-Critical Fields):")
    print("-" * 70)
    for field, pct in report['summary']['rag_critical_fields'].items():
        status = "OK" if float(pct.rstrip('%')) >= 90 else "WARN" if float(pct.rstrip('%')) >= 70 else "FAIL"
        print(f"  [{status}] {field:20s}: {pct:>6s}")

    print("\nCONTENT LENGTH STATISTICS:")
    print("-" * 70)
    for field, stats in report['content_length_stats'].items():
        print(f"  {field}:")
        print(f"    - Average: {stats['avg_length']:.1f} chars")
        print(f"    - Median:  {stats['median_length']:.1f} chars")
        if 'populated_count' in stats:
            print(f"    - Populated: {stats['populated_count']} events")

    print("\nDATA QUALITY GAPS:")
    print("-" * 70)
    if not report['quality_gaps']:
        print("  No significant quality gaps detected!")
    else:
        for gap in report['quality_gaps']:
            severity_label = gap['severity'].upper()
            print(f"\n  [{severity_label}] {gap['issue'].upper()}")
            print(f"     Count: {gap['count']} events ({gap['percentage']}%)")
            print(f"     Impact: {gap['impact']}")
            print(f"     Recommendation: {gap['recommendation']}")

    print("\nTOP CATEGORIES:")
    print("-" * 70)
    for cat, count in list(report['distributions']['categories'].items())[:10]:
        print(f"  {cat:30s}: {count:>4} events")

    print("\nTOP CITIES:")
    print("-" * 70)
    for city, count in list(report['distributions']['cities'].items())[:10]:
        print(f"  {city:30s}: {count:>4} events")

    print("\n" + "="*70)
    print(f"Audit complete. {report['summary']['enrichment_opportunities']} enrichment opportunities identified.")
    print("="*70 + "\n")


def main():
    """Main audit execution."""
    parser = argparse.ArgumentParser(
        description="Audit database quality for RAG optimization"
    )
    parser.add_argument(
        "--output",
        default="data/evaluation/data_quality_report.json",
        help="Output path for JSON report"
    )
    args = parser.parse_args()

    try:
        # Load events from database
        logger.info("Loading events from database...")
        storage = EventStorage()
        events = storage.get_all_events()

        if not events:
            logger.error("No events found in database!")
            return 1

        # Generate report
        report = generate_audit_report(events)

        # Print summary to console
        print_summary(report)

        # Save JSON report
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Full report saved to: {output_path}")

        return 0

    except Exception as e:
        logger.error(f"Audit failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
