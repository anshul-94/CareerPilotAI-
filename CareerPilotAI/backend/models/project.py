"""
CareerPilot AI — Project Model
CRUD operations for the projects table.
"""

import json
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


class ProjectModel:
    """Data access layer for generated project operations."""

    @staticmethod
    def create(user_id: int, domain: str, skills: list,
               experience_level: str = "beginner", project_data: dict = None,
               title: str = "", description: str = "") -> int:
        """Create a new project record."""
        return execute_insert(
            """INSERT INTO projects 
               (user_id, domain, skills, experience_level, project_data, title, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, domain, json.dumps(skills), experience_level,
             json.dumps(project_data or {}), title, description)
        )

    @staticmethod
    def get_by_id(project_id: int) -> Optional[dict]:
        """Get a project by its ID."""
        return execute_one("SELECT * FROM projects WHERE id = ?", (project_id,))

    @staticmethod
    def get_by_user(user_id: int, limit: int = 20) -> list[dict]:
        """Get all projects for a user."""
        return execute_query(
            "SELECT *, generated_at AS created_at FROM projects WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?",
            (user_id, limit)
        )

    @staticmethod
    def delete(project_id: int) -> int:
        """Delete a project."""
        return execute_update("DELETE FROM projects WHERE id = ?", (project_id,))


class ResumeAnalysisModel:
    """Data access layer for resume analysis records."""

    @staticmethod
    def create(resume_id: int, user_id: int, ats_score: int = 0,
               strong_skills: list = None, weak_skills: list = None,
               missing_keywords: list = None, grammar_issues: list = None,
               experience_analysis: str = "", project_analysis: str = "",
               summary: str = "", action_plan: list = None,
               full_analysis: dict = None) -> int:
        """Create a new resume analysis record."""
        return execute_insert(
            """INSERT INTO resume_analysis 
               (resume_id, user_id, ats_score, strong_skills, weak_skills,
                missing_keywords, grammar_issues, experience_analysis,
                project_analysis, summary, action_plan, full_analysis)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (resume_id, user_id, ats_score,
             json.dumps(strong_skills or []), json.dumps(weak_skills or []),
             json.dumps(missing_keywords or []), json.dumps(grammar_issues or []),
             experience_analysis, project_analysis, summary,
             json.dumps(action_plan or []), json.dumps(full_analysis or {}))
        )

    @staticmethod
    def get_by_resume(resume_id: int) -> Optional[dict]:
        """Get the latest analysis for a resume."""
        return execute_one(
            """SELECT *, analyzed_at AS created_at FROM resume_analysis WHERE resume_id = ?
               ORDER BY analyzed_at DESC LIMIT 1""",
            (resume_id,)
        )

    @staticmethod
    def get_by_user(user_id: int) -> list[dict]:
        """Get all resume analyses for a user."""
        return execute_query(
            """SELECT ra.*, r.original_name, ra.analyzed_at AS created_at
               FROM resume_analysis ra
               JOIN resumes r ON ra.resume_id = r.id
               WHERE ra.user_id = ?
               ORDER BY ra.analyzed_at DESC""",
            (user_id,)
        )

    @staticmethod
    def get_latest(user_id: int) -> Optional[dict]:
        """Get the latest resume analysis for a user."""
        return execute_one(
            """SELECT *, analyzed_at AS created_at FROM resume_analysis WHERE user_id = ?
               ORDER BY analyzed_at DESC LIMIT 1""",
            (user_id,)
        )


class CodeReviewModel:
    """Data access layer for code review records."""

    @staticmethod
    def create(user_id: int, language: str, code_input: str,
               review_data: dict = None) -> int:
        """Create a new code review record."""
        return execute_insert(
            """INSERT INTO code_reviews (user_id, language, code_input, review_data)
               VALUES (?, ?, ?, ?)""",
            (user_id, language, code_input, json.dumps(review_data or {}))
        )

    @staticmethod
    def get_by_user(user_id: int, limit: int = 20) -> list[dict]:
        """Get code reviews for a user."""
        return execute_query(
            "SELECT *, reviewed_at AS created_at FROM code_reviews WHERE user_id = ? ORDER BY reviewed_at DESC LIMIT ?",
            (user_id, limit)
        )


class SQLQueryModel:
    """Data access layer for SQL query analysis records."""

    @staticmethod
    def create(user_id: int, query_input: str, analysis_data: dict = None) -> int:
        """Create a new SQL query analysis record."""
        return execute_insert(
            """INSERT INTO sql_queries (user_id, query_input, analysis_data)
               VALUES (?, ?, ?)""",
            (user_id, query_input, json.dumps(analysis_data or {}))
        )

    @staticmethod
    def get_by_user(user_id: int, limit: int = 20) -> list[dict]:
        """Get SQL query analyses for a user."""
        return execute_query(
            "SELECT *, analyzed_at AS created_at FROM sql_queries WHERE user_id = ? ORDER BY analyzed_at DESC LIMIT ?",
            (user_id, limit)
        )


class SettingsModel:
    """Data access layer for user settings."""

    @staticmethod
    def get_by_user(user_id: int) -> Optional[dict]:
        """Get settings for a user."""
        return execute_one("SELECT * FROM settings WHERE user_id = ?", (user_id,))

    @staticmethod
    def create_or_update(user_id: int, **kwargs) -> int:
        """Create or update user settings."""
        existing = SettingsModel.get_by_user(user_id)
        if existing:
            allowed_fields = [
                'theme', 'notifications', 'email_alerts', 'preferred_role',
                'preferred_location', 'expected_salary', 'job_type_preference',
                'experience_level'
            ]
            fields = []
            values = []
            for key, value in kwargs.items():
                if key in allowed_fields:
                    fields.append(f"{key} = ?")
                    values.append(value)
            if not fields:
                return 0
            values.append(user_id)
            query = f"UPDATE settings SET {', '.join(fields)} WHERE user_id = ?"
            return execute_update(query, tuple(values))
        else:
            return execute_insert(
                """INSERT INTO settings (user_id, theme, notifications, preferred_role,
                   preferred_location, expected_salary, experience_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, kwargs.get('theme', 'dark'),
                 kwargs.get('notifications', 1),
                 kwargs.get('preferred_role', ''),
                 kwargs.get('preferred_location', ''),
                 kwargs.get('expected_salary', 0),
                 kwargs.get('experience_level', 'fresher'))
            )
