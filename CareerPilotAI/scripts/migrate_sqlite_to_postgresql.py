#!/usr/bin/env python3
"""
CareerPilot AI — Safe SQLite to PostgreSQL Data Migration Utility
Migrates all 27 tables, rows, relationships, JSON content, timestamps,
and password hashes while preserving original SQLite data untouched.
"""

import os
import sys
import argparse
import sqlite3
import time
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urlparse

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv()

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("[ERROR] psycopg2-binary is required. Run: pip install psycopg2-binary")
    sys.exit(1)


def mask_url_credentials(url: str) -> str:
    """Mask password and user in database URL for safe terminal logging."""
    if not url:
        return "<unset>"
    try:
        parsed = urlparse(url)
        netloc = parsed.hostname or "unknown"
        if parsed.port:
            netloc += f":{parsed.port}"
        if parsed.username:
            netloc = f"{parsed.username}:***@" + netloc
        return f"{parsed.scheme}://{netloc}{parsed.path}"
    except Exception:
        return "<redacted-database-url>"


# Complete verified PostgreSQL DDL for all 27 tables in CareerPilot AI
POSTGRESQL_SCHEMA_DDL = """
-- Level 0: Root Tables
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '/static/images/default-avatar.png',
    bio TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    location TEXT DEFAULT '',
    linkedin_url TEXT DEFAULT '',
    github_url TEXT DEFAULT '',
    portfolio_url TEXT DEFAULT '',
    role TEXT DEFAULT 'user' CHECK(role IN ('user', 'admin')),
    is_active INTEGER DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER,
    admin_username TEXT,
    action TEXT NOT NULL,
    target TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS problems (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    topic TEXT NOT NULL,
    subtopics TEXT,
    companies TEXT,
    constraints TEXT,
    description TEXT NOT NULL,
    examples TEXT,
    hints TEXT,
    editorial TEXT,
    starter_code TEXT,
    tags TEXT,
    premium INTEGER DEFAULT 0,
    estimated_time INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Level 1: Tables dependent on Level 0
CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    raw_text TEXT DEFAULT '',
    parsed_data TEXT DEFAULT '{}',
    is_primary INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Conversation',
    is_pinned INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT DEFAULT '',
    salary TEXT DEFAULT '',
    job_type TEXT DEFAULT 'Full-time',
    experience_level TEXT DEFAULT '',
    description TEXT DEFAULT '',
    apply_link TEXT DEFAULT '',
    source TEXT DEFAULT '',
    match_score INTEGER DEFAULT 0,
    match_details TEXT DEFAULT '{}',
    status TEXT DEFAULT 'discovered' CHECK(status IN ('discovered', 'saved', 'applied', 'interviewing', 'rejected', 'offered')),
    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interview_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    difficulty TEXT DEFAULT 'medium' CHECK(difficulty IN ('easy', 'medium', 'hard', 'expert')),
    experience_years INTEGER DEFAULT 0,
    interview_type TEXT DEFAULT 'technical',
    questions TEXT DEFAULT '[]',
    answers TEXT DEFAULT '[]',
    evaluations TEXT DEFAULT '[]',
    communication_score INTEGER DEFAULT 0,
    technical_score INTEGER DEFAULT 0,
    confidence_score INTEGER DEFAULT 0,
    overall_score INTEGER DEFAULT 0,
    feedback TEXT DEFAULT '',
    conducted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_roadmaps (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_role TEXT NOT NULL,
    current_skills TEXT DEFAULT '[]',
    roadmap_data TEXT DEFAULT '{}',
    daily_plan TEXT DEFAULT '{}',
    weekly_plan TEXT DEFAULT '{}',
    resources TEXT DEFAULT '{}',
    progress_percent INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'paused', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    skills TEXT DEFAULT '[]',
    experience_level TEXT DEFAULT 'beginner',
    project_data TEXT DEFAULT '{}',
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    theme TEXT DEFAULT 'dark',
    notifications INTEGER DEFAULT 1,
    email_alerts INTEGER DEFAULT 1,
    preferred_role TEXT DEFAULT '',
    preferred_location TEXT DEFAULT '',
    expected_salary INTEGER DEFAULT 0,
    job_type_preference TEXT DEFAULT 'Full-time',
    experience_level TEXT DEFAULT 'fresher',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS code_reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language TEXT DEFAULT 'python',
    code_input TEXT NOT NULL,
    review_data TEXT DEFAULT '{}',
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sql_queries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_input TEXT NOT NULL,
    analysis_data TEXT DEFAULT '{}',
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS career_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    location TEXT DEFAULT '',
    linkedin_url TEXT DEFAULT '',
    github_url TEXT DEFAULT '',
    portfolio_url TEXT DEFAULT '',
    preferred_role TEXT DEFAULT '',
    career_goal TEXT DEFAULT '',
    expected_salary TEXT DEFAULT '',
    preferred_location TEXT DEFAULT '',
    skills TEXT DEFAULT '[]',
    top_skills TEXT DEFAULT '[]',
    soft_skills TEXT DEFAULT '[]',
    technologies TEXT DEFAULT '[]',
    certifications TEXT DEFAULT '[]',
    projects TEXT DEFAULT '[]',
    experience_summary TEXT DEFAULT '',
    education TEXT DEFAULT '',
    experience_years INTEGER DEFAULT 0,
    domain TEXT DEFAULT '',
    seniority_level TEXT DEFAULT 'fresher',
    ats_score INTEGER DEFAULT 0,
    profile_completeness INTEGER DEFAULT 0,
    ai_readiness INTEGER DEFAULT 0,
    resume_strength INTEGER DEFAULT 0,
    full_name_is_manual INTEGER DEFAULT 0,
    phone_is_manual INTEGER DEFAULT 0,
    location_is_manual INTEGER DEFAULT 0,
    linkedin_url_is_manual INTEGER DEFAULT 0,
    github_url_is_manual INTEGER DEFAULT 0,
    portfolio_url_is_manual INTEGER DEFAULT 0,
    preferred_role_is_manual INTEGER DEFAULT 0,
    career_goal_is_manual INTEGER DEFAULT 0,
    expected_salary_is_manual INTEGER DEFAULT 0,
    preferred_location_is_manual INTEGER DEFAULT 0,
    last_resume_sync TIMESTAMP,
    last_manual_update TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resume_versions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_target TEXT NOT NULL,
    version_type TEXT NOT NULL,
    content TEXT NOT NULL,
    scores TEXT DEFAULT '{}',
    suggestions TEXT DEFAULT '[]',
    template TEXT DEFAULT 'modern',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    skills TEXT DEFAULT '[]',
    top_skills TEXT DEFAULT '[]',
    projects TEXT DEFAULT '[]',
    experience_years INTEGER DEFAULT 0,
    education TEXT DEFAULT '',
    preferred_role TEXT DEFAULT '',
    preferred_location TEXT DEFAULT '',
    expected_salary TEXT DEFAULT '',
    technologies TEXT DEFAULT '[]',
    soft_skills TEXT DEFAULT '[]',
    career_goal TEXT DEFAULT '',
    experience_summary TEXT DEFAULT '',
    domain TEXT DEFAULT '',
    seniority_level TEXT DEFAULT 'fresher',
    search_queries TEXT DEFAULT '[]',
    profile_score INTEGER DEFAULT 0,
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS problem_templates (
    id SERIAL PRIMARY KEY,
    problem_id INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    function_signature TEXT,
    return_type TEXT,
    starter_code TEXT,
    driver_template TEXT
);

CREATE TABLE IF NOT EXISTS problem_test_cases (
    id SERIAL PRIMARY KEY,
    problem_id INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    input TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_hidden INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS problem_submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    language TEXT NOT NULL,
    status TEXT NOT NULL,
    execution_time INTEGER DEFAULT 0,
    memory INTEGER DEFAULT 0,
    coding_metrics TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_problem_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    streak INTEGER DEFAULT 0,
    confidence_score INTEGER DEFAULT 50,
    learning_velocity REAL DEFAULT 1.0,
    last_submission_at TEXT
);

CREATE TABLE IF NOT EXISTS user_topic_scores (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    UNIQUE(user_id, topic)
);

CREATE TABLE IF NOT EXISTS problem_hints_used (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    problem_id INTEGER NOT NULL,
    hint_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, problem_id, hint_index)
);

-- Level 2: Tables dependent on Level 1
CREATE TABLE IF NOT EXISTS resume_analysis (
    id SERIAL PRIMARY KEY,
    resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ats_score INTEGER DEFAULT 0,
    strong_skills TEXT DEFAULT '[]',
    weak_skills TEXT DEFAULT '[]',
    missing_keywords TEXT DEFAULT '[]',
    grammar_issues TEXT DEFAULT '[]',
    experience_analysis TEXT DEFAULT '',
    project_analysis TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    action_plan TEXT DEFAULT '[]',
    full_analysis TEXT DEFAULT '{}',
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    message TEXT NOT NULL,
    module TEXT DEFAULT 'career_coach',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    company_logo TEXT DEFAULT '',
    location TEXT DEFAULT '',
    salary_raw TEXT DEFAULT '',
    salary_min INTEGER DEFAULT 0,
    salary_max INTEGER DEFAULT 0,
    salary_estimate TEXT DEFAULT '',
    job_type TEXT DEFAULT 'Full-time',
    experience_required TEXT DEFAULT '',
    is_remote INTEGER DEFAULT 0,
    description TEXT DEFAULT '',
    apply_link TEXT DEFAULT '',
    source TEXT DEFAULT '',
    posted_date TEXT DEFAULT '',
    freshness TEXT DEFAULT 'recent',
    urgency TEXT DEFAULT 'normal',
    resume_match INTEGER DEFAULT 0,
    ats_score INTEGER DEFAULT 0,
    shortlist_probability INTEGER DEFAULT 0,
    interview_probability INTEGER DEFAULT 0,
    competition_level TEXT DEFAULT 'medium',
    learning_time TEXT DEFAULT '',
    required_skills TEXT DEFAULT '[]',
    missing_skills TEXT DEFAULT '[]',
    matching_skills TEXT DEFAULT '[]',
    ai_summary TEXT DEFAULT '',
    match_reason TEXT DEFAULT '',
    category TEXT DEFAULT 'medium_match',
    status TEXT DEFAULT 'new' CHECK(status IN ('new','saved','applied','hidden','expired')),
    agent_run_id TEXT DEFAULT '',
    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL,
    status TEXT DEFAULT 'running' CHECK(status IN ('running','completed','failed')),
    jobs_searched INTEGER DEFAULT 0,
    jobs_matched INTEGER DEFAULT 0,
    queries_used TEXT DEFAULT '[]',
    summary TEXT DEFAULT '',
    error TEXT DEFAULT '',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_problem_feedback (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES problem_submissions(id) ON DELETE CASCADE,
    correctness INTEGER,
    time_complexity TEXT,
    space_complexity TEXT,
    naming_convention INTEGER,
    readability INTEGER,
    logic INTEGER,
    optimization INTEGER,
    code_style INTEGER,
    maintainability INTEGER,
    edge_cases TEXT,
    potential_bugs TEXT,
    interview_quality INTEGER,
    overall_score INTEGER,
    feedback_report TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resume_analysis_user_id ON resume_analysis(user_id);
CREATE INDEX IF NOT EXISTS idx_resume_analysis_resume_id ON resume_analysis(resume_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_module ON chat_history(module);
CREATE INDEX IF NOT EXISTS idx_job_history_user_id ON job_history(user_id);
CREATE INDEX IF NOT EXISTS idx_job_history_status ON job_history(status);
CREATE INDEX IF NOT EXISTS idx_interview_history_user_id ON interview_history(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_roadmaps_user_id ON learning_roadmaps(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_code_reviews_user_id ON code_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_sql_queries_user_id ON sql_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_profiles_user_id ON agent_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_job_notifications_user_id ON job_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_job_notifications_status ON job_notifications(status);
CREATE INDEX IF NOT EXISTS idx_job_notifications_category ON job_notifications(category);
CREATE INDEX IF NOT EXISTS idx_job_notifications_resume_match ON job_notifications(resume_match);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_career_profiles_user_id ON career_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_resume_versions_user_id ON resume_versions(user_id);
"""

