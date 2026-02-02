"""
FILE: test_chat_history.py
STATUS: Active
RESPONSIBILITY: Unit tests for SQLiteChatMessageHistory.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.data.chat_history import SQLiteChatMessageHistory


class TestSQLiteChatMessageHistory:
    """Test SQLiteChatMessageHistory class."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage."""
        storage = MagicMock()
        storage.get_chat_history.return_value = []
        return storage

    def test_init_with_storage(self, mock_storage):
        """Test initialization with provided storage."""
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)

        assert history.session_id == "session-1"
        assert history.storage == mock_storage

    def test_init_creates_storage_if_not_provided(self):
        """Test that storage is created if not provided."""
        with patch('src.data.chat_history.ChatStorage') as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            history = SQLiteChatMessageHistory("session-1")

            assert history.storage == mock_instance
            mock_class.assert_called_once()

    def test_messages_empty(self, mock_storage):
        """Test messages property with empty history."""
        mock_storage.get_chat_history.return_value = []
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)

        messages = history.messages

        assert messages == []
        mock_storage.get_chat_history.assert_called_once_with("session-1")

    def test_messages_with_user_message(self, mock_storage):
        """Test messages property with user message."""
        mock_storage.get_chat_history.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)

        messages = history.messages

        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Hello"

    def test_messages_with_assistant_message(self, mock_storage):
        """Test messages property with assistant message."""
        mock_storage.get_chat_history.return_value = [
            {"role": "assistant", "content": "Hi there!"}
        ]
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)

        messages = history.messages

        assert len(messages) == 1
        assert isinstance(messages[0], AIMessage)
        assert messages[0].content == "Hi there!"

    def test_messages_with_conversation(self, mock_storage):
        """Test messages property with full conversation."""
        mock_storage.get_chat_history.return_value = [
            {"role": "user", "content": "What events are in Paris?"},
            {"role": "assistant", "content": "There are jazz concerts..."},
            {"role": "user", "content": "Tell me more"},
            {"role": "assistant", "content": "The main event is..."},
        ]
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)

        messages = history.messages

        assert len(messages) == 4
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert isinstance(messages[2], HumanMessage)
        assert isinstance(messages[3], AIMessage)

    def test_add_human_message(self, mock_storage):
        """Test adding a human message."""
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)
        message = HumanMessage(content="Hello!")

        history.add_message(message)

        mock_storage.add_chat_message.assert_called_once_with(
            "session-1", "user", "Hello!"
        )

    def test_add_ai_message(self, mock_storage):
        """Test adding an AI message."""
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)
        message = AIMessage(content="Hi there!")

        history.add_message(message)

        mock_storage.add_chat_message.assert_called_once_with(
            "session-1", "assistant", "Hi there!"
        )

    def test_add_system_message(self, mock_storage):
        """Test adding a system message."""
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)
        message = SystemMessage(content="You are a helpful assistant.")

        history.add_message(message)

        mock_storage.add_chat_message.assert_called_once_with(
            "session-1", "system", "You are a helpful assistant."
        )

    def test_clear_does_nothing(self, mock_storage):
        """Test that clear method exists but does nothing."""
        history = SQLiteChatMessageHistory("session-1", storage=mock_storage)

        # Should not raise
        history.clear()

        # Storage should not be called for clear
        assert not mock_storage.clear.called

    def test_multiple_sessions_independent(self, mock_storage):
        """Test that different sessions have independent histories."""
        history1 = SQLiteChatMessageHistory("session-1", storage=mock_storage)
        history2 = SQLiteChatMessageHistory("session-2", storage=mock_storage)

        # Access messages for each session
        _ = history1.messages
        _ = history2.messages

        # Verify get_chat_history called with correct session IDs
        calls = mock_storage.get_chat_history.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "session-1"
        assert calls[1][0][0] == "session-2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
