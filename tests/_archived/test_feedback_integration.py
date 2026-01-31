"""
FILE: test_feedback_integration.py
STATUS: Active
RESPONSIBILITY: Integration tests for feedback storage, analysis, and API endpoints.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Feedback system validation

IMPORTS (What this file needs):
- pytest: Test framework
- tempfile: Temporary database for testing
- datetime, timedelta: Time-based testing
- pathlib: Path operations
- src.data.chat_storage: ChatStorage for feedback persistence
- src.analysis.feedback_analyzer: FeedbackAnalyzer for analysis

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.data.chat_storage import ChatStorage
from src.analysis.feedback_analyzer import FeedbackAnalyzer


@pytest.fixture
def temp_chat_storage():
    """Create temporary ChatStorage for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    storage = ChatStorage(db_path=db_path)
    yield storage
    storage.close()

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestFeedbackStorage:
    """Test feedback storage in conversations table."""

    def test_add_feedback_to_conversation(self, temp_chat_storage):
        """Test adding feedback to a conversation message."""
        # Add a conversation
        msg_id = temp_chat_storage.add_chat_message(
            session_id="test_session", role="assistant", content="Here are some jazz concerts in Paris..."
        )

        # Add positive feedback
        temp_chat_storage.add_feedback(message_id=msg_id, is_positive=True, comment="Great suggestions!")

        # Verify feedback was added (check via raw SQL)
        with temp_chat_storage.SessionLocal() as session:
            from src.data.chat_storage import ConversationRecord

            record = session.query(ConversationRecord).filter(ConversationRecord.id == msg_id).first()

            assert record is not None
            assert record.feedback_rating == "positive"
            assert record.feedback_comment == "Great suggestions!"
            assert record.feedback_timestamp is not None

    def test_add_negative_feedback(self, temp_chat_storage):
        """Test adding negative feedback."""
        msg_id = temp_chat_storage.add_chat_message(
            session_id="test_session", role="assistant", content="No events found."
        )

        temp_chat_storage.add_feedback(
            message_id=msg_id, is_positive=False, comment="Wrong results, I asked for Paris not Lyon"
        )

        with temp_chat_storage.SessionLocal() as session:
            from src.data.chat_storage import ConversationRecord

            record = session.query(ConversationRecord).filter(ConversationRecord.id == msg_id).first()

            assert record.feedback_rating == "negative"
            assert "Paris" in record.feedback_comment

    def test_add_feedback_without_comment(self, temp_chat_storage):
        """Test adding feedback without optional comment."""
        msg_id = temp_chat_storage.add_chat_message(
            session_id="test_session", role="assistant", content="Found 5 events."
        )

        temp_chat_storage.add_feedback(message_id=msg_id, is_positive=True, comment=None)

        with temp_chat_storage.SessionLocal() as session:
            from src.data.chat_storage import ConversationRecord

            record = session.query(ConversationRecord).filter(ConversationRecord.id == msg_id).first()

            assert record.feedback_rating == "positive"
            assert record.feedback_comment is None

    def test_add_feedback_to_nonexistent_message(self, temp_chat_storage):
        """Test adding feedback to non-existent message ID."""
        # Should not raise error, just log warning
        temp_chat_storage.add_feedback(message_id=99999, is_positive=True, comment="This message doesn't exist")

    def test_update_existing_feedback(self, temp_chat_storage):
        """Test that feedback can be updated (overwrite)."""
        msg_id = temp_chat_storage.add_chat_message(
            session_id="test_session", role="assistant", content="Response content"
        )

        # Add positive feedback
        temp_chat_storage.add_feedback(message_id=msg_id, is_positive=True, comment="First feedback")

        # Update to negative feedback
        temp_chat_storage.add_feedback(message_id=msg_id, is_positive=False, comment="Changed my mind")

        with temp_chat_storage.SessionLocal() as session:
            from src.data.chat_storage import ConversationRecord

            record = session.query(ConversationRecord).filter(ConversationRecord.id == msg_id).first()

            # Should have the updated feedback
            assert record.feedback_rating == "negative"
            assert record.feedback_comment == "Changed my mind"


