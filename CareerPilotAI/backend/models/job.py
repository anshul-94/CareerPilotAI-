"""
CareerPilot AI — Job History Model
CRUD operations for the job_history table.
"""

import json
from datetime import datetime
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


class JobModel:
    """Data access layer for job history operations."""

    @staticmethod
    def create(user_id: int, title: str, company: str, location: str = "",
               salary: str = "", apply_link: str = "", source: str = "",
               match_score: int = 0, match_details: dict = None,
               job_type: str = "Full-time", experience_level: str = "",
               description: str = "") -> int:
        """Create a new job record."""
        return execute_insert(
            """INSERT INTO job_history 
               (user_id, title, company, location, salary, apply_link, source,
                match_score, match_details, job_type, experience_level, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, company, location, salary, apply_link, source,
             match_score, json.dumps(match_details or {}), job_type,
             experience_level, description)
        )

    @staticmethod
    def get_by_id(job_id: int) -> Optional[dict]:
        """Get a job by its ID."""
        return execute_one("SELECT *, found_at AS created_at FROM job_history WHERE id = ?", (job_id,))

    @staticmethod
    def get_by_user(user_id: int, status: str = None, limit: int = 50) -> list[dict]:
        """Get jobs for a user, optionally filtered by status."""
        if status:
            return execute_query(
                """SELECT *, found_at AS created_at FROM job_history WHERE user_id = ? AND status = ?
                   ORDER BY match_score DESC, found_at DESC LIMIT ?""",
                (user_id, status, limit)
            )
        return execute_query(
            """SELECT *, found_at AS created_at FROM job_history WHERE user_id = ?
               ORDER BY found_at DESC LIMIT ?""",
            (user_id, limit)
        )

    @staticmethod
    def update_status(job_id: int, status: str) -> int:
        """Update the status of a job entry."""
        return execute_update(
            "UPDATE job_history SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), job_id)
        )

    @staticmethod
    def get_stats(user_id: int) -> dict:
        """Get job search statistics for a user."""
        result = execute_one(
            """SELECT 
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'saved' THEN 1 ELSE 0 END) as saved,
                SUM(CASE WHEN status = 'interviewing' THEN 1 ELSE 0 END) as interviewing,
                AVG(match_score) as avg_match_score
               FROM job_history WHERE user_id = ?""",
            (user_id,)
        )
        return result if result else {}

    @staticmethod
    def delete(job_id: int) -> int:
        """Delete a job entry."""
        return execute_update("DELETE FROM job_history WHERE id = ?", (job_id,))

    @staticmethod
    def bulk_create(user_id: int, jobs: list[dict]) -> int:
        """Bulk insert multiple job records."""
        count = 0
        for job in jobs:
            JobModel.create(
                user_id=user_id,
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                salary=job.get("salary", ""),
                apply_link=job.get("apply_link", ""),
                source=job.get("source", ""),
                match_score=job.get("match_score", 0),
                match_details=job.get("match_details"),
                job_type=job.get("job_type", "Full-time"),
                experience_level=job.get("experience_level", ""),
                description=job.get("description", "")
            )
            count += 1
        return count

    @staticmethod
    def get_all(limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all jobs with user info (admin)."""
        return execute_query(
            """SELECT jh.*, u.username, u.full_name, jh.found_at AS created_at
               FROM job_history jh
               JOIN users u ON jh.user_id = u.id
               ORDER BY jh.found_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        )
