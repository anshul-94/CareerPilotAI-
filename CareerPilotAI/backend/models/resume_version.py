"""
CareerPilot AI — Resume Version Model
Stores AI-generated resume versions over time. Never overwrites previous versions.
"""

import json
from typing import Optional, List
from backend.database.db import execute_query, execute_one, execute_insert


RESUME_VERSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS resume_versions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    role_target       TEXT NOT NULL,
    version_type      TEXT DEFAULT 'manual_trigger', -- or 'daily_optimization'
    
    -- JSON blobs
    content           TEXT DEFAULT '{}',
    scores            TEXT DEFAULT '{}',
    suggestions       TEXT DEFAULT '[]',
    template          TEXT DEFAULT 'modern',
    
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resume_versions_user_id ON resume_versions(user_id);
"""


def migrate_resume_versions_table() -> None:
    """Run schema migration to add resume_versions table."""
    from backend.database.db import get_db_path
    import sqlite3
    path = get_db_path()
    with sqlite3.connect(path) as conn:
        conn.executescript(RESUME_VERSIONS_SCHEMA)
        conn.commit()
    print("[✓] resume_versions table created/verified.")


class ResumeVersionModel:
    """Data access layer for AI-optimized resume versions."""
    
    @staticmethod
    def create(user_id: int, role_target: str, version_type: str,
               content: dict, scores: dict, suggestions: list,
               template: str = 'modern') -> int:
        """Create a new AI-generated resume version."""
        return execute_insert(
            """INSERT INTO resume_versions 
               (user_id, role_target, version_type, content, scores, suggestions, template)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, role_target, version_type,
             json.dumps(content or {}), json.dumps(scores or {}),
             json.dumps(suggestions or []), template)
        )
        
    @staticmethod
    def get_by_user(user_id: int, limit: int = 15) -> List[dict]:
        """Get all resume versions for a user, ordered by newest first."""
        rows = execute_query(
            "SELECT * FROM resume_versions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        for row in rows:
            ResumeVersionModel._parse_json_fields(row)
        return rows
        
    @staticmethod
    def get_latest_for_role(user_id: int, role_target: str) -> Optional[dict]:
        """Get the most recent resume version for a specific role."""
        row = execute_one(
            "SELECT * FROM resume_versions WHERE user_id = ? AND role_target = ? ORDER BY created_at DESC LIMIT 1",
            (user_id, role_target)
        )
        if row:
            ResumeVersionModel._parse_json_fields(row)
        return row
        
    @staticmethod
    def get_latest(user_id: int) -> Optional[dict]:
        """Get the absolute latest resume version across all roles."""
        row = execute_one(
            "SELECT * FROM resume_versions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        if row:
            ResumeVersionModel._parse_json_fields(row)
        return row
        
    @staticmethod
    def _parse_json_fields(row: dict) -> None:
        """Helper to parse JSON fields in a row."""
        for field in ['content', 'scores', 'suggestions']:
            val = row.get(field, '{}' if field != 'suggestions' else '[]')
            if isinstance(val, str):
                try:
                    row[field] = json.loads(val)
                except Exception:
                    row[field] = {} if field != 'suggestions' else []
