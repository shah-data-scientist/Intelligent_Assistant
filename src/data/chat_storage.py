"""SQLite storage layer for chat history and feedback."""

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
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings

logger = logging.getLogger(__name__)


class ChatBase(DeclarativeBase):
    """Base class for Chat SQLAlchemy models."""

    pass


class ConversationRecord(ChatBase):
    """SQLAlchemy model for storing chat history."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    retrieved_events = Column(Text, nullable=True)  # JSON string of retrieved events for context
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class FeedbackRecord(ChatBase):
    """SQLAlchemy model for storing user feedback."""

    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False, index=True)  # Links to ConversationRecord.id
    is_positive = Column(Integer, nullable=False)  # 1 for thumbs up, 0 for thumbs down
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class ChatStorage:
    """Storage layer for chat history using SQLite."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize storage with SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path or settings.chat_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with proper SQLite configuration
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={
                "timeout": 30,  # 30 second timeout for database locks
                "check_same_thread": False  # Allow multi-threaded access
            },
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        # Create tables
        ChatBase.metadata.create_all(self.engine)

        # Enable WAL mode for better concurrency
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()

        # Migrate existing database: add retrieved_events column if it doesn't exist
        self._migrate_add_retrieved_events()

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Initialized ChatStorage at {self.db_path}")

    def _migrate_add_retrieved_events(self) -> None:
        """Add retrieved_events column to existing databases if it doesn't exist."""
        try:
            with self.engine.connect() as conn:
                # Check if column exists
                result = conn.execute(text("PRAGMA table_info(conversations)"))
                columns = [row[1] for row in result]

                if "retrieved_events" not in columns:
                    logger.info("Migrating database: adding retrieved_events column")
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN retrieved_events TEXT"))
                    conn.commit()
                    logger.info("Migration complete")
        except Exception as e:
            logger.warning(f"Migration check failed (may be expected): {e}")

    def close(self) -> None:
        """Close database connections and dispose engine."""
        self.engine.dispose()
        logger.debug("Closed ChatStorage connections")

    def __enter__(self) -> "ChatStorage":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        retrieved_events: list[dict] | None = None
    ) -> int:
        """Add a chat message to history and return its ID.

        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Message content
            retrieved_events: Optional list of retrieved events for coreference resolution

        Returns:
            The ID of the inserted message record.
        """
        with self.SessionLocal() as session:
            # Serialize retrieved_events to JSON if provided
            events_json = None
            if retrieved_events:
                events_json = json.dumps(retrieved_events)

            record = ConversationRecord(
                session_id=session_id,
                role=role,
                content=content,
                retrieved_events=events_json
            )
            session.add(record)
            session.commit()
            return record.id

    def add_feedback(self, message_id: int, is_positive: bool, comment: str | None = None) -> None:
        """Add user feedback for a specific message.

        Args:
            message_id: The ID of the message being rated
            is_positive: True for thumbs up, False for thumbs down
            comment: Optional detailed feedback
        """
        with self.SessionLocal() as session:
            record = FeedbackRecord(
                message_id=message_id,
                is_positive=1 if is_positive else 0,
                comment=comment
            )
            session.add(record)
            session.commit()
            logger.info(f"Added {'positive' if is_positive else 'negative'} feedback for message {message_id}")

    def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get chat history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of recent messages to retrieve

        Returns:
            List of dicts with 'role', 'content', and optionally 'retrieved_events', ordered chronologically.
        """
        with self.SessionLocal() as session:
            # Fetch most recent messages
            query = (
                select(ConversationRecord)
                .where(ConversationRecord.session_id == session_id)
                .order_by(ConversationRecord.timestamp.desc())
                .limit(limit)
            )
            records = session.execute(query).scalars().all()

            # Reverse to return chronological order
            history = []
            for r in reversed(records):
                entry = {"role": r.role, "content": r.content}

                # Deserialize retrieved_events if present
                if r.retrieved_events:
                    try:
                        entry["retrieved_events"] = json.loads(r.retrieved_events)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode retrieved_events for message {r.id}")
                        entry["retrieved_events"] = None
                else:
                    entry["retrieved_events"] = None

                history.append(entry)

            return history
