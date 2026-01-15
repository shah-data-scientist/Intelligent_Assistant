"""Pydantic schemas for API requests and responses."""

from typing import List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str = Field(..., min_length=3, max_length=1000, description="User's question about cultural events")
    language: Optional[str] = Field(None, description="Preferred language (fr/en). If None, auto-detected.")

class SourceDocument(BaseModel):
    """Model representing a source event."""
    title: Optional[str]
    city: Optional[str]
    date: Optional[str]
    url: Optional[str]
    score: float

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str = Field(..., description="Generated answer from the assistant")
    sources: List[SourceDocument] = Field(default_factory=list, description="List of events used as context")
