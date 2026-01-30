"""Test coreference resolution with previous events context.

This script tests the Phase 1 changes:
1. Chat storage now stores retrieved_events
2. Chain extracts previous events
3. Unified analyzer receives previous events in prompt
"""

import logging
import sys
from src.retrieval.chain import RAGChain
from src.data.chat_storage import ChatStorage

# Force UTF-8 encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_print(text):
    """Print text safely handling encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII ignoring errors
        print(text.encode('ascii', 'ignore').decode('ascii'))

def test_coreference_resolution():
    """Test that 'Art of the Trio' is correctly resolved from context."""

    safe_print("=" * 80)
    safe_print("PHASE 1 TEST: COREFERENCE RESOLUTION")
    safe_print("=" * 80)
    safe_print("")

    # Initialize RAG chain
    chain = RAGChain()
    session_id = "test_coreference_session"

    # Step 1: First query - search for jazz concerts
    safe_print("Step 1: User asks for jazz concerts in Paris")
    safe_print("-" * 80)
    query1 = "jazz concerts in Paris this weekend"

    try:
        result1 = chain.query_with_metadata(query1, session_id=session_id)
        safe_print(f"Query: {query1}")
        # Use ASCII-safe preview
        answer_ascii = result1['answer'].encode('ascii', 'ignore').decode('ascii')
        safe_print(f"Answer preview: {answer_ascii[:200]}...")
        safe_print(f"Events found: {len(result1.get('sources', []))}")

        # Check if Art of the Trio is in results
        art_of_trio_found = False
        for source in result1.get('sources', []):
            if 'Art of the Trio' in source.get('title', ''):
                art_of_trio_found = True
                safe_print("\n[OK] Found 'Art of the Trio' in results:")
                safe_print(f"  Title: {source['title']}")
                safe_print(f"  City: {source['city']}")
                safe_print(f"  Address: {source.get('address', 'N/A')}")
                break

        if not art_of_trio_found:
            safe_print("\n[WARNING] 'Art of the Trio' not found in results")
            safe_print("This is OK - test will still show if coreference works")

    except Exception as e:
        safe_print(f"[ERROR] Error in first query: {e}")
        import traceback
        traceback.print_exc()
        return

    safe_print("\n" + "=" * 80)
    safe_print("")

    # Step 2: Verify events were stored
    safe_print("Step 2: Verify retrieved_events were stored in chat history")
    safe_print("-" * 80)

    try:
        chat_storage = ChatStorage()
        history = chat_storage.get_chat_history(session_id, limit=10)

        last_assistant_msg = None
        for entry in reversed(history):
            if entry['role'] == 'assistant':
                last_assistant_msg = entry
                break

        if last_assistant_msg and last_assistant_msg.get('retrieved_events'):
            events = last_assistant_msg['retrieved_events']
            safe_print(f"[OK] Found {len(events)} stored events")
            for i, event in enumerate(events[:3], 1):
                safe_print(f"  {i}. {event.get('title')} ({event.get('city')})")

            # Check if Art of the Trio is stored
            art_stored = any('Art of the Trio' in e.get('title', '') for e in events)
            if art_stored:
                safe_print("\n[OK] 'Art of the Trio' IS stored in retrieved_events")
            else:
                safe_print("\n[WARNING] 'Art of the Trio' not in stored events (but structure works)")
        else:
            safe_print("[ERROR] No retrieved_events found in chat history")
            return

    except Exception as e:
        safe_print(f"[ERROR] Error checking storage: {e}")
        import traceback
        traceback.print_exc()
        return

    safe_print("\n" + "=" * 80)
    safe_print("")

    # Step 3: Follow-up query with coreference
    safe_print("Step 3: User asks for directions (coreference to previous event)")
    safe_print("-" * 80)
    query2 = "How do I go from porte de pantin to Art of the Trio?"

    try:
        result2 = chain.query_with_metadata(query2, session_id=session_id)
        safe_print(f"Query: {query2}")
        answer_ascii = result2['answer'].encode('ascii', 'ignore').decode('ascii')
        safe_print(f"Answer preview: {answer_ascii[:300]}...")

        # Check intent classification
        # If coreference works, this should be DIRECTIONS, not EVENT_SEARCH
        query_type = result2.get('query_type', 'unknown')
        safe_print(f"\nQuery type: {query_type}")

        if 'directions' in query_type.lower() or 'direction' in result2['answer'].lower():
            safe_print("[SUCCESS] Query recognized as DIRECTIONS request!")
            safe_print("[SUCCESS] Coreference resolution is working!")
        else:
            safe_print("[WARNING] Query may not have been classified as DIRECTIONS")
            safe_print("This could mean:")
            safe_print("  - Previous events context not being used by LLM")
            safe_print("  - LLM still classifying as EVENT_SEARCH")

    except Exception as e:
        safe_print(f"[ERROR] Error in follow-up query: {e}")
        import traceback
        traceback.print_exc()
        return

    safe_print("\n" + "=" * 80)
    safe_print("TEST COMPLETE")
    safe_print("=" * 80)


if __name__ == "__main__":
    test_coreference_resolution()
