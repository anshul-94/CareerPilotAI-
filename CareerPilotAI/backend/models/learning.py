"""
CareerPilot AI — Learning Roadmap Model
CRUD operations for the learning_roadmaps table.
"""

import json
from datetime import datetime
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


class LearningModel:
    """Data access layer for learning roadmap operations."""

    @staticmethod
    def create(user_id: int, target_role: str, current_skills: list,
               roadmap_data: dict = None) -> int:
        """Create a new learning roadmap."""
        return execute_insert(
            """INSERT INTO learning_roadmaps 
               (user_id, target_role, current_skills, roadmap_data)
               VALUES (?, ?, ?, ?)""",
            (user_id, target_role, json.dumps(current_skills),
             json.dumps(roadmap_data or {}))
        )

    @staticmethod
    def get_by_id(roadmap_id: int) -> Optional[dict]:
        """Get a roadmap by its ID."""
        return execute_one("SELECT * FROM learning_roadmaps WHERE id = ?", (roadmap_id,))

    @staticmethod
    def get_by_user(user_id: int) -> list[dict]:
        """Get all roadmaps for a user."""
        return execute_query(
            "SELECT * FROM learning_roadmaps WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )

    @staticmethod
    def get_active(user_id: int) -> Optional[dict]:
        """Get the currently active roadmap for a user."""
        return execute_one(
            """SELECT * FROM learning_roadmaps 
               WHERE user_id = ? AND status = 'active'
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,)
        )

    @staticmethod
    def update_roadmap(roadmap_id: int, roadmap_data: dict,
                       daily_plan: dict = None, weekly_plan: dict = None,
                       resources: dict = None) -> int:
        """Update roadmap data."""
        return execute_update(
            """UPDATE learning_roadmaps SET 
               roadmap_data = ?, daily_plan = ?, weekly_plan = ?,
               resources = ?, updated_at = ?
               WHERE id = ?""",
            (json.dumps(roadmap_data), json.dumps(daily_plan or {}),
             json.dumps(weekly_plan or {}), json.dumps(resources or {}),
             datetime.now().isoformat(), roadmap_id)
        )

    @staticmethod
    def update_progress(roadmap_id: int, progress_percent: int) -> int:
        """Update the progress percentage of a roadmap."""
        return execute_update(
            "UPDATE learning_roadmaps SET progress_percent = ?, updated_at = ? WHERE id = ?",
            (min(100, max(0, progress_percent)), datetime.now().isoformat(), roadmap_id)
        )

    @staticmethod
    def update_status(roadmap_id: int, status: str) -> int:
        """Update the status of a roadmap."""
        return execute_update(
            "UPDATE learning_roadmaps SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), roadmap_id)
        )

    @staticmethod
    def delete(roadmap_id: int) -> int:
        """Delete a learning roadmap."""
        return execute_update("DELETE FROM learning_roadmaps WHERE id = ?", (roadmap_id,))
