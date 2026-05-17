"""Debug script for structured output with LangChain Google Genai."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("DEBUG: Structured Output Test")
print("=" * 60)

# Check versions
try:

    print("langchain_google_genai loaded")
except Exception as e:
    print(f"langchain_google_genai import error: {e}")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import Optional


# Simple test schema
class SimpleExtraction(BaseModel):
    """Simple extraction for testing."""

    city: Optional[str] = Field(None, description="City name mentioned in query")
    event_type: Optional[str] = Field(None, description="Type of event")
    language: str = Field("fr", description="Detected language")


api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: No GOOGLE_API_KEY found")
    sys.exit(1)

print(f"API Key: {api_key[:15]}...")

# Create LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0,
    google_api_key=api_key,
)
print(f"LLM created: {type(llm).__name__}")

# Test basic invocation first
print("\n1. Testing basic invocation...")
try:
    basic_response = llm.invoke("Say OK")
    print(f"   Basic response: {basic_response.content[:50]}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")

# Test with_structured_output
print("\n2. Testing with_structured_output...")
try:
    structured_llm = llm.with_structured_output(SimpleExtraction)
    print(f"   Structured LLM created: {type(structured_llm)}")

    messages = [
        SystemMessage(content="Extract city and event type from the query."),
        HumanMessage(content="Jazz concerts in Paris"),
    ]

    result = structured_llm.invoke(messages)
    print(f"   Result type: {type(result).__name__}")
    print(f"   City: {result.city}")
    print(f"   Event type: {result.event_type}")
    print(f"   Language: {result.language}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

# Test with the actual UnifiedAnalysisSchema
print("\n3. Testing with UnifiedAnalysisSchema...")
try:
    from src.retrieval.schemas import UnifiedAnalysisSchema

    structured_llm2 = llm.with_structured_output(UnifiedAnalysisSchema)
    print("   Structured LLM created with UnifiedAnalysisSchema")

    messages = [
        SystemMessage(content="You are a query analyzer. Extract all entities."),
        HumanMessage(content="Query: Jazz concerts in Paris"),
    ]

    result = structured_llm2.invoke(messages)
    print(f"   Result type: {type(result).__name__}")
    print(f"   City: {result.city}")
    print(f"   City normalized: {result.city_normalized}")
    print(f"   Event type: {result.event_type}")
    print(f"   Intent: {result.intent}")
    print(f"   Filters: {result.filters}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)
