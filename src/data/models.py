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
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Original raw data from API")
    scraped_content: str | None = Field(None, description="Enriched content from URL")

    # New metadata fields
    age_min: int | None = Field(None, description="Minimum age")
    age_max: int | None = Field(None, description="Maximum age")
    accessibility: str | None = Field(None, description="Accessibility info")
    conditions: str | None = Field(None, description="Pricing or entry conditions")

    # Derived display labels (pre-computed, no runtime enrichment needed)
    price_label: str = Field("Non spécifié", description="Display-ready price label")
    age_label: str = Field("Tout public", description="Display-ready age label")

    # Multi-showtime fields (for deduplicated events)
    timings: list[str] = Field(default_factory=list, description="List of show times (e.g., ['10:00', '14:00'])")
    periods: list[str] = Field(default_factory=list, description="Periods of day (e.g., ['matin', 'après-midi'])")
    is_full_day: bool = Field(False, description="Whether event spans full day without specific times")

    # Period filter flags (indexed for fast filtering)
    has_morning: bool = Field(False, description="Has showtime before 12:00")
    has_afternoon: bool = Field(False, description="Has showtime 12:00-18:00")
    has_evening: bool = Field(False, description="Has showtime after 18:00")

    def to_text(self, include_metadata_prefix: bool = True) -> str:
        """Convert event to text representation for embedding.

        URLs and critical information are placed first to help prevent hallucination.

        Args:
            include_metadata_prefix: Whether to include explicit metadata prefix for better retrieval

        Returns:
            Text representation of the event
        """
        parts = []

        # Add explicit metadata prefix for better semantic matching
        if include_metadata_prefix and self.location and self.location.city and self.category:
            metadata_prefix = f"[Ville: {self.location.city}] [Catégorie: {self.category}]"
            if self.start_date:
                month_year = self.start_date.strftime("%B %Y")
                metadata_prefix += f" [Date: {month_year}]"
            parts.append(metadata_prefix)
            parts.append("")  # Blank line separator

        # Title and URL first (most important for preventing URL hallucination)
        parts.append(f"Titre: {self.title}")
        if self.url:
            parts.append(f"🔗 Lien de l'événement: {self.url}")

        # Core details
        if self.category:
            parts.append(f"Catégorie: {self.category}")

        if self.start_date:
            parts.append(f"Date de début: {self.start_date.strftime('%d/%m/%Y %H:%M')}")
        if self.end_date:
            parts.append(f"Date de fin: {self.end_date.strftime('%d/%m/%Y %H:%M')}")

        # Multi-showtime information
        if self.timings:
            parts.append(f"Horaires: {', '.join(self.timings)}")
        if self.periods:
            parts.append(f"Créneaux: {', '.join(self.periods)}")
        if self.is_full_day:
            parts.append("Événement toute la journée")

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

    def to_chunks(self, max_tokens: int = 400, overlap_tokens: int = 50) -> list[str]:
        """Split event into overlapping chunks for better embedding quality.

        For events with long descriptions, splitting into smaller chunks improves
        semantic search precision by avoiding diluted embeddings.

        Args:
            max_tokens: Maximum tokens per chunk (default: 400)
            overlap_tokens: Tokens to overlap between chunks (default: 50)

        Returns:
            List of text chunks. If event is short, returns single chunk.
        """
        full_text = self.to_text(include_metadata_prefix=True)

        # Rough token estimation: 1 token ≈ 4 characters
        estimated_tokens = len(full_text) // 4

        # If short enough, return as single chunk
        if estimated_tokens <= max_tokens:
            return [full_text]

        # Split into sentences (simple approach)
        import re

        sentences = re.split(r"(?<=[.!?])\s+", full_text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        # Build metadata header that appears in every chunk
        metadata_header = ""
        if self.location and self.location.city:
            metadata_header = f"[Ville: {self.location.city}]"
        if self.category:
            metadata_header += f" [Catégorie: {self.category}]"
        if self.title:
            metadata_header += f"\nTitre: {self.title}"
        if self.url:
            metadata_header += f"\n🔗 Lien: {self.url}"

        metadata_tokens = len(metadata_header) // 4
        effective_max = max_tokens - metadata_tokens

        for sentence in sentences:
            sentence_tokens = len(sentence) // 4

            # If adding this sentence would exceed limit and we have content, create chunk
            if current_tokens + sentence_tokens > effective_max and current_chunk:
                chunk_text = metadata_header + "\n" + " ".join(current_chunk)
                chunks.append(chunk_text)

                # Keep last sentences for overlap (approximate 50 tokens)
                overlap_size = 0
                overlap_sentences = []
                for sent in reversed(current_chunk):
                    sent_tokens = len(sent) // 4
                    if overlap_size + sent_tokens > overlap_tokens:
                        break
                    overlap_sentences.insert(0, sent)
                    overlap_size += sent_tokens

                current_chunk = overlap_sentences
                current_tokens = overlap_size

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Add remaining content as final chunk
        if current_chunk:
            chunk_text = metadata_header + "\n" + " ".join(current_chunk)
            chunks.append(chunk_text)

        return chunks if chunks else [full_text]

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

        # Price and age labels (pre-computed in database)
        metadata["price_label"] = self.price_label
        metadata["age_label"] = self.age_label

        # Raw conditions and age fields for detailed display
        if self.conditions:
            metadata["conditions"] = self.conditions
        if self.age_min is not None:
            metadata["age_min"] = self.age_min
        if self.age_max is not None:
            metadata["age_max"] = self.age_max

        # Multi-showtime metadata
        if self.timings:
            metadata["timings"] = self.timings
        if self.periods:
            metadata["periods"] = self.periods
        if self.is_full_day:
            metadata["is_full_day"] = True

        # Location details for display
        if self.location:
            if self.location.address:
                metadata["address"] = self.location.address
            if self.location.postal_code:
                metadata["postal_code"] = self.location.postal_code

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
