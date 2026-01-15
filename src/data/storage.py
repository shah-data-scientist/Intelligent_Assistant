"""SQLite storage layer for events and embeddings metadata."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.data.models import Event, EventLocation

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class EventRecord(Base):
    """SQLAlchemy model for storing events."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(200), nullable=True, index=True)

    # Location fields
    city = Column(String(200), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True, index=True)
    address = Column(Text, nullable=True)
    coordinates_json = Column(Text, nullable=True)  # JSON: {"lat": ..., "lon": ...}

    # Date fields
    start_date = Column(DateTime, nullable=True, index=True)
    end_date = Column(DateTime, nullable=True)

    # Other fields
    organizer = Column(String(300), nullable=True)
    url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    tags_json = Column(Text, nullable=True)  # JSON array

    # Metadata
    raw_data_json = Column(Text, nullable=True)  # Full raw event data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # FAISS index position (set when indexed)
    faiss_index = Column(Integer, nullable=True, index=True)


class EventStorage:
    """Storage layer for events using SQLite."""

    def __init__(self, db_path: str = "./data/events.db") -> None:
        """Initialize storage with SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,  # Set to True for SQL debugging
        )

        # Create tables
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Initialized EventStorage at {self.db_path}")

    def close(self) -> None:
        """Close database connections and dispose engine."""
        self.engine.dispose()
        logger.debug("Closed EventStorage connections")

    def __enter__(self) -> "EventStorage":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def _event_to_record(self, event: Event, faiss_index: int | None = None) -> EventRecord:
        """Convert Event model to EventRecord for storage.

        Args:
            event: Event object
            faiss_index: Optional FAISS index position

        Returns:
            EventRecord for database storage
        """
        record = EventRecord(
            event_id=event.event_id,
            title=event.title,
            description=event.description,
            category=event.category,
            start_date=event.start_date,
            end_date=event.end_date,
            organizer=event.organizer,
            url=event.url,
            image_url=event.image_url,
            tags_json=json.dumps(event.tags) if event.tags else None,
            raw_data_json=json.dumps(event.raw_data) if event.raw_data else None,
            faiss_index=faiss_index,
        )

        # Extract location fields
        if event.location:
            record.city = event.location.city
            record.postal_code = event.location.postal_code
            record.address = event.location.address
            if event.location.coordinates:
                record.coordinates_json = json.dumps(event.location.coordinates)

        return record

    def _record_to_event(self, record: EventRecord) -> Event:
        """Convert EventRecord to Event model.

        Args:
            record: Database record

        Returns:
            Event object
        """
        # Parse location
        location = None
        if record.city or record.address:
            coordinates = None
            if record.coordinates_json:
                try:
                    coordinates = json.loads(record.coordinates_json)
                except json.JSONDecodeError:
                    pass

            location = EventLocation(
                city=record.city,
                postal_code=record.postal_code,
                address=record.address,
                coordinates=coordinates,
            )

        # Parse tags
        tags = []
        if record.tags_json:
            try:
                tags = json.loads(record.tags_json)
            except json.JSONDecodeError:
                pass

        # Parse raw data
        raw_data = {}
        if record.raw_data_json:
            try:
                raw_data = json.loads(record.raw_data_json)
            except json.JSONDecodeError:
                pass

        return Event(
            event_id=record.event_id,
            title=record.title,
            description=record.description,
            category=record.category,
            location=location,
            start_date=record.start_date,
            end_date=record.end_date,
            organizer=record.organizer,
            url=record.url,
            image_url=record.image_url,
            tags=tags,
            raw_data=raw_data,
        )

    def add_event(self, event: Event, faiss_index: int | None = None) -> bool:
        """Add a single event to storage.

        Args:
            event: Event to store
            faiss_index: Optional FAISS index position

        Returns:
            True if added, False if already exists
        """
        with self.SessionLocal() as session:
            # Check if exists
            existing = session.execute(
                select(EventRecord).where(EventRecord.event_id == event.event_id)
            ).first()

            if existing:
                logger.debug(f"Event {event.event_id} already exists, skipping")
                return False

            # Add new record
            record = self._event_to_record(event, faiss_index)
            session.add(record)
            session.commit()
            logger.debug(f"Added event {event.event_id}")
            return True

    def add_events_bulk(
        self, events: list[Event], faiss_indices: list[int] | None = None
    ) -> int:
        """Add multiple events in bulk.

        Args:
            events: List of events to store
            faiss_indices: Optional list of FAISS indices (must match events length)

        Returns:
            Number of events added
        """
        if faiss_indices and len(faiss_indices) != len(events):
            raise ValueError("faiss_indices must match events length")

        with self.SessionLocal() as session:
            # Get existing event IDs
            existing_ids = {
                row[0]
                for row in session.execute(select(EventRecord.event_id)).all()
            }

            # Filter to new events only
            new_events = [e for e in events if e.event_id not in existing_ids]

            if not new_events:
                logger.info("No new events to add")
                return 0

            # Create records
            records = []
            for i, event in enumerate(new_events):
                faiss_idx = faiss_indices[i] if faiss_indices else None
                records.append(self._event_to_record(event, faiss_idx))

            # Bulk insert
            session.add_all(records)
            session.commit()

            logger.info(f"Added {len(records)} new events to storage")
            return len(records)

    def get_event(self, event_id: str) -> Event | None:
        """Retrieve a single event by ID.

        Args:
            event_id: Event ID to retrieve

        Returns:
            Event object or None if not found
        """
        with self.SessionLocal() as session:
            record = session.execute(
                select(EventRecord).where(EventRecord.event_id == event_id)
            ).scalar_one_or_none()

            if not record:
                return None

            return self._record_to_event(record)

    def get_all_events(
        self,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Event]:
        """Retrieve all events with optional pagination.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of Event objects
        """
        with self.SessionLocal() as session:
            query = select(EventRecord).offset(offset)
            if limit:
                query = query.limit(limit)

            records = session.execute(query).scalars().all()
            return [self._record_to_event(r) for r in records]

    def get_events_by_date_range(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Event]:
        """Retrieve events within date range.

        Args:
            start_date: Minimum start date (inclusive)
            end_date: Maximum start date (inclusive)

        Returns:
            List of Event objects
        """
        with self.SessionLocal() as session:
            query = select(EventRecord)

            if start_date:
                query = query.where(EventRecord.start_date >= start_date)
            if end_date:
                query = query.where(EventRecord.start_date <= end_date)

            records = session.execute(query).scalars().all()
            return [self._record_to_event(r) for r in records]

    def update_event(self, event: Event) -> bool:
        """Update an existing event in storage.

        Args:
            event: Event with updated fields

        Returns:
            True if updated, False if not found
        """
        with self.SessionLocal() as session:
            record = session.execute(
                select(EventRecord).where(EventRecord.event_id == event.event_id)
            ).scalar_one_or_none()

            if not record:
                logger.debug(f"Event {event.event_id} not found for update")
                return False

            # Update fields
            record.title = event.title
            record.description = event.description
            record.category = event.category
            record.start_date = event.start_date
            record.end_date = event.end_date
            record.organizer = event.organizer
            record.url = event.url
            record.image_url = event.image_url
            record.tags_json = json.dumps(event.tags) if event.tags else None
            record.raw_data_json = json.dumps(event.raw_data) if event.raw_data else None

            if event.location:
                record.city = event.location.city
                record.postal_code = event.location.postal_code
                record.address = event.location.address
                if event.location.coordinates:
                    record.coordinates_json = json.dumps(event.location.coordinates)

            session.commit()
            logger.debug(f"Updated event {event.event_id}")
            return True

    def count_events(self) -> int:
        """Count total events in storage.

        Returns:
            Number of events
        """
        with self.SessionLocal() as session:
            return session.query(EventRecord).count()

    def get_existing_event_ids(self) -> set[str]:
        """Get set of all existing event IDs.

        Returns:
            Set of event IDs
        """
        with self.SessionLocal() as session:
            return {
                row[0]
                for row in session.execute(select(EventRecord.event_id)).all()
            }

    def update_faiss_index(self, event_id: str, faiss_index: int) -> bool:
        """Update FAISS index for an event.

        Args:
            event_id: Event ID
            faiss_index: FAISS index position

        Returns:
            True if updated, False if event not found
        """
        with self.SessionLocal() as session:
            record = session.execute(
                select(EventRecord).where(EventRecord.event_id == event_id)
            ).scalar_one_or_none()

            if not record:
                return False

            record.faiss_index = faiss_index
            session.commit()
            return True

    def delete_old_events(self, before_date: datetime) -> int:
        """Delete events older than specified date.

        Args:
            before_date: Delete events with start_date before this

        Returns:
            Number of events deleted
        """
        with self.SessionLocal() as session:
            result = session.query(EventRecord).filter(
                EventRecord.start_date < before_date
            ).delete()
            session.commit()
            logger.info(f"Deleted {result} events before {before_date}")
            return result

    def clear_all(self) -> None:
        """Clear all events from storage (use with caution)."""
        with self.SessionLocal() as session:
            session.query(EventRecord).delete()
            session.commit()
            logger.warning("Cleared all events from storage")