# Tables in strict foreign-key dependency order
MIGRATION_ORDER = [
    # Tier 0 (Root tables)
    "users",
    "admin_users",
    "admin_audit_logs",
    "problems",
    # Tier 1 (Depend on Tier 0)
    "resumes",
    "chat_sessions",
    "job_history",
    "interview_history",
    "learning_roadmaps",
    "projects",
    "settings",
    "code_reviews",
    "sql_queries",
    "career_profiles",
    "resume_versions",
    "agent_profiles",
    "problem_templates",
    "problem_test_cases",
    "problem_submissions",
    "user_problem_analytics",
    "user_topic_scores",
    "problem_hints_used",
    "agent_runs",
    # Tier 2 (Depend on Tier 1)
    "resume_analysis",
    "chat_history",
    "job_notifications",
    "ai_problem_feedback"
]


class MigrationRunner:
    def __init__(self, sqlite_path: str, pg_url: str = "", dry_run: bool = False,
                 clean_destination: bool = False, confirm_clean_destination: str = "",
                 skip_orphans: bool = False):
        self.sqlite_path = sqlite_path
        self.pg_url = pg_url or ""
        if self.pg_url.startswith("postgres://"):
            self.pg_url = "postgresql://" + self.pg_url[len("postgres://"):]
        self.dry_run = dry_run
        self.clean_destination = clean_destination
        self.confirm_clean_destination = confirm_clean_destination
        self.skip_orphans = skip_orphans
        self.sqlite_conn = None
        self.pg_conn = None
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.orphans_detected: List[Dict[str, Any]] = []
        self.orphans_skipped: Dict[str, List[Dict[str, Any]]] = {}

    def validate_safety_guards(self):
        """
        Enforce strict destination safety checks against accidental data destruction.
        Rejects known production domains and requires deliberate confirmation string.
        """
        if self.clean_destination:
            # Check 1: Reject known production hosts and patterns
            target = (self.pg_url or "").lower()
            prod_indicators = [
                "render.com", "neon.tech", "supabase.co", "rds.amazonaws.com",
                "aws.com", "azure.com", "pooler.supabase.com", "production", "prod-db"
            ]
            env_mode = os.getenv("ENVIRONMENT", "").lower()
            flask_env = os.getenv("FLASK_ENV", "").lower()

            if any(p in target for p in prod_indicators) or env_mode in ("production", "prod") or flask_env in ("production", "prod"):
                raise RuntimeError(
                    f"[SAFETY VIOLATION] Destructive flag --clean-destination is strictly prohibited "
                    f"against production targets or when ENVIRONMENT=production. "
                    f"Target was: '{mask_url_credentials(self.pg_url)}'. Aborting immediately."
                )

            # Check 2: Require explicit confirmation argument
            expected_token = "YES_DELETE_DESTINATION_DATA"
            if self.confirm_clean_destination != expected_token:
                raise RuntimeError(
                    f"[SAFETY VIOLATION] Destructive flag --clean-destination requires explicit confirmation. "
                    f"Please specify --confirm-clean-destination '{expected_token}' to proceed."
                )

    def validate_connections(self):
        """Validate both source SQLite and destination PostgreSQL connections."""
        print("[-] Validating source SQLite database...")
        if not os.path.exists(self.sqlite_path):
            raise FileNotFoundError(f"SQLite database file not found at: {self.sqlite_path}")

        # Open in read-only URI mode to guarantee source is never mutated
        abs_path = os.path.abspath(self.sqlite_path)
        uri = f"file:{abs_path}?mode=ro"
        self.sqlite_conn = sqlite3.connect(uri, uri=True)
        self.sqlite_conn.row_factory = sqlite3.Row
        cur = self.sqlite_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        tbl_cnt = cur.fetchone()[0]
        print(f"[✓] Source SQLite connection valid: {abs_path} ({tbl_cnt} tables)")

        if self.dry_run and not self.pg_url:
            print("[DRY-RUN] No PostgreSQL URL provided; validating source SQLite database only.")
            return

        print("[-] Validating destination PostgreSQL database...")
        masked = mask_url_credentials(self.pg_url)
        print(f"    Target: {masked}")
        self.pg_conn = psycopg2.connect(self.pg_url)
        with self.pg_conn.cursor() as pg_cur:
            pg_cur.execute("SELECT version();")
            v = pg_cur.fetchone()[0]
            print(f"[✓] Destination PostgreSQL connection valid:\n    {v}")

    def validate_source_referential_integrity(self):
        """
        Scan SQLite source database for foreign-key violations (orphan child records).
        Uses SQLite's PRAGMA foreign_key_check to detect any dangling references.
        """
        print("[-] Scanning source SQLite database for foreign-key integrity...")
        cur = self.sqlite_conn.cursor()
        cur.execute("PRAGMA foreign_key_check;")
        # returns list of (table, rowid, parent_table, fkid)
        violations = cur.fetchall()
        self.orphans_detected = []

        for v in violations:
            tbl, rowid, parent_tbl, fkid = v[0], v[1], v[2], v[3]
            cur.execute(f"PRAGMA foreign_key_list({tbl});")
            fk_info = [r for r in cur.fetchall() if r[0] == fkid]
            from_col = fk_info[0][3] if fk_info else "unknown"
            to_col = fk_info[0][4] if fk_info else "id"

            cur.execute(f"SELECT id, {from_col} FROM {tbl} WHERE rowid = ?", (rowid,))
            val_row = cur.fetchone()
            row_id = val_row["id"] if val_row and "id" in val_row.keys() else rowid
            val = val_row[from_col] if val_row and from_col in val_row.keys() else None

            self.orphans_detected.append({
                "table": tbl,
                "rowid": rowid,
                "id": row_id,
                "parent_table": parent_tbl,
                "from_col": from_col,
                "to_col": to_col,
                "orphan_value": val
            })

        if not self.orphans_detected:
            print("[✓] Source database referential integrity valid: 0 foreign key orphans.")
            return

        print(f"\n[!] CAUTION: Detected {len(self.orphans_detected)} orphaned foreign-key record(s) in source SQLite database:")
        for o in self.orphans_detected:
            print(f"    - Table '{o['table']}' row id={o['id']}: {o['from_col']}={o['orphan_value']} -> references missing '{o['parent_table']}.{o['to_col']}'")

        if not self.skip_orphans:
            tables_affected = sorted(list(set(o['table'] for o in self.orphans_detected)))
            raise RuntimeError(
                f"[REFERENTIAL INTEGRITY VIOLATION] Source SQLite database contains {len(self.orphans_detected)} "
                f"orphan child record(s) in table(s): {', '.join(tables_affected)}. "
                f"PostgreSQL strictly enforces foreign keys and will abort on these rows. "
                f"To safely migrate all valid rows while audit-logging and excluding orphan records, "
                f"pass the '--skip-orphans' flag."
            )
        else:
            print("[✓] Flag '--skip-orphans' is enabled. Orphan records will be logged and excluded from PostgreSQL destination.\n")

    def initialize_destination_schema(self):
        """Create PostgreSQL schema if not existing."""
        if self.dry_run:
            print("[DRY-RUN] Genuinely skipping all DDL and schema modifications.")
            return

        print("[-] Initializing verified PostgreSQL schema...")
        with self.pg_conn.cursor() as cur:
            if self.clean_destination:
                print("[!] Clean destination confirmed. Dropping existing tables in reverse dependency order...")
                for table in reversed(MIGRATION_ORDER):
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                self.pg_conn.commit()

            cur.execute(POSTGRESQL_SCHEMA_DDL)
            self.pg_conn.commit()
        print("[✓] PostgreSQL schema initialized successfully.")

    def migrate_table(self, table: str, cursor=None):
        """Copy records from SQLite to PostgreSQL preserving exact IDs and types."""
        # Inspect SQLite columns
        s_cur = self.sqlite_conn.cursor()
        s_cur.execute(f"PRAGMA table_info({table});")
        sqlite_cols = [r[1] for r in s_cur.fetchall()]
        if not sqlite_cols:
            print(f"    [!] Table {table} does not exist in SQLite source. Skipping.")
            return

        # Fetch records from SQLite (include rowid to uniquely identify any detected orphans)
        s_cur.execute(f"SELECT rowid, {', '.join(sqlite_cols)} FROM {table};")
        raw_rows = s_cur.fetchall()
        total_rows = len(raw_rows)

        # Check for orphans in this table
        orphan_rowids = {o["rowid"] for o in self.orphans_detected if o["table"] == table}
        table_orphans = []
        valid_rows = []

        for r in raw_rows:
            rid = r[0]
            row_data = r[1:]
            if self.skip_orphans and rid in orphan_rowids:
                matching_o = next((o for o in self.orphans_detected if o["table"] == table and o["rowid"] == rid), None)
                row_id_val = matching_o.get("id") if matching_o else rid
                table_orphans.append({
                    "rowid": rid,
                    "id": row_id_val,
                    "details": matching_o
                })
                p_table = matching_o.get("parent_table") if matching_o else "parent"
                to_col = matching_o.get("to_col") if matching_o else "id"
                from_col = matching_o.get("from_col") if matching_o else "fk"
                o_val = matching_o.get("orphan_value") if matching_o else "?"
                print(f"    [AUDIT - ORPHAN EXCLUDED] {table} row id={row_id_val}: {from_col}={o_val} references missing {p_table}.{to_col} (excluded)")
            else:
                valid_rows.append(row_data)

        if table_orphans:
            self.orphans_skipped[table] = table_orphans

        total_to_insert = len(valid_rows)
        skipped_count = len(table_orphans)

        print(f"[-] Migrating `{table}`: {total_to_insert} row(s) to insert" +
              (f" ({skipped_count} orphan(s) excluded)..." if skipped_count else "..."))

        if self.dry_run:
            status = "DRY-RUN"
            if skipped_count > 0:
                status = f"DRY-RUN ({skipped_count} orphan(s) excluded)"
            self.stats[table] = {
                "sqlite": total_rows,
                "pg": total_to_insert,
                "orphans_skipped": skipped_count,
                "status": status
            }
            return

        if total_to_insert == 0:
            self.stats[table] = {
                "sqlite": total_rows,
                "pg": 0,
                "orphans_skipped": skipped_count,
                "status": "EMPTY"
            }
            return

        # PostgreSQL insert (stops safely on duplicate key without broad ON CONFLICT DO NOTHING)
        cols_str = ", ".join(sqlite_cols)
        placeholders = ", ".join(["%s"] * len(sqlite_cols))
        insert_sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"

        data_tuples = [tuple(row) for row in valid_rows]

        p_cur = cursor if cursor else self.pg_conn.cursor()
        try:
            execute_batch(p_cur, insert_sql, data_tuples, page_size=500)

            # Verify count in current transaction
            p_cur.execute(f"SELECT COUNT(*) FROM {table};")
            pg_count = p_cur.fetchone()[0]

            expected_count = total_to_insert
            status = "MATCH" if pg_count == expected_count else "MISMATCH"
            if status == "MATCH" and skipped_count > 0:
                status = f"MATCH ({skipped_count} orphan(s) excluded)"

            self.stats[table] = {
                "sqlite": total_rows,
                "pg": pg_count,
                "orphans_skipped": skipped_count,
                "status": status
            }
        finally:
            if cursor is None:
                p_cur.close()

    def reset_sequences(self, cursor=None):
        """Update PostgreSQL auto-increment sequences to MAX(id), correctly handling empty & populated tables."""
        if self.dry_run:
            return

        print("[-] Synchronizing PostgreSQL primary key sequences...")
        cur = cursor if cursor else self.pg_conn.cursor()
        try:
            for table in MIGRATION_ORDER:
                if table == "chat_sessions":
                    continue  # uses UUID/text session_id PK
                cur.execute(f"""
                    DO $$
                    DECLARE
                        seq TEXT;
                        max_id BIGINT;
                    BEGIN
                        seq := pg_get_serial_sequence('{table}', 'id');
                        IF seq IS NOT NULL THEN
                            SELECT MAX(id) INTO max_id FROM {table};
                            IF max_id IS NOT NULL THEN
                                PERFORM setval(seq, max_id, true);
                            ELSE
                                PERFORM setval(seq, 1, false);
                            END IF;
                        END IF;
                    END $$;
                """)
        finally:
            if cursor is None:
                cur.close()
        print("[✓] Primary key sequences synchronized.")

    def run(self):
        """Execute end-to-end migration process with atomic transaction safety."""
        start_time = time.time()
        print("=" * 70)
        print(" CareerPilot AI — SQLite to PostgreSQL Migration Utility")
        print("=" * 70)

        try:
            self.validate_safety_guards()
            self.validate_connections()
            self.validate_source_referential_integrity()
            self.initialize_destination_schema()

            if self.dry_run:
                print("\n[DRY-RUN] Simulating data migration (strictly 0 writes to destination)...")
                for table in MIGRATION_ORDER:
                    self.migrate_table(table)
                elapsed = round(time.time() - start_time, 2)
                self.print_report(elapsed)
                return

            print("\n[-] Starting atomic data migration in topological dependency order...")
            # Atomic transaction boundary: all tables and sequences commit together
            with self.pg_conn:
                with self.pg_conn.cursor() as cur:
                    for table in MIGRATION_ORDER:
                        self.migrate_table(table, cursor=cur)
                    self.reset_sequences(cursor=cur)
            print("[✓] Atomic transaction committed successfully.")

            elapsed = round(time.time() - start_time, 2)
            self.print_report(elapsed)

        except Exception as e:
            if self.pg_conn:
                try:
                    self.pg_conn.rollback()
                except Exception:
                    pass
            print(f"\n[FATAL ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            if self.sqlite_conn:
                try:
                    self.sqlite_conn.close()
                except Exception:
                    pass
            if self.pg_conn:
                try:
                    self.pg_conn.close()
                except Exception:
                    pass

    def print_report(self, elapsed: float):
        """Print audit and verification report."""
        print("\n" + "=" * 70)
        print(" MIGRATION VERIFICATION REPORT")
        print("=" * 70)
        print(f"{'Table Name':<28} | {'SQLite Rows':<12} | {'PG Rows':<10} | {'Status':<10}")
        print("-" * 70)

        all_matched = True
        total_sqlite = 0
        total_pg = 0

        for table in MIGRATION_ORDER:
            st = self.stats.get(table, {"sqlite": 0, "pg": 0, "status": "SKIPPED", "orphans_skipped": 0})
            s_cnt = st["sqlite"]
            p_cnt = st["pg"]
            status = st["status"]
            total_sqlite += s_cnt
            total_pg += p_cnt

            if not (status.startswith("MATCH") or status in ("EMPTY", "DRY-RUN") or "DRY-RUN" in status):
                all_matched = False

            print(f"{table:<28} | {s_cnt:<12} | {p_cnt:<10} | {status:<10}")

        print("-" * 70)
        print(f"{'TOTALS':<28} | {total_sqlite:<12} | {total_pg:<10} |")
        print(f"\nCompleted in: {elapsed} seconds")

        if self.orphans_skipped:
            print("\n" + "=" * 70)
            print(" AUDITED ORPHAN RECORDS EXCLUDED FROM POSTGRESQL")
            print("=" * 70)
            for tbl, orphans in self.orphans_skipped.items():
                print(f"Table '{tbl}' ({len(orphans)} record(s) excluded):")
                for o in orphans:
                    d = o.get("details", {})
                    p_tbl = d.get("parent_table", "users") if d else "users"
                    to_col = d.get("to_col", "id") if d else "id"
                    from_col = d.get("from_col", "user_id") if d else "user_id"
                    o_val = d.get("orphan_value", "?") if d else "?"
                    print(f"  - Row id={o.get('id')}: {from_col}={o_val} -> references missing {p_tbl}.{to_col}")
            print("=" * 70)

        if all_matched:
            print("\n[✓] ALL TABLE ROW COUNTS AND CONSTRAINTS MATCH PERFECTLY!")
        else:
            print("\n[!] WARNING: Some row counts did not match or errors occurred.")


def main():
    parser = argparse.ArgumentParser(description="Migrate CareerPilot AI from SQLite to PostgreSQL")
    parser.add_argument("--sqlite-path", default=os.getenv("DATABASE_PATH", "database.db"),
                        help="Path to source SQLite database (default: database.db)")
    parser.add_argument("--pg-url", default=os.getenv("DATABASE_URL", ""),
                        help="Destination PostgreSQL connection URL (or set DATABASE_URL)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate connections and print table counts without copying data")
    parser.add_argument("--skip-orphans", action="store_true",
                        help="Audit and safely exclude orphaned child records whose foreign key parent is missing")
    parser.add_argument("--clean-destination", action="store_true",
                        help="Drop destination tables before migrating (USE WITH CAUTION)")
    parser.add_argument("--confirm-clean-destination", default="",
                        help="Safety confirmation string required when using --clean-destination ('YES_DELETE_DESTINATION_DATA')")

    args = parser.parse_args()

    if not args.pg_url and not args.dry_run:
        print("[ERROR] Destination PostgreSQL URL is required via --pg-url or DATABASE_URL env var.")
        sys.exit(1)

    runner = MigrationRunner(
        sqlite_path=args.sqlite_path,
        pg_url=args.pg_url,
        dry_run=args.dry_run,
        clean_destination=args.clean_destination,
        confirm_clean_destination=args.confirm_clean_destination,
        skip_orphans=args.skip_orphans
    )
    runner.run()


if __name__ == "__main__":
    main()

