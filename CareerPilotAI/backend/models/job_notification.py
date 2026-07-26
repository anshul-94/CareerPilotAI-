"""
CareerPilot AI — Job Notification Agent Model
CRUD operations for agent_profiles and job_notifications tables.
These tables power the proactive AI Job Notification Agent.
"""

import json
from datetime import datetime
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


# ─────────────────────────────────────────────────────────────
# Schema SQL — run once via migrate_notification_tables()
# ─────────────────────────────────────────────────────────────

NOTIFICATION_SCHEMA_SQL = """
-- AI Agent Profile: Extracted career intelligence per user
CREATE TABLE IF NOT EXISTS agent_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Job Notifications: Scored & analyzed job listings per user
CREATE TABLE IF NOT EXISTS job_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Agent Run Log: Audit trail of each agent execution
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    status TEXT DEFAULT 'running' CHECK(status IN ('running','completed','failed')),
    jobs_searched INTEGER DEFAULT 0,
    jobs_matched INTEGER DEFAULT 0,
    queries_used TEXT DEFAULT '[]',
    summary TEXT DEFAULT '',
    error TEXT DEFAULT '',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_profiles_user_id ON agent_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_job_notifications_user_id ON job_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_job_notifications_status ON job_notifications(status);
CREATE INDEX IF NOT EXISTS idx_job_notifications_category ON job_notifications(category);
CREATE INDEX IF NOT EXISTS idx_job_notifications_resume_match ON job_notifications(resume_match);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);
"""


def migrate_notification_tables() -> None:
    """Run schema migration to add notification agent tables."""
    from backend.database.db import get_db_path
    import sqlite3
    path = get_db_path()
    with sqlite3.connect(path) as conn:
        conn.executescript(NOTIFICATION_SCHEMA_SQL)
        conn.commit()
    print("[✓] Notification agent tables created/verified.")


# ─────────────────────────────────────────────────────────────
# AgentProfileModel
# ─────────────────────────────────────────────────────────────

