"""Pydantic schemas for API requests and responses."""

from typing import List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str = Field(..., min_length=1, max_length=1000, description="User's question about cultural events")
    language: Optional[str] = Field(None, description="Preferred language (fr/en). If None, auto-detected.")

class SourceDocument(BaseModel):
    """Model representing a source event."""
    title: Optional[str]
    city: Optional[str]
    date: Optional[str]
    url: Optional[str]
    score: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str = Field(..., description="Generated answer from the assistant")
    sources: List[SourceDocument] = Field(default_factory=list, description="List of events used as context")
    message_id: Optional[int] = Field(None, description="Database ID of the assistant's message for feedback")

class FeedbackRequest(BaseModel):
    """Request model for feedback endpoint."""
    message_id: int = Field(..., description="The ID of the assistant message")
    is_positive: bool = Field(..., description="True for thumbs up, False for thumbs down")
    comment: Optional[str] = Field(None, description="Optional explanation for negative feedback")
