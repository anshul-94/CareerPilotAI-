import os
import sqlite3
from backend.config import Config

from backend.database.schema import init_db
from backend.models.career_profile import migrate_career_profile_table
from backend.models.resume_version import migrate_resume_versions_table
from backend.models.job_notification import migrate_notification_tables
from backend.models.chat import migrate_chat_sessions_table
from backend.models.problem import migrate_problem_solving_tables

def initialize_database():
    """Run all database creation and migrations in one place."""
    
    # 1. Base Schema (users, resumes, projects, code_reviews, etc)
    db_path = Config.DATABASE_PATH
    if not os.path.exists(db_path):
        init_db(db_path)
    
    print("\nInitializing database...\n", flush=True)
    
    # 2. Dynamic Migrations (Tables that evolved after base schema)
    migrate_career_profile_table()
    print("[✓] career_profiles", flush=True)
    
    migrate_resume_versions_table()
    print("\n[✓] resume_versions", flush=True)
    
    migrate_notification_tables()
    print("\n[✓] notification_agent", flush=True)
    
    migrate_chat_sessions_table()
    print("\n[✓] chat_sessions", flush=True)
    
    migrate_problem_solving_tables()
    print("\n[✓] problem_solving", flush=True)
    
    print("\nDatabase Ready.", flush=True)
    print("\nServer Ready.", flush=True)
