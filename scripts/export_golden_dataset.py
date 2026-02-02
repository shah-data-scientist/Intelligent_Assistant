"""Export golden dataset to editable YAML format with comments.

This script converts the JSON golden dataset to a human-readable YAML format
that allows for easy consultation, editing, and direct feedback annotation.

Features:
- Clean YAML formatting with proper indentation
- Inline comments for guidance
- User notes sections for feedback
- Easy to review in any text editor

Usage:
    python scripts/export_golden_dataset.py
    python scripts/export_golden_dataset.py --output data/evaluation/golden_dataset.yaml
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def export_to_yaml(json_path: str, yaml_path: str) -> None:
    """Export golden dataset from JSON to editable YAML format.

    Args:
        json_path: Path to JSON golden dataset
        yaml_path: Path to output YAML file
    """
    # Load JSON dataset
    logger.info(f"Loading dataset from {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    queries = dataset.get("queries", [])
    metadata = dataset.get("metadata", {})

    logger.info(f"Exporting {len(queries)} queries to YAML format...")

    # Create YAML content with proper formatting
    yaml_lines = []

    # Header
    yaml_lines.append("# Golden Dataset - Editable YAML Format")
    yaml_lines.append("# This file can be edited directly and re-imported to update the dataset")
    yaml_lines.append("#")
    yaml_lines.append("# Instructions:")
    yaml_lines.append("#   - Modify queries, expectations, and annotations as needed")
    yaml_lines.append("#   - Add user_notes to provide feedback on specific results")
    yaml_lines.append("#   - Use annotation_comments to document test intent and improvements")
    yaml_lines.append("#   - After editing, run: python scripts/import_golden_dataset.py")
    yaml_lines.append("")

    # Metadata section
    yaml_lines.append("metadata:")
    for key, value in metadata.items():
        yaml_lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
    yaml_lines.append("")

    # Queries section
    yaml_lines.append("queries:")
    yaml_lines.append("")

    for i, query in enumerate(queries):
        # Query header
        yaml_lines.append(f"  # Query {i+1}/{len(queries)}")
        yaml_lines.append(f"  - id: {query['id']}")
        yaml_lines.append(f"    query: \"{query['query']}\"")
        yaml_lines.append(f"    language: {query['language']}")
        yaml_lines.append(f"    query_type: {query['query_type']}")
        yaml_lines.append(f"    complexity: {query['complexity']}")
        yaml_lines.append("")

        # Expected entities
        yaml_lines.append("    expected_entities:")
        for entity in query.get("expected_entities", []):
            yaml_lines.append(f'      - "{entity}"')
        yaml_lines.append("")

        # Expected categories
        yaml_lines.append("    expected_categories:")
        for cat in query.get("expected_categories", []):
            yaml_lines.append(f"      - {cat}")
        yaml_lines.append("")

        # Expected filters
        yaml_lines.append("    expected_filters:")
        filters = query.get("expected_filters", {})
        if filters:
            for key, value in filters.items():
                yaml_lines.append(f"      {key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            yaml_lines.append("      {}")
        yaml_lines.append("")

        # Conversational context (if present)
        if "conversational_context" in query:
            yaml_lines.append("    conversational_context:")
            ctx = query["conversational_context"]
            yaml_lines.append(f"      parent_query_id: {ctx.get('parent_query_id', 'null')}")
            yaml_lines.append(f"      turn_number: {ctx.get('turn_number', 0)}")
            yaml_lines.append(f"      chain_description: \"{ctx.get('chain_description', '')}\"")
            yaml_lines.append("")

        # Bilingual equivalent (if present)
        if "bilingual_equivalent" in query:
            yaml_lines.append(f"    bilingual_equivalent: {query['bilingual_equivalent']}")
            yaml_lines.append("")

        # Relevance ground truth
        yaml_lines.append("    relevance_ground_truth:")
        ground_truth = query.get("relevance_ground_truth", [])
        if ground_truth:
            for gt in ground_truth:
                yaml_lines.append(f"      - event_id: \"{gt['event_id']}\"")
                yaml_lines.append(f"        relevance_score: {gt['relevance_score']}")
                reason = gt.get("reason", "No reason provided")
                yaml_lines.append(f'        reason: "{reason}"')
                yaml_lines.append("")
                yaml_lines.append("        # ✏️ USER NOTES (add your feedback here):")
                yaml_lines.append("        user_notes: |")
                yaml_lines.append("          # Add notes about this result:")
                yaml_lines.append("          # - Is the relevance score accurate?")
                yaml_lines.append("          # - Should this event be ranked higher/lower?")
                yaml_lines.append("          # - Any improvements needed?")
                yaml_lines.append("")
        else:
            yaml_lines.append("      []  # No ground truth defined yet")
        yaml_lines.append("")

        # Generation expectations
        yaml_lines.append("    generation_expectations:")
        gen_exp = query.get("generation_expectations", {})
        yaml_lines.append("      must_contain_keywords:")
        for keyword in gen_exp.get("must_contain_keywords", []):
            yaml_lines.append(f'        - "{keyword}"')
        yaml_lines.append(f"      must_not_hallucinate: {gen_exp.get('must_not_hallucinate', True)}")
        yaml_lines.append(f"      should_ask_clarification: {gen_exp.get('should_ask_clarification', False)}")
        yaml_lines.append(f"      should_refuse_gracefully: {gen_exp.get('should_refuse_gracefully', False)}")
        yaml_lines.append(f"      expected_language: {gen_exp.get('expected_language', 'fr')}")
        yaml_lines.append("")

        # Annotation comments
        yaml_lines.append("    # 📝 ANNOTATION COMMENTS (document test intent):")
        yaml_lines.append("    annotation_comments: |")
        comments = query.get("annotation_comments", "No comments provided")
        # Indent comment lines
        for line in comments.split("\n"):
            yaml_lines.append(f"      {line}")
        yaml_lines.append("")
        yaml_lines.append("    # ✅ TEST RESULTS (add evaluation results here):")
        yaml_lines.append("    test_results: |")
        yaml_lines.append("      # After running evaluation, document:")
        yaml_lines.append("      # - Precision: ?")
        yaml_lines.append("      # - Recall: ?")
        yaml_lines.append("      # - Issues found: ?")
        yaml_lines.append("")
        yaml_lines.append("  # " + "-" * 70)
        yaml_lines.append("")

    # Write YAML file
    yaml_content = "\n".join(yaml_lines)

    output_path = Path(yaml_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    logger.info(f"Exported {len(queries)} queries to {yaml_path}")
    logger.info(f"File size: {len(yaml_content):,} characters")
    logger.info("\nYou can now:")
    logger.info("  1. Open the YAML file in any text editor")
    logger.info("  2. Review and edit queries, expectations, and annotations")
    logger.info("  3. Add user_notes and test_results for each query")
    logger.info("  4. Re-import with: python scripts/import_golden_dataset.py")


def main():
    """Main export execution."""
    parser = argparse.ArgumentParser(description="Export golden dataset to editable YAML format")
    parser.add_argument("--input", default="data/evaluation/golden_dataset.json", help="Input JSON golden dataset path")
    parser.add_argument("--output", default="data/evaluation/golden_dataset.yaml", help="Output YAML path")
    args = parser.parse_args()

    try:
        export_to_yaml(args.input, args.output)

        print("\n" + "=" * 70)
        print("YAML EXPORT COMPLETE")
        print("=" * 70)
        print(f"Input:  {args.input}")
        print(f"Output: {args.output}")
        print("\nNext steps:")
        print("  1. Review the YAML file")
        print("  2. Edit queries and add feedback")
        print("  3. Re-import: python scripts/import_golden_dataset.py")
        print("=" * 70 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
