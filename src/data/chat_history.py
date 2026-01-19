"""Persistent chat history backed by SQLite."""

import logging
from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.data.chat_storage import ChatStorage

logger = logging.getLogger(__name__)

class SQLiteChatMessageHistory(BaseChatMessageHistory):
    """Chat history implementation that stores messages in SQLite."""

    def __init__(self, session_id: str, storage: ChatStorage | None = None) -> None:
        """Initialize with session ID.

        Args:
            session_id: Unique identifier for the conversation
            storage: Optional existing storage instance
        """
        self.session_id = session_id
        # We create a new storage instance if not provided.
        # Ideally, this should be a singleton or dependency injected.
        self.storage = storage or ChatStorage()
        print(f"DEBUG: Initialized history for {session_id} with storage {self.storage}")

    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve messages from database."""
        records = self.storage.get_chat_history(self.session_id)
        messages = []
        for r in records:
            if r["role"] == "user":
                messages.append(HumanMessage(content=r["content"]))
            elif r["role"] == "assistant":
                messages.append(AIMessage(content=r["content"]))
        return messages

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the database."""
        print(f"DEBUG: Adding message to {self.session_id}: {message}")
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            # Handle SystemMessage or others if needed, typically we skip or map to 'system'
            role = "system"
        
        self.storage.add_chat_message(self.session_id, role, str(message.content))

    def clear(self) -> None:
        """Clear session history (not implemented in storage yet, but optional)."""
        pass
