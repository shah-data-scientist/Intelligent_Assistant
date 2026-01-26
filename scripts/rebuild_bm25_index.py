"""Rebuild BM25 index with language-aware tokenization from Phase 4.

This script:
1. Backs up the existing FAISS + BM25 index
2. Loads all events from the database
3. Tokenizes events using language-aware processing (stopwords, stemming, accent normalization)
4. Rebuilds BM25 index with new tokenization
5. Saves the updated index

Usage:
    python scripts/rebuild_bm25_index.py
    python scripts/rebuild_bm25_index.py --skip-backup  # Skip backup creation
"""

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.data.storage import EventStorage
from src.models.vector_store import EventVectorStore
from src.utils.language import tokenize_for_bm25, detect_language

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def backup_index(index_dir: Path, backup_dir: Path) -> None:
    """Create a timestamped backup of the current index.

    Args:
        index_dir: Current index directory
        backup_dir: Backup directory
    """
    if not index_dir.exists():
        logger.warning(f"Index directory {index_dir} does not exist, skipping backup")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"index_backup_{timestamp}"

    logger.info(f"Creating backup at {backup_path}")
    shutil.copytree(index_dir, backup_path)
    logger.info(f"Backup created successfully")


def rebuild_index(store: EventVectorStore, language: str = "fr") -> dict[str, Any]:
    """Rebuild BM25 index with language-aware tokenization.

    Args:
        store: EventVectorStore instance
        language: Default language for tokenization ("fr" or "en")

    Returns:
        Dict with rebuild statistics
    """
    logger.info(f"Loading events from database...")
    events = store.storage.get_all_events()

    if not events:
        logger.error("No events found in database!")
        return {"success": False, "error": "No events found"}

    logger.info(f"Loaded {len(events)} events")

    # Tokenize corpus with language-aware processing
    logger.info(f"Tokenizing events with language-aware processing (language={language})...")
    tokenized_corpus = []
    total_tokens_before = 0
    total_tokens_after = 0

    for i, event in enumerate(events):
        # Build searchable text
        searchable_text = f"{event.title} {event.description or ''} {event.scraped_content or ''}"

        # Old tokenization (simple split for comparison)
        old_tokens = searchable_text.lower().split()
        total_tokens_before += len(old_tokens)

        # New tokenization (language-aware)
        new_tokens = tokenize_for_bm25(searchable_text, language=language)
        total_tokens_after += len(new_tokens)
        tokenized_corpus.append(new_tokens)

        if (i + 1) % 100 == 0:
            logger.info(f"Tokenized {i + 1}/{len(events)} events")

    # Calculate token reduction
    avg_tokens_before = total_tokens_before / len(events)
    avg_tokens_after = total_tokens_after / len(events)
    reduction_pct = ((total_tokens_before - total_tokens_after) / total_tokens_before) * 100

    logger.info(f"\nTokenization Statistics:")
    logger.info(f"  Avg tokens before: {avg_tokens_before:.1f}")
    logger.info(f"  Avg tokens after:  {avg_tokens_after:.1f}")
    logger.info(f"  Token reduction:   {reduction_pct:.1f}%")

    # Rebuild BM25 index
    logger.info(f"\nRebuilding BM25 index...")
    from rank_bm25 import BM25Okapi
    store.bm25 = BM25Okapi(tokenized_corpus)
    logger.info(f"BM25 index rebuilt successfully")

    # Save updated index
    logger.info(f"Saving updated index...")
    store.save_index()
    logger.info(f"Index saved to {settings.faiss_index_path}")

    return {
        "success": True,
        "total_events": len(events),
        "avg_tokens_before": round(avg_tokens_before, 1),
        "avg_tokens_after": round(avg_tokens_after, 1),
        "token_reduction_pct": round(reduction_pct, 1),
        "language": language
    }


def main():
    """Main rebuild execution."""
    parser = argparse.ArgumentParser(
        description="Rebuild BM25 index with language-aware tokenization"
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup of existing index"
    )
    parser.add_argument(
        "--language",
        default="fr",
        choices=["fr", "en"],
        help="Default language for tokenization (default: fr)"
    )
    args = parser.parse_args()

    try:
        # Backup existing index
        if not args.skip_backup:
            index_dir = Path(settings.faiss_index_path).parent
            backup_dir = index_dir.parent / "index_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_index(index_dir, backup_dir)
        else:
            logger.info("Skipping backup (--skip-backup flag set)")

        # Initialize vector store
        logger.info("Initializing EventVectorStore...")
        storage = EventStorage()
        store = EventVectorStore(index_path=None, embedder=None, storage=storage)

        # Load existing index (to preserve FAISS embeddings)
        logger.info("Loading existing index...")
        store.load_index()

        # Rebuild BM25 component
        stats = rebuild_index(store, language=args.language)

        if not stats["success"]:
            logger.error(f"Rebuild failed: {stats.get('error')}")
            return 1

        # Print summary
        print("\n" + "="*70)
        print("BM25 INDEX REBUILD SUMMARY")
        print("="*70)
        print(f"Total Events:       {stats['total_events']}")
        print(f"Language:           {stats['language']}")
        print(f"Avg Tokens Before:  {stats['avg_tokens_before']}")
        print(f"Avg Tokens After:   {stats['avg_tokens_after']}")
        print(f"Token Reduction:    {stats['token_reduction_pct']}%")
        print("="*70)
        print("\nIndex rebuilt successfully!")
        print("="*70 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Rebuild failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
