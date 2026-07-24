"""
CareerPilot AI — Interview History Model
CRUD operations for the interview_history table.
"""

import json
import uuid
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


class InterviewModel:
    """Data access layer for interview history operations."""

    @staticmethod
    def create(user_id: int, role: str, difficulty: str = "medium",
               experience_years: int = 0, interview_type: str = "technical") -> int:
        """Create a new interview session."""
        session_id = str(uuid.uuid4())
        return execute_insert(
            """INSERT INTO interview_history 
               (user_id, session_id, role, difficulty, experience_years, interview_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, session_id, role, difficulty, experience_years, interview_type)
        )

    @staticmethod
    def get_by_id(interview_id: int) -> Optional[dict]:
        """Get an interview session by its ID."""
        return execute_one("SELECT *, conducted_at AS created_at FROM interview_history WHERE id = ?", (interview_id,))

    @staticmethod
    def get_by_session(session_id: str) -> Optional[dict]:
        """Get an interview session by session ID."""
        return execute_one(
            "SELECT *, conducted_at AS created_at FROM interview_history WHERE session_id = ?",
            (session_id,)
        )

    @staticmethod
    def get_by_user(user_id: int, limit: int = 20) -> list[dict]:
        """Get interview history for a user."""
        return execute_query(
            """SELECT *, conducted_at AS created_at FROM interview_history WHERE user_id = ?
               ORDER BY conducted_at DESC LIMIT ?""",
            (user_id, limit)
        )

    @staticmethod
    def update_results(interview_id: int, questions: list, answers: list,
                       evaluations: list, communication_score: int,
                       technical_score: int, confidence_score: int,
                       overall_score: int, feedback: str = "") -> int:
        """Update interview results after evaluation."""
        return execute_update(
            """UPDATE interview_history SET 
               questions = ?, answers = ?, evaluations = ?,
               communication_score = ?, technical_score = ?,
               confidence_score = ?, overall_score = ?, feedback = ?
               WHERE id = ?""",
            (json.dumps(questions), json.dumps(answers), json.dumps(evaluations),
             communication_score, technical_score, confidence_score,
             overall_score, feedback, interview_id)
        )

    @staticmethod
    def get_stats(user_id: int) -> dict:
        """Get interview statistics for a user."""
        result = execute_one(
            """SELECT 
                COUNT(*) as total_interviews,
                AVG(overall_score) as avg_score,
                MAX(overall_score) as best_score,
                AVG(communication_score) as avg_communication,
                AVG(technical_score) as avg_technical,
                AVG(confidence_score) as avg_confidence
               FROM interview_history WHERE user_id = ? AND overall_score > 0""",
            (user_id,)
        )
        return result if result else {}

    @staticmethod
    def get_recent_scores(user_id: int, limit: int = 7) -> list[dict]:
        """Get recent interview scores for charting."""
        return execute_query(
            """SELECT overall_score, communication_score, technical_score,
                      confidence_score, conducted_at, role, conducted_at AS created_at
               FROM interview_history WHERE user_id = ? AND overall_score > 0
               ORDER BY conducted_at DESC LIMIT ?""",
            (user_id, limit)
        )

    @staticmethod
    def delete(interview_id: int) -> int:
        """Delete an interview session."""
        return execute_update("DELETE FROM interview_history WHERE id = ?", (interview_id,))