class AgentProfileModel:
    """CRUD for agent_profiles — the AI-extracted career profile."""

    @staticmethod
    def get_by_user(user_id: int) -> Optional[dict]:
        """Fetch the AI profile for a user."""
        return execute_one(
            "SELECT * FROM agent_profiles WHERE user_id = ?",
            (user_id,)
        )

    @staticmethod
    def upsert(user_id: int, profile_data: dict) -> int:
        """Insert or update the AI profile for a user."""
        existing = AgentProfileModel.get_by_user(user_id)

        skills         = json.dumps(profile_data.get("skills", []))
        top_skills     = json.dumps(profile_data.get("top_skills", []))
        projects       = json.dumps(profile_data.get("projects", []))
        technologies   = json.dumps(profile_data.get("technologies", []))
        soft_skills    = json.dumps(profile_data.get("soft_skills", []))
        search_queries = json.dumps(profile_data.get("search_queries", []))
        now            = datetime.now().isoformat()

        if existing:
            execute_update(
                """UPDATE agent_profiles SET
                    skills=?, top_skills=?, projects=?, experience_years=?,
                    education=?, preferred_role=?, preferred_location=?,
                    expected_salary=?, technologies=?, soft_skills=?,
                    career_goal=?, experience_summary=?, domain=?,
                    seniority_level=?, search_queries=?, profile_score=?,
                    last_synced=?, updated_at=?
                   WHERE user_id=?""",
                (skills, top_skills, projects,
                 profile_data.get("experience_years", 0),
                 profile_data.get("education", ""),
                 profile_data.get("preferred_role", ""),
                 profile_data.get("preferred_location", ""),
                 profile_data.get("expected_salary", ""),
                 technologies, soft_skills,
                 profile_data.get("career_goal", ""),
                 profile_data.get("experience_summary", ""),
                 profile_data.get("domain", ""),
                 profile_data.get("seniority_level", "fresher"),
                 search_queries,
                 profile_data.get("profile_score", 0),
                 now, now, user_id)
            )
            return existing["id"]
        else:
            return execute_insert(
                """INSERT INTO agent_profiles
                   (user_id, skills, top_skills, projects, experience_years,
                    education, preferred_role, preferred_location, expected_salary,
                    technologies, soft_skills, career_goal, experience_summary,
                    domain, seniority_level, search_queries, profile_score, last_synced)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, skills, top_skills, projects,
                 profile_data.get("experience_years", 0),
                 profile_data.get("education", ""),
                 profile_data.get("preferred_role", ""),
                 profile_data.get("preferred_location", ""),
                 profile_data.get("expected_salary", ""),
                 technologies, soft_skills,
                 profile_data.get("career_goal", ""),
                 profile_data.get("experience_summary", ""),
                 profile_data.get("domain", ""),
                 profile_data.get("seniority_level", "fresher"),
                 search_queries,
                 profile_data.get("profile_score", 0),
                 now)
            )

    @staticmethod
    def parse(profile: dict) -> dict:
        """Parse JSON fields in a profile row."""
        if not profile:
            return {}
        for field in ["skills", "top_skills", "projects", "technologies",
                      "soft_skills", "search_queries"]:
            val = profile.get(field, "[]")
            if isinstance(val, str):
                try:
                    profile[field] = json.loads(val)
                except Exception:
                    profile[field] = []
        return profile


# ─────────────────────────────────────────────────────────────
# JobNotificationModel
# ─────────────────────────────────────────────────────────────

class JobNotificationModel:
    """CRUD for job_notifications — AI-scored job cards."""

    @staticmethod
    def create(user_id: int, job: dict, agent_run_id: str = "") -> int:
        """Insert a single job notification record."""
        return execute_insert(
            """INSERT INTO job_notifications
               (user_id, title, company, company_logo, location,
                salary_raw, salary_min, salary_max, salary_estimate,
                job_type, experience_required, is_remote, description,
                apply_link, source, posted_date, freshness, urgency,
                resume_match, ats_score, shortlist_probability,
                interview_probability, competition_level, learning_time,
                required_skills, missing_skills, matching_skills,
                ai_summary, match_reason, category, agent_run_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user_id,
                job.get("title", ""),
                job.get("company", ""),
                job.get("company_logo", ""),
                job.get("location", ""),
                job.get("salary_raw", ""),
                job.get("salary_min", 0),
                job.get("salary_max", 0),
                job.get("salary_estimate", ""),
                job.get("job_type", "Full-time"),
                job.get("experience_required", ""),
                1 if job.get("is_remote") else 0,
                job.get("description", ""),
                job.get("apply_link", ""),
                job.get("source", ""),
                job.get("posted_date", ""),
                job.get("freshness", "recent"),
                job.get("urgency", "normal"),
                job.get("resume_match", 0),
                job.get("ats_score", 0),
                job.get("shortlist_probability", 0),
                job.get("interview_probability", 0),
                job.get("competition_level", "medium"),
                job.get("learning_time", ""),
                json.dumps(job.get("required_skills", [])),
                json.dumps(job.get("missing_skills", [])),
                json.dumps(job.get("matching_skills", [])),
                job.get("ai_summary", ""),
                job.get("match_reason", ""),
                job.get("category", "medium_match"),
                agent_run_id,
            )
        )

    @staticmethod
    def bulk_create(user_id: int, jobs: list[dict], agent_run_id: str = "") -> int:
        """Bulk insert job notifications."""
        count = 0
        for job in jobs:
            try:
                JobNotificationModel.create(user_id, job, agent_run_id)
                count += 1
            except Exception as e:
                print(f"[WARN] Failed to insert job: {e}")
        return count

    @staticmethod
    def get_by_user(user_id: int, status: str = None,
                    category: str = None, limit: int = 100) -> list[dict]:
        """Fetch notifications for a user, with optional filters."""
        wheres = ["user_id = ?"]
        params = [user_id]
        if status:
            wheres.append("status = ?")
            params.append(status)
        if category:
            wheres.append("category = ?")
            params.append(category)
        params.append(limit)

        rows = execute_query(
            f"""SELECT * FROM job_notifications
                WHERE {' AND '.join(wheres)}
                ORDER BY resume_match DESC, shortlist_probability DESC, found_at DESC
                LIMIT ?""",
            tuple(params)
        )
        return [JobNotificationModel._parse_row(r) for r in rows]

    @staticmethod
    def get_stats(user_id: int) -> dict:
        """Aggregate statistics for the notification dashboard."""
        result = execute_one(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN resume_match >= 80 THEN 1 ELSE 0 END) as high_match,
                SUM(CASE WHEN resume_match >= 60 AND resume_match < 80 THEN 1 ELSE 0 END) as medium_match,
                SUM(CASE WHEN resume_match < 60 THEN 1 ELSE 0 END) as low_match,
                SUM(CASE WHEN shortlist_probability >= 80 THEN 1 ELSE 0 END) as high_shortlist,
                SUM(CASE WHEN is_remote = 1 THEN 1 ELSE 0 END) as remote_count,
                SUM(CASE WHEN urgency = 'urgent' THEN 1 ELSE 0 END) as urgent_count,
                SUM(CASE WHEN status = 'saved' THEN 1 ELSE 0 END) as saved_count,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied_count,
                AVG(resume_match) as avg_match,
                AVG(shortlist_probability) as avg_shortlist,
                AVG(ats_score) as avg_ats,
                MAX(resume_match) as top_match
               FROM job_notifications
               WHERE user_id = ? AND status != 'hidden'""",
            (user_id,)
        )
        return result or {}

    @staticmethod
    def update_status(notification_id: int, status: str) -> int:
        """Update job notification status."""
        return execute_update(
            "UPDATE job_notifications SET status=?, updated_at=? WHERE id=?",
            (status, datetime.now().isoformat(), notification_id)
        )

    @staticmethod
    def clear_old_notifications(user_id: int, keep_statuses: list = None) -> int:
        """Remove old 'new' notifications before a fresh agent run."""
        if keep_statuses is None:
            keep_statuses = ["saved", "applied"]
        placeholders = ",".join(["?" for _ in keep_statuses])
        return execute_update(
            f"DELETE FROM job_notifications WHERE user_id=? AND status NOT IN ({placeholders})",
            (user_id, *keep_statuses)
        )

    @staticmethod
    def get_missing_skills_summary(user_id: int) -> list[dict]:
        """Aggregate most common missing skills across all notifications."""
        rows = execute_query(
            "SELECT missing_skills FROM job_notifications WHERE user_id=? AND status != 'hidden'",
            (user_id,)
        )
        skill_count: dict[str, int] = {}
        for row in rows:
            try:
                skills = json.loads(row.get("missing_skills", "[]"))
                for s in skills:
                    skill_count[s] = skill_count.get(s, 0) + 1
            except Exception:
                pass
        sorted_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)
        return [{"skill": k, "job_count": v} for k, v in sorted_skills[:15]]

    @staticmethod
    def get_company_distribution(user_id: int) -> list[dict]:
        """Count jobs per company for distribution chart."""
        return execute_query(
            """SELECT company, COUNT(*) as count, AVG(resume_match) as avg_match
               FROM job_notifications
               WHERE user_id=? AND status != 'hidden'
               GROUP BY company ORDER BY count DESC LIMIT 10""",
            (user_id,)
        )

    @staticmethod
    def get_salary_distribution(user_id: int) -> list[dict]:
        """Return salary distribution buckets."""
        return execute_query(
            """SELECT salary_estimate, COUNT(*) as count
               FROM job_notifications
               WHERE user_id=? AND salary_estimate != '' AND status != 'hidden'
               GROUP BY salary_estimate ORDER BY count DESC""",
            (user_id,)
        )

    @staticmethod
    def _parse_row(row: dict) -> dict:
        """Parse JSON fields in a notification row."""
        if not row:
            return {}
        for field in ["required_skills", "missing_skills", "matching_skills"]:
            val = row.get(field, "[]")
            if isinstance(val, str):
                try:
                    row[field] = json.loads(val)
                except Exception:
                    row[field] = []
        return row


# ─────────────────────────────────────────────────────────────
# AgentRunModel
# ─────────────────────────────────────────────────────────────

class AgentRunModel:
    """Audit trail for each agent run."""

    @staticmethod
    def create(user_id: int, run_id: str) -> int:
        return execute_insert(
            """INSERT INTO agent_runs (user_id, run_id, status)
               VALUES (?, ?, 'running')""",
            (user_id, run_id)
        )

    @staticmethod
    def complete(run_id: str, jobs_searched: int, jobs_matched: int,
                 queries_used: list, summary: str) -> None:
        execute_update(
            """UPDATE agent_runs SET status='completed', jobs_searched=?,
               jobs_matched=?, queries_used=?, summary=?, completed_at=?
               WHERE run_id=?""",
            (jobs_searched, jobs_matched, json.dumps(queries_used),
             summary, datetime.now().isoformat(), run_id)
        )

    @staticmethod
    def fail(run_id: str, error: str) -> None:
        execute_update(
            "UPDATE agent_runs SET status='failed', error=?, completed_at=? WHERE run_id=?",
            (error, datetime.now().isoformat(), run_id)
        )

    @staticmethod
    def get_last(user_id: int) -> Optional[dict]:
        return execute_one(
            "SELECT * FROM agent_runs WHERE user_id=? ORDER BY started_at DESC LIMIT 1",
            (user_id,)
        )
