"""
CareerPilot AI — User Model
CRUD operations for the users table.
"""

import json
from datetime import datetime
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


class UserModel:
    """Data access layer for user operations."""

    @staticmethod
    def create(username: str, email: str, password_hash: str, full_name: str = "") -> int:
        """Create a new user and return the user ID."""
        return execute_insert(
            """INSERT INTO users (username, email, password_hash, full_name)
               VALUES (?, ?, ?, ?)""",
            (username, email, password_hash, full_name)
        )

    @staticmethod
    def get_by_id(user_id: int) -> Optional[dict]:
        """Get a user by their ID."""
        return execute_one("SELECT * FROM users WHERE id = ?", (user_id,))

    @staticmethod
    def get_by_username(username: str) -> Optional[dict]:
        """Get a user by their username."""
        return execute_one("SELECT * FROM users WHERE username = ?", (username,))

    @staticmethod
    def get_by_email(email: str) -> Optional[dict]:
        """Get a user by their email address."""
        return execute_one("SELECT * FROM users WHERE email = ?", (email,))

    @staticmethod
    def get_all(limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all users with pagination."""
        return execute_query(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )

    @staticmethod
    def update_profile(user_id: int, **kwargs) -> int:
        """Update user profile fields."""
        allowed_fields = [
            'full_name', 'bio', 'phone', 'location',
            'linkedin_url', 'github_url', 'portfolio_url', 'avatar_url'
        ]
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return 0
        
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(user_id)
        
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        return execute_update(query, tuple(values))

    @staticmethod
    def update_last_login(user_id: int) -> int:
        """Update the last login timestamp."""
        return execute_update(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user_id)
        )

    @staticmethod
    def update_role(user_id: int, role: str) -> int:
        """Update user role (admin/user)."""
        return execute_update(
            "UPDATE users SET role = ?, updated_at = ? WHERE id = ?",
            (role, datetime.now().isoformat(), user_id)
        )

    @staticmethod
    def delete(user_id: int) -> int:
        """Delete a user by their ID."""
        return execute_update("DELETE FROM users WHERE id = ?", (user_id,))

    @staticmethod
    def count() -> int:
        """Get total number of users."""
        result = execute_one("SELECT COUNT(*) as count FROM users")
        return result["count"] if result else 0

    @staticmethod
    def search(query: str) -> list[dict]:
        """Search users by username, email, or full name."""
        search_term = f"%{query}%"
        return execute_query(
            """SELECT * FROM users 
               WHERE username LIKE ? OR email LIKE ? OR full_name LIKE ?
               ORDER BY created_at DESC""",
            (search_term, search_term, search_term)
        )
