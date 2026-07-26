"""
CareerPilot AI — Chat History Model
CRUD operations for chat_sessions and chat_history tables.
"""

import uuid
from datetime import datetime
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


def migrate_chat_sessions_table():
    """Create chat_sessions table if it doesn't exist."""
    from backend.database.db import execute_update
    execute_update("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'New Conversation',
            is_pinned INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)


class ChatSessionModel:
    """Data access layer for chat sessions."""
    
    @staticmethod
    def create(session_id: str, user_id: int, title: str = "New Conversation") -> str:
        execute_insert(
            """INSERT INTO chat_sessions (session_id, user_id, title)
               VALUES (?, ?, ?)""",
            (session_id, user_id, title)
        )
        return session_id

    @staticmethod
    def get(session_id: str) -> Optional[dict]:
        return execute_one("SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,))

    @staticmethod
    def update_title(session_id: str, title: str) -> int:
        return execute_update(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE session_id = ?",
            (title, datetime.now().isoformat(), session_id)
        )

    @staticmethod
    def toggle_pin(session_id: str, is_pinned: bool) -> int:
        return execute_update(
            "UPDATE chat_sessions SET is_pinned = ?, updated_at = ? WHERE session_id = ?",
            (1 if is_pinned else 0, datetime.now().isoformat(), session_id)
        )
        
    @staticmethod
    def toggle_archive(session_id: str, is_archived: bool) -> int:
        return execute_update(
            "UPDATE chat_sessions SET is_archived = ?, updated_at = ? WHERE session_id = ?",
            (1 if is_archived else 0, datetime.now().isoformat(), session_id)
        )

    @staticmethod
    def delete(session_id: str) -> int:
        # Also deletes history due to no cascade in old sqlite sometimes, so we'll delete both
        ChatModel.delete_session(session_id)
        return execute_update("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))


class ChatModel:
    """Data access layer for chat history operations."""

    @staticmethod
    def create(user_id: int, session_id: str, role: str,
               message: str, module: str = "career_coach") -> int:
        """Create a new chat message and ensure session exists."""
        # Ensure session exists
        session_exists = ChatSessionModel.get(session_id)
        if not session_exists:
            ChatSessionModel.create(session_id, user_id, title="New Conversation")
        else:
            execute_update("UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?", (datetime.now().isoformat(), session_id))

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
        """Get chat sessions enriched with session metadata."""
        # We join chat_sessions and chat_history
        return execute_query(
            """
            SELECT 
                cs.session_id,
                cs.title,
                cs.is_pinned,
                cs.is_archived,
                cs.created_at as session_created_at,
                cs.updated_at,
                MIN(ch.created_at) as started_at,
                MAX(ch.created_at) as last_message,
                COUNT(ch.id) as message_count
            FROM chat_sessions cs
            LEFT JOIN chat_history ch ON cs.session_id = ch.session_id
            WHERE cs.user_id = ? AND cs.is_archived = 0
            GROUP BY cs.session_id
            ORDER BY cs.is_pinned DESC, cs.updated_at DESC
            """,
            (user_id,)
        )
        
    @staticmethod
    def get_archived_sessions(user_id: int) -> list[dict]:
        return execute_query(
            """
            SELECT 
                cs.session_id,
                cs.title,
                cs.is_pinned,
                cs.is_archived,
                cs.updated_at,
                COUNT(ch.id) as message_count
            FROM chat_sessions cs
            LEFT JOIN chat_history ch ON cs.session_id = ch.session_id
            WHERE cs.user_id = ? AND cs.is_archived = 1
            GROUP BY cs.session_id
            ORDER BY cs.updated_at DESC
            """,
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
