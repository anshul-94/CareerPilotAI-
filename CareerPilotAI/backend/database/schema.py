"""
CareerPilot AI — Database Schema
Complete SQLite schema with all tables, foreign keys, indexes, and timestamps.
"""

SCHEMA_SQL = """
-- ============================================
-- CareerPilot AI — Database Schema
-- ============================================

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

-- Resumes Table
CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    raw_text TEXT DEFAULT '',
    parsed_data TEXT DEFAULT '{}',
    is_primary INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Resume Analysis Table
CREATE TABLE IF NOT EXISTS resume_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
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
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Chat Sessions Table
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT DEFAULT 'New Conversation',
    is_pinned INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Chat History Table
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    message TEXT NOT NULL,
    module TEXT DEFAULT 'career_coach',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Job History Table
CREATE TABLE IF NOT EXISTS job_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Interview History Table
CREATE TABLE IF NOT EXISTS interview_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
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
    conducted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Learning Roadmaps Table
CREATE TABLE IF NOT EXISTS learning_roadmaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_role TEXT NOT NULL,
    current_skills TEXT DEFAULT '[]',
    roadmap_data TEXT DEFAULT '{}',
    daily_plan TEXT DEFAULT '{}',
    weekly_plan TEXT DEFAULT '{}',
    resources TEXT DEFAULT '{}',
    progress_percent INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'paused', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    domain TEXT NOT NULL,
    skills TEXT DEFAULT '[]',
    experience_level TEXT DEFAULT 'beginner',
    project_data TEXT DEFAULT '{}',
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User Settings Table
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    theme TEXT DEFAULT 'dark',
    notifications INTEGER DEFAULT 1,
    email_alerts INTEGER DEFAULT 1,
    preferred_role TEXT DEFAULT '',
    preferred_location TEXT DEFAULT '',
    expected_salary INTEGER DEFAULT 0,
    job_type_preference TEXT DEFAULT 'Full-time',
    experience_level TEXT DEFAULT 'fresher',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Code Reviews Table
CREATE TABLE IF NOT EXISTS code_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    language TEXT DEFAULT 'python',
    code_input TEXT NOT NULL,
    review_data TEXT DEFAULT '{}',
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- SQL Queries Table
CREATE TABLE IF NOT EXISTS sql_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    query_input TEXT NOT NULL,
    analysis_data TEXT DEFAULT '{}',
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================
-- Indexes for Performance
-- ============================================
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
"""


def init_db(db_path: str = "database.db") -> None:
    """Initialize the database with the complete schema."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"[✓] Database initialized at {db_path}")


def reset_db(db_path: str = "database.db") -> None:
    """Drop all tables and reinitialize (development only)."""
    import sqlite3
    import os
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[✓] Removed existing database: {db_path}")
    init_db(db_path)


if __name__ == "__main__":
    init_db()
