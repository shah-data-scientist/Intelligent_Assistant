"""Test conversational multi-turn query handling."""

import logging
import uuid
from src.retrieval.chain import RAGChain

logging.basicConfig(level=logging.WARNING)

chain = RAGChain()

# Simulate a conversational sequence
session_id = f"conv_test_{uuid.uuid4().hex[:8]}"

print("="*80)
print("CONVERSATIONAL INTERACTION TEST")
print("="*80)

# Turn 1: Initial query
query1 = "Concerts de jazz à Paris en février"
print(f"\n[Turn 1] USER: {query1}")
result1 = chain.query_with_metadata(query1, session_id=session_id)
answer1 = result1["answer"]
print(f"[Turn 1] ASSISTANT: {answer1[:300]}...")

# Turn 2: Follow-up referencing previous answer
query2 = "Tell me more about the first one"
print(f"\n[Turn 2] USER: {query2}")
result2 = chain.query_with_metadata(query2, session_id=session_id)
answer2 = result2["answer"]
print(f"[Turn 2] ASSISTANT: {answer2}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("\nDid the system:")
print("1. Remember the context from Turn 1? (Should know what 'the first one' refers to)")
print("2. Provide more details about the specific event mentioned first?")
print("3. Avoid repeating the full list or asking what 'first one' means?")
