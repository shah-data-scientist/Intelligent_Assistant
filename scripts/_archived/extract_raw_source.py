"""Extract raw records directly from the API source."""

import json
import pandas as pd
from src.data.api_client import OpenAgendaClient


def extract_raw_source(limit=100):
    client = OpenAgendaClient()
    print(f"Fetching {limit} raw records from API...")

    # Fetch raw records (this bypasses our processing/date shifting)
    raw_records = client.fetch_events(limit=limit)

    # 1. Save as JSON (Raw)
    json_path = "data/raw_source_100.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_records, f, indent=4, ensure_ascii=False)
    print(f"Saved raw JSON to {json_path}")

    # 2. Save as Excel (Flattened)
    # Use json_normalize to flatten nested structures (e.g. location.city)
    df = pd.json_normalize(raw_records)
    excel_path = "data/raw_source_100.xlsx"
    df.to_excel(excel_path, index=False)
    print(f"Saved flattened Excel to {excel_path}")


if __name__ == "__main__":
    extract_raw_source()
