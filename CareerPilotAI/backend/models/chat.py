"""
CareerPilot AI — Chat History Model
CRUD operations for the chat_history table.
"""

import uuid
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


class ChatModel:
    """Data access layer for chat history operations."""

    @staticmethod
    def create(user_id: int, session_id: str, role: str,
               message: str, module: str = "career_coach") -> int:
        """Create a new chat message."""
        return execute_insert(
            """INSERT INTO chat_history (user_id, session_id, role, message, module)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, session_id, role, message, module)
        )

    @staticmethod
    def get_session(session_id: str) -> list[dict]:
        """Get all messages in a chat session, ordered chronologically."""
        return execute_query(
            "SELECT * FROM chat_history WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )

    @staticmethod
    def get_user_sessions(user_id: int, module: str = None) -> list[dict]:
        """Get unique chat sessions for a user, optionally filtered by module."""
        if module:
            return execute_query(
                """SELECT session_id, module, MIN(created_at) as started_at, 
                   MAX(created_at) as last_message, COUNT(*) as message_count
                   FROM chat_history WHERE user_id = ? AND module = ?
                   GROUP BY session_id ORDER BY last_message DESC""",
                (user_id, module)
            )
        return execute_query(
            """SELECT session_id, module, MIN(created_at) as started_at,
               MAX(created_at) as last_message, COUNT(*) as message_count
               FROM chat_history WHERE user_id = ?
               GROUP BY session_id ORDER BY last_message DESC""",
            (user_id,)
        )

    @staticmethod
    def get_recent(user_id: int, limit: int = 10) -> list[dict]:
        """Get the most recent chat messages for a user."""
        return execute_query(
            """SELECT * FROM chat_history WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        )

    @staticmethod
    def delete_session(session_id: str) -> int:
        """Delete all messages in a chat session."""
        return execute_update(
            "DELETE FROM chat_history WHERE session_id = ?",
            (session_id,)
        )

    @staticmethod
    def count_by_user(user_id: int) -> int:
        """Get total number of chat messages for a user."""
        result = execute_one(
            "SELECT COUNT(*) as count FROM chat_history WHERE user_id = ?",
            (user_id,)
        )
        return result["count"] if result else 0

    @staticmethod
    def generate_session_id() -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())

    @staticmethod
    def get_all_chats(limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all chat messages with user info (admin)."""
        return execute_query(
            """SELECT ch.*, u.username, u.full_name
               FROM chat_history ch
               JOIN users u ON ch.user_id = u.id
               ORDER BY ch.created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        )
