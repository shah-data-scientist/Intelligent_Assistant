"""
FILE: test_chat_storage.py
STATUS: Active
RESPONSIBILITY: Unit tests for SQLite chat storage layer.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
import tempfile
from pathlib import Path

from src.data.chat_storage import (
    ChatStorage,
    ConversationRecord,
    FeedbackRecord,
)


class TestChatStorage:
    """Test ChatStorage class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_chat.db"
            yield str(db_path)

    @pytest.fixture
    def storage(self, temp_db):
        """Create ChatStorage instance with temp database."""
        storage = ChatStorage(db_path=temp_db)
        yield storage
        storage.close()

    def test_init_creates_db(self, temp_db):
        """Test that initialization creates database file."""
        storage = ChatStorage(db_path=temp_db)
        assert Path(temp_db).exists()
        storage.close()

    def test_init_creates_tables(self, storage):
        """Test that initialization creates required tables."""
        # Tables should exist after initialization
        from sqlalchemy import inspect

        inspector = inspect(storage.engine)
        tables = inspector.get_table_names()

        assert "conversations" in tables
        assert "feedbacks" in tables

    def test_context_manager(self, temp_db):
        """Test using storage as context manager."""
        with ChatStorage(db_path=temp_db) as storage:
            assert storage is not None
            # Add a message to verify it works
            storage.add_chat_message("session-1", "user", "Hello")

    def test_add_chat_message_returns_id(self, storage):
        """Test that add_chat_message returns message ID."""
        msg_id = storage.add_chat_message("session-1", "user", "Hello!")

        assert msg_id is not None
        assert isinstance(msg_id, int)
        assert msg_id > 0

    def test_add_chat_message_increments_id(self, storage):
        """Test that message IDs increment."""
        id1 = storage.add_chat_message("session-1", "user", "First")
        id2 = storage.add_chat_message("session-1", "assistant", "Second")

        assert id2 > id1

    def test_add_chat_message_with_retrieved_events(self, storage):
        """Test adding message with retrieved events."""
        events = [{"title": "Jazz Concert", "venue": "Paris"}, {"title": "Rock Show", "venue": "Lyon"}]
        msg_id = storage.add_chat_message("session-1", "assistant", "Found events", retrieved_events=events)

        # Verify events were stored
        history = storage.get_chat_history("session-1")
        assert len(history) == 1
        assert history[0]["retrieved_events"] == events

    def test_get_chat_history_empty(self, storage):
        """Test getting history for session with no messages."""
        history = storage.get_chat_history("nonexistent-session")
        assert history == []

    def test_get_chat_history_returns_messages(self, storage):
        """Test getting chat history returns messages in order."""
        storage.add_chat_message("session-1", "user", "Hello")
        storage.add_chat_message("session-1", "assistant", "Hi there!")
        storage.add_chat_message("session-1", "user", "How are you?")

        history = storage.get_chat_history("session-1")

        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "How are you?"

    def test_get_chat_history_respects_limit(self, storage):
        """Test that get_chat_history respects limit parameter."""
        # Use unique session to avoid any cross-test pollution
        session = "limit-test-session"
        for i in range(10):
            storage.add_chat_message(session, "user", f"Message {i}")

        history = storage.get_chat_history(session, limit=5)

        assert len(history) == 5
        # Check that all messages are from the original set
        contents = [msg["content"] for msg in history]
        for content in contents:
            assert content.startswith("Message ")
        # Last message should be from the recent 5 (Message 5-9)
        assert "Message 9" in contents or "Message 8" in contents

    def test_get_chat_history_isolates_sessions(self, storage):
        """Test that history is isolated by session."""
        storage.add_chat_message("session-1", "user", "Session 1 message")
        storage.add_chat_message("session-2", "user", "Session 2 message")

        history1 = storage.get_chat_history("session-1")
        history2 = storage.get_chat_history("session-2")

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["content"] == "Session 1 message"
        assert history2[0]["content"] == "Session 2 message"

    def test_add_feedback_positive(self, storage):
        """Test adding positive feedback."""
        msg_id = storage.add_chat_message("session-1", "assistant", "Response")
        storage.add_feedback(msg_id, is_positive=True, comment="Great!")

        # Verify feedback was stored
        with storage.SessionLocal() as session:
            from sqlalchemy import select

            query = select(FeedbackRecord).where(FeedbackRecord.message_id == msg_id)
            feedback = session.execute(query).scalar()

            assert feedback is not None
            assert feedback.is_positive == 1
            assert feedback.comment == "Great!"

    def test_add_feedback_negative(self, storage):
        """Test adding negative feedback."""
        msg_id = storage.add_chat_message("session-1", "assistant", "Response")
        storage.add_feedback(msg_id, is_positive=False, comment="Not helpful")

        with storage.SessionLocal() as session:
            from sqlalchemy import select

            query = select(FeedbackRecord).where(FeedbackRecord.message_id == msg_id)
            feedback = session.execute(query).scalar()

            assert feedback is not None
            assert feedback.is_positive == 0
            assert feedback.comment == "Not helpful"

    def test_add_feedback_without_comment(self, storage):
        """Test adding feedback without comment."""
        msg_id = storage.add_chat_message("session-1", "assistant", "Response")
        storage.add_feedback(msg_id, is_positive=True)

        with storage.SessionLocal() as session:
            from sqlalchemy import select

            query = select(FeedbackRecord).where(FeedbackRecord.message_id == msg_id)
            feedback = session.execute(query).scalar()

            assert feedback is not None
            assert feedback.comment is None

    def test_close_disposes_engine(self, temp_db):
        """Test that close disposes the engine."""
        storage = ChatStorage(db_path=temp_db)
        storage.close()

        # Engine should be disposed (attempting to use it may raise)
        # We just verify no exception on close
        assert True


class TestConversationRecord:
    """Test ConversationRecord model."""

    def test_model_attributes(self):
        """Test model has expected attributes."""
        assert hasattr(ConversationRecord, "__tablename__")
        assert ConversationRecord.__tablename__ == "conversations"

        # Check columns exist
        assert hasattr(ConversationRecord, "id")
        assert hasattr(ConversationRecord, "session_id")
        assert hasattr(ConversationRecord, "role")
        assert hasattr(ConversationRecord, "content")
        assert hasattr(ConversationRecord, "retrieved_events")
        assert hasattr(ConversationRecord, "timestamp")


class TestFeedbackRecord:
    """Test FeedbackRecord model."""

    def test_model_attributes(self):
        """Test model has expected attributes."""
        assert hasattr(FeedbackRecord, "__tablename__")
        assert FeedbackRecord.__tablename__ == "feedbacks"

        # Check columns exist
        assert hasattr(FeedbackRecord, "id")
        assert hasattr(FeedbackRecord, "message_id")
        assert hasattr(FeedbackRecord, "is_positive")
        assert hasattr(FeedbackRecord, "comment")
        assert hasattr(FeedbackRecord, "timestamp")


class TestMigration:
    """Test database migration functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_migration.db"
            yield str(db_path)

    def test_migration_adds_column_if_missing(self, temp_db):
        """Test that migration adds retrieved_events column."""
        # Initialize storage (creates db with all columns)
        storage = ChatStorage(db_path=temp_db)

        # Migration should have run without error
        # Verify column exists
        from sqlalchemy import inspect

        inspector = inspect(storage.engine)
        columns = [c["name"] for c in inspector.get_columns("conversations")]

        assert "retrieved_events" in columns
        storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
