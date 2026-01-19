"""Data models for cultural events."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventLocation(BaseModel):
    """Event location information."""

    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    coordinates: dict[str, float] | None = None


class Event(BaseModel):
    """Cultural event model."""

    event_id: str = Field(..., description="Unique event identifier")
    title: str = Field(..., description="Event title")
    description: str | None = Field(None, description="Event description")
    category: str | None = Field(None, description="Event category")
    location: EventLocation | None = Field(None, description="Event location")
    start_date: datetime | None = Field(None, description="Event start date")
    end_date: datetime | None = Field(None, description="Event end date")
    organizer: str | None = Field(None, description="Event organizer")
    url: str | None = Field(None, description="Event URL")
    image_url: str | None = Field(None, description="Event image URL")
    tags: list[str] = Field(default_factory=list, description="Event tags")
    raw_data: dict[str, Any] = Field(
        default_factory=dict, description="Original raw data from API"
    )
    scraped_content: str | None = Field(None, description="Enriched content from URL")
    
    # New metadata fields
    age_min: int | None = Field(None, description="Minimum age")
    age_max: int | None = Field(None, description="Maximum age")
    accessibility: str | None = Field(None, description="Accessibility info")
    conditions: str | None = Field(None, description="Pricing or entry conditions")

    def to_text(self) -> str:
        """Convert event to text representation for embedding.

        URLs and critical information are placed first to help prevent hallucination.

        Returns:
            Text representation of the event
        """
        parts = []

        # Title and URL first (most important for preventing URL hallucination)
        parts.append(f"Titre: {self.title}")
        if self.url:
            parts.append(f"Lien de l'événement: {self.url}")

        # Core details
        if self.category:
            parts.append(f"Catégorie: {self.category}")

        if self.start_date:
            parts.append(f"Date de début: {self.start_date.strftime('%d/%m/%Y %H:%M')}")
        if self.end_date:
            parts.append(f"Date de fin: {self.end_date.strftime('%d/%m/%Y %H:%M')}")

        # Location information
        if self.location:
            if self.location.address:
                parts.append(f"Adresse: {self.location.address}")
            if self.location.city:
                parts.append(f"Ville: {self.location.city}")
            if self.location.postal_code:
                parts.append(f"Code postal: {self.location.postal_code}")

        # Descriptions (after core details)
        if self.description:
            parts.append(f"Description: {self.description}")

        if self.scraped_content:
            parts.append(f"Description complète: {self.scraped_content}")

        # Additional metadata
        if self.tags:
            parts.append(f"Mots-clés: {', '.join(self.tags)}")
        if self.organizer:
            parts.append(f"Organisateur: {self.organizer}")
        if self.conditions:
            parts.append(f"Conditions et Tarifs: {self.conditions}")
        if self.accessibility:
            parts.append(f"Accessibilité: {self.accessibility}")

        return "\n".join(parts)

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata for vector store filtering.

        Returns:
            Dictionary of metadata fields
        """
        metadata = {
            "event_id": self.event_id,
            "title": self.title,
            "category": self.category or "unknown",
        }

        if self.location and self.location.city:
            metadata["city"] = self.location.city

        if self.start_date:
            metadata["start_date"] = self.start_date.isoformat()
            metadata["year"] = self.start_date.year
            metadata["month"] = self.start_date.month

        if self.url:
            metadata["url"] = self.url

        return metadata


class ChatMessage(BaseModel):
    """Model for a single chat message."""

    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Feedback(BaseModel):
    """Model for user feedback."""

    message_id: int
    is_positive: bool
    comment: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
