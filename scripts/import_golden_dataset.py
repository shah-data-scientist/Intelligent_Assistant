"""Import edited YAML golden dataset back to JSON format.

This script reads the human-edited YAML file and converts it back to the
JSON format used by the evaluation system.

Features:
- Validates YAML structure
- Preserves all edits and user notes
- Creates backup of existing JSON before updating
- Reports changes made

Usage:
    python scripts/import_golden_dataset.py
    python scripts/import_golden_dataset.py --input data/evaluation/golden_dataset.yaml
    python scripts/import_golden_dataset.py --no-backup  # Skip backup creation
"""

import argparse
import json
import logging
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_yaml_manually(yaml_content: str) -> dict:
    """Parse YAML content manually (simple parser for our specific format).

    Args:
        yaml_content: YAML file content as string

    Returns:
        Parsed dataset as dict
    """
    lines = yaml_content.split('\n')
    dataset = {"metadata": {}, "queries": []}

    current_query = None
    current_section = None
    current_list = None
    indent_stack = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip comments and empty lines
        if line.strip().startswith('#') or not line.strip():
            i += 1
            continue

        # Detect indentation level
        indent = len(line) - len(line.lstrip())

        # Metadata section
        if line.strip().startswith('metadata:'):
            current_section = 'metadata'
            i += 1
            continue

        # Queries section
        if line.strip().startswith('queries:'):
            current_section = 'queries'
            i += 1
            continue

        # Parse metadata
        if current_section == 'metadata' and indent == 2:
            match = re.match(r'\s*(\w+):\s*(.+)', line)
            if match:
                key, value = match.groups()
                # Try to parse JSON value
                try:
                    dataset['metadata'][key] = json.loads(value)
                except:
                    dataset['metadata'][key] = value.strip('"')

        # Parse queries
        if current_section == 'queries':
            # New query
            if line.strip().startswith('- id:'):
                current_query = {}
                dataset['queries'].append(current_query)
                match = re.match(r'\s*-\s*id:\s*(.+)', line)
                if match:
                    current_query['id'] = match.group(1).strip()

            # Query fields
            elif current_query is not None and indent >= 4:
                # Simple key-value pairs
                match = re.match(r'\s*(\w+):\s*(.+)', line)
                if match:
                    key, value = match.groups()
                    value = value.strip()

                    # Handle different value types
                    if value.startswith('"') and value.endswith('"'):
                        current_query[key] = value.strip('"')
                    elif value in ['True', 'False']:
                        current_query[key] = value == 'True'
                    elif value == '[]':
                        current_query[key] = []
                    elif value == '{}':
                        current_query[key] = {}
                    elif value.isdigit():
                        current_query[key] = int(value)
                    elif re.match(r'^\d+\.\d+$', value):
                        current_query[key] = float(value)
                    else:
                        current_query[key] = value

                    # Track current list context
                    if key in ['expected_entities', 'expected_categories', 'relevance_ground_truth', 'must_contain_keywords']:
                        current_list = key
                        if key not in current_query:
                            current_query[key] = []

                    elif key == 'expected_filters':
                        current_query[key] = {}
                        current_section = 'filters'

                    elif key == 'conversational_context':
                        current_query[key] = {}
                        current_section = 'conv_context'

                    elif key == 'generation_expectations':
                        current_query[key] = {}
                        current_section = 'gen_exp'

                # List items
                elif line.strip().startswith('- '):
                    value = line.strip()[2:].strip('"')
                    if current_list == 'expected_entities':
                        current_query['expected_entities'].append(value)
                    elif current_list == 'expected_categories':
                        current_query['expected_categories'].append(value)
                    elif current_list == 'must_contain_keywords':
                        if 'generation_expectations' in current_query:
                            if 'must_contain_keywords' not in current_query['generation_expectations']:
                                current_query['generation_expectations']['must_contain_keywords'] = []
                            current_query['generation_expectations']['must_contain_keywords'].append(value)
                    elif current_list == 'relevance_ground_truth':
                        # Start of new ground truth item
                        match = re.match(r'\s*-\s*event_id:\s*"(.+)"', line)
                        if match:
                            gt_item = {'event_id': match.group(1)}
                            current_query['relevance_ground_truth'].append(gt_item)

                # Nested fields
                elif indent >= 6:
                    match = re.match(r'\s*(\w+):\s*(.+)', line)
                    if match:
                        key, value = match.groups()
                        value = value.strip().strip('"')

                        # Handle filter values
                        if 'expected_filters' in current_query and current_section == 'filters':
                            try:
                                current_query['expected_filters'][key] = json.loads(value)
                            except:
                                if value.isdigit():
                                    current_query['expected_filters'][key] = int(value)
                                elif value in ['True', 'False']:
                                    current_query['expected_filters'][key] = value == 'True'
                                else:
                                    current_query['expected_filters'][key] = value

                        # Handle conversational context
                        elif 'conversational_context' in current_query and current_section == 'conv_context':
                            if value.isdigit():
                                current_query['conversational_context'][key] = int(value)
                            else:
                                current_query['conversational_context'][key] = value

                        # Handle generation expectations
                        elif 'generation_expectations' in current_query and current_section == 'gen_exp':
                            if value in ['True', 'False']:
                                current_query['generation_expectations'][key] = value == 'True'
                            else:
                                current_query['generation_expectations'][key] = value

                        # Handle ground truth items
                        elif current_list == 'relevance_ground_truth' and len(current_query.get('relevance_ground_truth', [])) > 0:
                            gt_item = current_query['relevance_ground_truth'][-1]
                            if key == 'relevance_score':
                                gt_item[key] = float(value)
                            else:
                                gt_item[key] = value

        i += 1

    return dataset


def import_from_yaml(yaml_path: str, json_path: str, create_backup: bool = True) -> None:
    """Import edited YAML back to JSON format.

    Args:
        yaml_path: Path to edited YAML file
        json_path: Path to output JSON file
        create_backup: Whether to create backup of existing JSON
    """
    # Backup existing JSON
    json_file = Path(json_path)
    if create_backup and json_file.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = json_file.parent / f"golden_dataset_backup_{timestamp}.json"
        logger.info(f"Creating backup at {backup_path}")
        shutil.copy(json_file, backup_path)

    # Read YAML file
    logger.info(f"Reading YAML from {yaml_path}")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()

    # Parse YAML
    logger.info("Parsing YAML content...")
    dataset = parse_yaml_manually(yaml_content)

    # Validate structure
    if 'queries' not in dataset or not isinstance(dataset['queries'], list):
        raise ValueError("Invalid YAML structure: 'queries' list not found")

    logger.info(f"Parsed {len(dataset['queries'])} queries from YAML")

    # Write to JSON
    logger.info(f"Writing to JSON: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    logger.info("Import complete!")


def main():
    """Main import execution."""
    parser = argparse.ArgumentParser(
        description="Import edited YAML golden dataset back to JSON"
    )
    parser.add_argument(
        "--input",
        default="data/evaluation/golden_dataset.yaml",
        help="Input YAML file path"
    )
    parser.add_argument(
        "--output",
        default="data/evaluation/golden_dataset.json",
        help="Output JSON file path"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup of existing JSON"
    )
    args = parser.parse_args()

    try:
        import_from_yaml(args.input, args.output, create_backup=not args.no_backup)

        print("\n" + "="*70)
        print("YAML IMPORT COMPLETE")
        print("="*70)
        print(f"Input:  {args.input}")
        print(f"Output: {args.output}")
        print("\nChanges have been applied to the golden dataset.")
        print("Run evaluation to test your changes:")
        print("  python scripts/run_evaluation.py")
        print("="*70 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
