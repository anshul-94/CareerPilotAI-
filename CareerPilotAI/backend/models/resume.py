"""
CareerPilot AI — Resume Model
CRUD operations for the resumes table.
"""

import json
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


class ResumeModel:
    """Data access layer for resume operations."""

    @staticmethod
    def create(user_id: int, filename: str, original_name: str,
               raw_text: str = "", file_size: int = 0) -> int:
        """Create a new resume record and return its ID."""
        return execute_insert(
            """INSERT INTO resumes (user_id, filename, original_name, raw_text, file_size)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, filename, original_name, raw_text, file_size)
        )

    @staticmethod
    def get_by_id(resume_id: int) -> Optional[dict]:
        """Get a resume by its ID."""
        return execute_one("SELECT *, uploaded_at AS created_at FROM resumes WHERE id = ?", (resume_id,))

    @staticmethod
    def get_by_user(user_id: int) -> list[dict]:
        """Get all resumes for a user."""
        return execute_query(
            "SELECT *, uploaded_at AS created_at FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC",
            (user_id,)
        )

    @staticmethod
    def get_primary(user_id: int) -> Optional[dict]:
        """Get the primary resume for a user."""
        resume = execute_one(
            "SELECT *, uploaded_at AS created_at FROM resumes WHERE user_id = ? AND is_primary = 1",
            (user_id,)
        )
        if not resume:
            # Fall back to the most recent resume
            resume = execute_one(
                "SELECT *, uploaded_at AS created_at FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
                (user_id,)
            )
        return resume

    @staticmethod
    def set_primary(resume_id: int, user_id: int) -> None:
        """Set a resume as the primary resume for a user."""
        # Unset all primary flags for the user
        execute_update(
            "UPDATE resumes SET is_primary = 0 WHERE user_id = ?",
            (user_id,)
        )
        # Set the specified resume as primary
        execute_update(
            "UPDATE resumes SET is_primary = 1 WHERE id = ? AND user_id = ?",
            (resume_id, user_id)
        )

    @staticmethod
    def update_parsed_data(resume_id: int, parsed_data: dict) -> int:
        """Update the parsed data for a resume."""
        return execute_update(
            "UPDATE resumes SET parsed_data = ? WHERE id = ?",
            (json.dumps(parsed_data), resume_id)
        )

    @staticmethod
    def update_raw_text(resume_id: int, raw_text: str) -> int:
        """Update the raw text for a resume."""
        return execute_update(
            "UPDATE resumes SET raw_text = ? WHERE id = ?",
            (raw_text, resume_id)
        )

    @staticmethod
    def delete(resume_id: int) -> int:
        """Delete a resume by its ID."""
        return execute_update("DELETE FROM resumes WHERE id = ?", (resume_id,))

    @staticmethod
    def count_by_user(user_id: int) -> int:
        """Get total number of resumes for a user."""
        result = execute_one(
            "SELECT COUNT(*) as count FROM resumes WHERE user_id = ?",
            (user_id,)
        )
        return result["count"] if result else 0

    @staticmethod
    def get_all(limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all resumes with user info (admin)."""
        return execute_query(
            """SELECT r.*, u.username, u.full_name, u.email, r.uploaded_at AS created_at
               FROM resumes r 
               JOIN users u ON r.user_id = u.id
               ORDER BY r.uploaded_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        )