class TestFeedbackAnalyzer:
    """Test FeedbackAnalyzer class."""

    def test_analyze_feedback_no_data(self, temp_chat_storage):
        """Test analysis with no feedback data."""
        analyzer = FeedbackAnalyzer(temp_chat_storage)
        result = analyzer.analyze_feedback(days=30, min_feedback_count=1)

        assert result["summary"]["total_feedback"] == 0
        assert "message" in result

    def test_analyze_feedback_with_data(self, temp_chat_storage):
        """Test analysis with mixed positive and negative feedback."""
        # Add user query
        temp_chat_storage.add_chat_message(session_id="session1", role="user", content="Jazz concerts in Paris?")

        # Add assistant response with positive feedback
        msg_id1 = temp_chat_storage.add_chat_message(
            session_id="session1", role="assistant", content="Found 3 jazz concerts."
        )
        temp_chat_storage.add_feedback(msg_id1, is_positive=True, comment="Perfect!")

        # Add another query and response with negative feedback
        temp_chat_storage.add_chat_message(session_id="session2", role="user", content="Free events this weekend")
        msg_id2 = temp_chat_storage.add_chat_message(
            session_id="session2", role="assistant", content="No results found."
        )
        temp_chat_storage.add_feedback(msg_id2, is_positive=False, comment="No results found")

        # Analyze
        analyzer = FeedbackAnalyzer(temp_chat_storage)
        result = analyzer.analyze_feedback(days=30, min_feedback_count=1)

        assert result["summary"]["total_feedback"] == 2
        assert result["summary"]["positive_count"] == 1
        assert result["summary"]["negative_count"] == 1
        assert result["summary"]["satisfaction_rate"] == 50.0

    def test_pattern_identification(self, temp_chat_storage):
        """Test identification of patterns in negative feedback."""
        # Add multiple negative feedback entries with "no results" pattern
        for i in range(3):
            temp_chat_storage.add_chat_message(session_id=f"session{i}", role="user", content=f"Query {i}")
            msg_id = temp_chat_storage.add_chat_message(session_id=f"session{i}", role="assistant", content="Response")
            temp_chat_storage.add_feedback(msg_id, is_positive=False, comment="No results found")

        analyzer = FeedbackAnalyzer(temp_chat_storage)
        result = analyzer.analyze_feedback(days=30)

        patterns = result["patterns"]
        assert patterns["total_negative_with_comments"] == 3
        assert "no_results" in patterns["issue_breakdown"]
        assert patterns["issue_breakdown"]["no_results"] == 3

    def test_proposed_solutions_generation(self, temp_chat_storage):
        """Test that proposed solutions are generated."""
        # Add negative feedback with specific issue
        temp_chat_storage.add_chat_message(session_id="session1", role="user", content="Query")
        msg_id = temp_chat_storage.add_chat_message(session_id="session1", role="assistant", content="Response")
        temp_chat_storage.add_feedback(msg_id, is_positive=False, comment="Wrong results returned")

        analyzer = FeedbackAnalyzer(temp_chat_storage)
        result = analyzer.analyze_feedback(days=30)

        solutions = result["proposed_solutions"]
        assert len(solutions) > 0
        assert any(s["priority"] == "HIGH" for s in solutions)
        assert any("actionable_steps" in s for s in solutions)

    def test_get_negative_feedback_queries(self, temp_chat_storage):
        """Test extraction of queries with negative feedback."""
        # Add negative feedback
        temp_chat_storage.add_chat_message(session_id="session1", role="user", content="Test query")
        msg_id = temp_chat_storage.add_chat_message(session_id="session1", role="assistant", content="Test response")
        temp_chat_storage.add_feedback(msg_id, is_positive=False, comment="Bad")

        analyzer = FeedbackAnalyzer(temp_chat_storage)
        queries = analyzer.get_negative_feedback_queries(days=30, limit=10)

        assert len(queries) == 1
        assert queries[0]["user_query"] == "Test query"
        assert queries[0]["feedback_comment"] == "Bad"

    def test_satisfaction_rate_calculation(self, temp_chat_storage):
        """Test satisfaction rate calculation."""
        # Add 7 positive, 3 negative (70% satisfaction)
        for i in range(7):
            msg_id = temp_chat_storage.add_chat_message(session_id=f"session{i}", role="assistant", content="Response")
            temp_chat_storage.add_feedback(msg_id, is_positive=True)

        for i in range(7, 10):
            msg_id = temp_chat_storage.add_chat_message(session_id=f"session{i}", role="assistant", content="Response")
            temp_chat_storage.add_feedback(msg_id, is_positive=False)

        analyzer = FeedbackAnalyzer(temp_chat_storage)
        stats = analyzer.get_satisfaction_rate(days=30)

        assert stats["total_feedback"] == 10
        assert stats["positive_count"] == 7
        assert stats["negative_count"] == 3
        assert stats["satisfaction_rate"] == 70.0

    def test_time_window_filtering(self, temp_chat_storage):
        """Test that time window filtering works."""
        # Add old feedback (35 days ago)
        old_msg_id = temp_chat_storage.add_chat_message(
            session_id="old_session", role="assistant", content="Old response"
        )

        # Manually set old timestamp
        with temp_chat_storage.SessionLocal() as session:
            from src.data.chat_storage import ConversationRecord

            record = session.query(ConversationRecord).filter(ConversationRecord.id == old_msg_id).first()
            record.feedback_rating = "positive"
            record.feedback_timestamp = datetime.utcnow() - timedelta(days=35)
            session.commit()

        # Add recent feedback
        recent_msg_id = temp_chat_storage.add_chat_message(
            session_id="recent_session", role="assistant", content="Recent response"
        )
        temp_chat_storage.add_feedback(recent_msg_id, is_positive=True)

        # Analyze with 30-day window
        analyzer = FeedbackAnalyzer(temp_chat_storage)
        stats = analyzer.get_satisfaction_rate(days=30)

        # Should only count recent feedback
        assert stats["total_feedback"] == 1


class TestFeedbackMigration:
    """Test feedback column migration."""

    def test_migration_adds_columns_on_init(self):
        """Test that columns are automatically added on ChatStorage init."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        # Create storage (should auto-migrate)
        storage = ChatStorage(db_path=db_path)

        # Check columns exist
        with storage.SessionLocal() as session:
            from sqlalchemy import text

            result = session.execute(text("PRAGMA table_info(conversations)"))
            columns = [row[1] for row in result]

            assert "feedback_rating" in columns
            assert "feedback_comment" in columns
            assert "feedback_timestamp" in columns

        storage.close()
        Path(db_path).unlink(missing_ok=True)

    def test_migration_idempotent(self):
        """Test that migration can run multiple times safely."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        # Create storage twice (should not error)
        storage1 = ChatStorage(db_path=db_path)
        storage1.close()

        storage2 = ChatStorage(db_path=db_path)
        storage2.close()

        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
