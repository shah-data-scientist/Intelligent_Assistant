"""Pydantic schemas for structured LLM output."""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class IntentEnum(str, Enum):
    """Query intent types."""
    EVENT_SEARCH = "event_search"
    GREETING = "greeting"
    CHITCHAT = "chitchat"
    CAPABILITY = "capability"
    DIRECTIONS = "directions"
    ABUSE = "abuse"
    OFF_TOPIC = "off_topic"


class DimensionDetection(BaseModel):
    """Detection result for a specific dimension."""
    detected: bool = Field(description="Whether this dimension was detected")
    value: Optional[str] = Field(None, description="Extracted value if applicable")


class StructuredFilters(BaseModel):
    """Structured search filters extracted from query."""
    city: Optional[str] = Field(None, description="City name mentioned in query")
    category: Optional[str] = Field(None, description="Event category/type")
    month: Optional[int] = Field(None, description="Month number (1-12)")
    year: Optional[int] = Field(None, description="Year")
    day: Optional[int] = Field(None, description="Day of month")
    is_free: Optional[bool] = Field(None, description="Whether user wants free events")
    audience: Optional[str] = Field(None, description="Target audience (children, adults, family)")


class CoreferenceInfo(BaseModel):
    """Coreference resolution information."""
    references_previous: bool = Field(
        False,
        description="Whether query references events from previous results"
    )
    event_id: Optional[str] = Field(None, description="Referenced event ID if identified")
    event_name: Optional[str] = Field(None, description="Referenced event name if identified")
    reference_type: Literal["event", "venue", "last_result", "none"] = Field(
        "none",
        description="Type of reference"
    )


class UnifiedAnalysisSchema(BaseModel):
    """Structured output schema for unified query analysis."""

    # Primary intent classification
    intent: IntentEnum = Field(description="Primary intent of the query")
    intent_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in intent classification (0.0-1.0)"
    )

    # Entity extraction
    city: Optional[str] = Field(None, description="Raw city name from query")
    city_normalized: Optional[str] = Field(None, description="Normalized city name")
    event_type: Optional[str] = Field(None, description="Type of event mentioned")
    timeframe: Optional[str] = Field(None, description="Temporal expression (e.g., 'this weekend')")

    # Filters
    filters: StructuredFilters = Field(default_factory=StructuredFilters, description="Extracted search filters")

    # Refined search query
    refined_query: str = Field(description="Refined search query text")

    # Language detection
    detected_language: Literal["fr", "en"] = Field("fr", description="Detected language")

    # Dimensions (multi-dimensional classification)
    is_greeting: bool = Field(False, description="Query contains greeting")
    has_typo: bool = Field(False, description="Query has typos that were corrected")
    original_query: Optional[str] = Field(None, description="Original query if typo was detected")
    corrected_query: Optional[str] = Field(None, description="Corrected query")
    is_statistical: bool = Field(False, description="User wants count/statistics")
    wants_all_events: bool = Field(False, description="User wants all events without specific type")

    # Coreference resolution
    coreference: CoreferenceInfo = Field(
        default_factory=CoreferenceInfo,
        description="Coreference resolution information"
    )

    # Completeness check
    is_complete: bool = Field(description="Whether query has enough information for search")
    missing_info: list[str] = Field(
        default_factory=list,
        description="List of missing information (city, event_type, timeframe)"
    )

    # Reasoning (for debugging)
    reasoning: str = Field(description="Step-by-step reasoning for classification")


class StructuredMultiIntent(BaseModel):
    """For handling queries with multiple intents."""
    primary_intent: IntentEnum
    secondary_intent: Optional[IntentEnum] = None
    analysis: UnifiedAnalysisSchema
