"""
CareerPilot AI — Resume Storage Metadata Model
Tracks decoupled storage backend references (local vs. Supabase Storage) for uploaded resumes.
"""

from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


RESUME_STORAGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS resume_storage_metadata (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id         INTEGER NOT NULL UNIQUE,
    backend           TEXT NOT NULL DEFAULT 'local', -- 'local' or 'supabase'
    bucket_name       TEXT DEFAULT '',
    object_key        TEXT NOT NULL,
    file_size         INTEGER DEFAULT 0,
    content_type      TEXT DEFAULT 'application/pdf',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resume_storage_resume_id ON resume_storage_metadata(resume_id);
"""


def migrate_resume_storage_table() -> None:
    """Run schema migration to add resume_storage_metadata table if it does not exist."""
    from backend.database.db import get_db, is_postgres
    if is_postgres():
        schema = RESUME_STORAGE_SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        with get_db() as db:
            for stmt in schema.split(";"):
                stmt = stmt.strip()
                if stmt:
                    db.execute(stmt)
    else:
        from backend.database.db import get_db_path
        import sqlite3
        path = get_db_path()
        with sqlite3.connect(path) as conn:
            conn.executescript(RESUME_STORAGE_SCHEMA)
            conn.commit()


class ResumeStorageModel:
    """Data access layer for resume storage metadata."""

    @staticmethod
    def create(resume_id: int, backend: str, bucket_name: str,
               object_key: str, file_size: int = 0,
               content_type: str = "application/pdf") -> int:
        """Create a storage metadata entry for a resume."""
        return execute_insert(
            """INSERT INTO resume_storage_metadata 
               (resume_id, backend, bucket_name, object_key, file_size, content_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (resume_id, backend, bucket_name, object_key, file_size, content_type)
        )

    @staticmethod
    def get_by_resume_id(resume_id: int) -> Optional[dict]:
        """Retrieve storage metadata for a given resume_id."""
        return execute_one(
            "SELECT * FROM resume_storage_metadata WHERE resume_id = ?",
            (resume_id,)
        )

    @staticmethod
    def delete_by_resume_id(resume_id: int) -> int:
        """Delete storage metadata entry for a resume."""
        return execute_update(
            "DELETE FROM resume_storage_metadata WHERE resume_id = ?",
            (resume_id,)
        )

    @staticmethod
    def update(resume_id: int, backend: str, bucket_name: str,
               object_key: str, file_size: int = 0) -> int:
        """Update storage metadata when migrating an existing resume."""
        return execute_update(
            """UPDATE resume_storage_metadata
               SET backend = ?, bucket_name = ?, object_key = ?, file_size = ?
               WHERE resume_id = ?""",
            (backend, bucket_name, object_key, file_size, resume_id)
        )
