"""Pydantic schemas for API requests and responses."""

from typing import List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str = Field(..., min_length=1, max_length=1000, description="User's question about cultural events")
    session_id: str = Field(default="default_session", description="Unique session identifier for chat history")
    language: Optional[str] = Field(None, description="Preferred language (fr/en). If None, auto-detected.")
    age: Optional[int] = Field(None, description="Specific age filter")

class SourceDocument(BaseModel):
    """Model representing a source event."""
    title: Optional[str] = None
    city: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    score: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_id: Optional[str] = None
    category: Optional[str] = None
    match_type: Optional[str] = None

class StructuredEvent(BaseModel):
    """Model for formatted event details shown in UI cards."""
    title: str
    date: str
    city: str
    location: Optional[str] = None
    url: Optional[str] = None
    price_label: Optional[str] = "Unknown"
    age_label: Optional[str] = "Unknown"
    times: List[str] = Field(default_factory=list, description="List of available times if event has multiple showings")
    times_display: Optional[str] = Field(default="", description="Formatted times for display (e.g., '19:30, 21:30')")

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str = Field(..., description="Generated answer from the assistant")
    sources: List[SourceDocument] = Field(default_factory=list, description="List of events used as context")
    structured_events: List[StructuredEvent] = Field(default_factory=list, description="List of formatted event cards")
    message_id: Optional[int] = Field(None, description="Database ID of the assistant's message for feedback")
    needs_clarification: bool = Field(default=False, description="True if the query was too broad and clarifying questions were asked")
    clarifying_questions: List[str] = Field(default_factory=list, description="List of clarifying questions asked to the user")

class FeedbackRequest(BaseModel):
    """Request model for feedback endpoint."""
    message_id: int = Field(..., description="The ID of the assistant message")
    is_positive: bool = Field(..., description="True for thumbs up, False for thumbs down")
    comment: Optional[str] = Field(None, description="Optional explanation for negative feedback")
