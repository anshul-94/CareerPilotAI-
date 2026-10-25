# DATABASE_MIGRATION_AUDIT.md
## CareerPilot AI — SQLite → PostgreSQL Migration Audit

> **Status:** READ-ONLY AUDIT — No project files were modified.
> **Date:** 2026-10-23
> **Audited by:** Antigravity AI (Claude Sonnet 4.6 Thinking)

---

## Table of Contents

1. [Project and Database Overview](#1-project-and-database-overview)
2. [Database Configuration and Connection Flow](#2-database-configuration-and-connection-flow)
3. [Complete Verified Database Schema](#3-complete-verified-database-schema)
4. [Table-to-File / Function Usage Mapping](#4-table-to-file--function-usage-mapping)
5. [Feature-by-Feature Database Dependencies](#5-feature-by-feature-database-dependencies)
6. [Resume and File Storage Architecture](#6-resume-and-file-storage-architecture)
7. [Deployment and Data-Persistence Risks](#7-deployment-and-data-persistence-risks)
8. [SQLite-to-PostgreSQL Compatibility Issues](#8-sqlite-to-postgresql-compatibility-issues)
9. [Files Likely to Require Changes](#9-files-likely-to-require-changes)
10. [Data Preservation and Migration Risks](#10-data-preservation-and-migration-risks)
11. [Missing Information and Unresolved Questions](#11-missing-information-and-unresolved-questions)
12. [Recommended Migration Plan (Phased)](#12-recommended-migration-plan-phased)
13. [Verification Checklist](#13-verification-checklist)

---

## 1. Project and Database Overview

### Application Summary

| Property | Value |
|---|---|
| Application Name | CareerPilot AI |
| Version | 1.0.0 |
| Framework | Flask 3.1.1 (Python) |
| Template Engine | Jinja2 3.1.6 |
| Current Database | SQLite (file-based) |
| Target Database | PostgreSQL (migration goal) |
| Deployment Target | Render (cloud) |
| AI Providers | Groq API (production), Ollama (local dev) |

### Application Architecture

The project is a Flask monolith with a layered backend:

```
app.py                    ← Application factory / entry point
backend/
  config.py               ← Centralized env-var configuration
  database/
    db.py                 ← Database connection manager (raw sqlite3)
    schema.py             ← Base schema DDL + init_db() + reset_db()
    startup.py            ← initialize_database() orchestrator
  models/                 ← Per-table CRUD classes (Data Access Layer)
  routes/                 ← Flask blueprints (controllers)
  services/               ← Business logic layer
  ai/                     ← AI provider wrappers
  utils/                  ← Helpers, decorators, validators, logger
  prompts/                ← LLM prompt builders
```

### Verified Live Table Count (from `database.db`)

Running `sqlite3 database.db ".tables"` confirmed **27 tables** are active in the live database.

---

## 2. Database Configuration and Connection Flow

### 2.1 Database File Locations

| File | Path | Size | Role |
|---|---|---|---|
| **Primary DB** | `CareerPilotAI/database.db` | ~1.9 MB | Live production/development database |
| Backup DB | `CareerPilotAI/database_backup_before_user_cleanup.db` | ~868 KB | Manual backup snapshot |
| Test DB | `CareerPilotAI/test_ui.db` | ~128 KB | Used by Selenium / UI tests |
| Schema DB 1 | `CareerPilotAI/careerpilot.db` | 0 bytes | Empty (unused stub at root) |
| Schema DB 2 | `CareerPilotAI/backend/database/careerpilot.db` | ~128 KB | Created by `init_db.py` — separate from main |
| Schema DB 3 | `CareerPilotAI/backend/database/database.db` | ~136 KB | Another development artifact |

> [!WARNING]
> There are **multiple SQLite files** across the project. Only `CareerPilotAI/database.db` is the live application database. The others are development artifacts or backups.

### 2.2 Environment Variable Configuration

The database path is resolved from `DATABASE_PATH` env var (not `DATABASE_URL`).

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `"database.db"` | **Relative path** to the SQLite file |
| `DATABASE_URL` | *(defined in .env files, but **never read by the application code**)* | Placeholder only — not used |
| `UPLOAD_FOLDER` | `"static/uploads"` | Resume PDF upload directory |
| `ENVIRONMENT` | `"development"` | Controls prod vs dev config class |
| `SECRET_KEY` | `"careerpilot-dev-secret-key"` | Flask session secret |
| `RENDER` | *(not set)* | Set to `"true"` on Render platform |

> [!IMPORTANT]
> `DATABASE_URL` appears in `.env.example`, `.env.development`, and `.env.production` but is **never read by `config.py` or `db.py`**. The active variable is `DATABASE_PATH`. This is a critical discrepancy for the migration.

### 2.3 Path Resolution Logic

```python
# backend/database/db.py — get_db_path()
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Resolves to: /path/to/CareerPilotAI/
return os.path.join(base_dir, DATABASE_PATH)
# Final path: /path/to/CareerPilotAI/database.db
```

The path is **computed relative to the source file location**, not the working directory. If `DATABASE_PATH` is a relative value like `"database.db"`, the database is expected at the project root.

### 2.4 Database Library and Connection Pattern

- **Library used:** Python's built-in `sqlite3` module
- **No ORM:** The project does **not** use SQLAlchemy or any ORM. All queries are raw SQL strings with `?` parameter placeholders.
- **Row factory:** `conn.row_factory = sqlite3.Row` — enables dict-like column access.
- **WAL mode enabled:** `PRAGMA journal_mode = WAL` is applied per connection.
- **Foreign keys enforced:** `PRAGMA foreign_keys = ON` is applied per connection.

### 2.5 Connection Pattern

All database access goes through `backend/database/db.py` via these helper functions:

| Function | Operation | Returns |
|---|---|---|
| `get_connection()` | Opens a new connection | `sqlite3.Connection` |
| `get_db()` | Context manager (auto commit/rollback/close) | yields `conn` |
| `execute_query()` | SELECT → list | `list[dict]` |
| `execute_one()` | SELECT → single row | `dict \| None` |
| `execute_insert()` | INSERT | `int` (lastrowid) |
| `execute_update()` | UPDATE / DELETE | `int` (rowcount) |
| `execute_many()` | Batch INSERT/UPDATE | `int` (rowcount) |
| `table_exists()` | Check table existence via `sqlite_master` | `bool` |
| `get_table_count()` | COUNT(*) on table | `int` |

> [!NOTE]
> Connections are **always** opened, committed/rolled back, and closed within a `with get_db()` context manager. No persistent or pooled connections are used.

### 2.6 Database Initialization Flow

At startup (`app.py` → `initialize_database()` in `startup.py`):

1. **Base schema** (`schema.py::init_db()`) creates 11 core tables via `CREATE TABLE IF NOT EXISTS`.
2. **Migration functions** are called in sequence to create/evolve 6 additional table groups:
   - `migrate_career_profile_table()` → `career_profiles` table
   - `migrate_resume_versions_table()` → `resume_versions` table
   - `migrate_notification_tables()` → `agent_profiles`, `job_notifications`, `agent_runs` tables
   - `migrate_chat_sessions_table()` → `chat_sessions` table (also in base schema — idempotent)
   - `migrate_problem_solving_tables()` → 7 problem/coding tables
   - `migrate_admin_tables()` → `admin_users`, `admin_audit_logs` tables + seeds default admin

All migrations use `CREATE TABLE IF NOT EXISTS`, making them safe to re-run.

---

## 3. Complete Verified Database Schema

All 27 tables confirmed to exist in the live `database.db`.

### 3.1 Core Tables (from `backend/database/schema.py`)

#### Table: `users`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | Auto-incrementing ID |
| `username` | TEXT | NOT NULL UNIQUE | — | Login identifier |
| `email` | TEXT | NOT NULL UNIQUE | — | Login / contact |
| `password_hash` | TEXT | NOT NULL | — | bcrypt hash |
| `full_name` | TEXT | | `''` | Display name |
| `avatar_url` | TEXT | | `'/static/images/default-avatar.png'` | Local path |
| `bio` | TEXT | | `''` | |
| `phone` | TEXT | | `''` | |
| `location` | TEXT | | `''` | |
| `linkedin_url` | TEXT | | `''` | |
| `github_url` | TEXT | | `''` | |
| `portfolio_url` | TEXT | | `''` | |
| `role` | TEXT | CHECK IN ('user','admin') | `'user'` | |
| `is_active` | INTEGER | | `1` | Boolean stored as 0/1 |
| `last_login` | TIMESTAMP | | NULL | ISO string |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `resumes`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `filename` | TEXT | NOT NULL | — | Server-generated secure filename |
| `original_name` | TEXT | NOT NULL | — | User's original filename |
| `file_size` | INTEGER | | `0` | Bytes |
| `raw_text` | TEXT | | `''` | Extracted PDF text |
| `parsed_data` | TEXT | | `'{}'` | JSON blob |
| `is_primary` | INTEGER | | `0` | Boolean 0/1 |
| `uploaded_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `resume_analysis`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `resume_id` | INTEGER | NOT NULL, FK→resumes(id) ON DELETE CASCADE | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `ats_score` | INTEGER | | `0` | 0–100 |
| `strong_skills` | TEXT | | `'[]'` | JSON array |
| `weak_skills` | TEXT | | `'[]'` | JSON array |
| `missing_keywords` | TEXT | | `'[]'` | JSON array |
| `grammar_issues` | TEXT | | `'[]'` | JSON array |
| `experience_analysis` | TEXT | | `''` | |
| `project_analysis` | TEXT | | `''` | |
| `summary` | TEXT | | `''` | |
| `action_plan` | TEXT | | `'[]'` | JSON array |
| `full_analysis` | TEXT | | `'{}'` | JSON blob |
| `analyzed_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `chat_sessions`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `session_id` | TEXT | PRIMARY KEY | — | UUID string — **not INTEGER** |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `title` | TEXT | | `'New Conversation'` | |
| `is_pinned` | INTEGER | | `0` | Boolean 0/1 |
| `is_archived` | INTEGER | | `0` | Boolean 0/1 |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `chat_history`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `session_id` | TEXT | NOT NULL | — | References `chat_sessions.session_id` (no FK constraint in schema) |
| `role` | TEXT | NOT NULL, CHECK IN ('user','assistant','system') | — | |
| `message` | TEXT | NOT NULL | — | Large text |
| `module` | TEXT | | `'career_coach'` | |
| `metadata` | TEXT | | `'{}'` | JSON blob |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

> [!NOTE]
> `chat_history.session_id` references `chat_sessions.session_id` but there is **no FOREIGN KEY constraint** in the `chat_history` DDL. This is intentional or an oversight to be reviewed.

#### Table: `job_history`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `title` | TEXT | NOT NULL | — | |
| `company` | TEXT | NOT NULL | — | |
| `location` | TEXT | | `''` | |
| `salary` | TEXT | | `''` | |
| `job_type` | TEXT | | `'Full-time'` | |
| `experience_level` | TEXT | | `''` | |
| `description` | TEXT | | `''` | |
| `apply_link` | TEXT | | `''` | |
| `source` | TEXT | | `''` | |
| `match_score` | INTEGER | | `0` | |
| `match_details` | TEXT | | `'{}'` | JSON blob |
| `status` | TEXT | CHECK IN ('discovered','saved','applied','interviewing','rejected','offered') | `'discovered'` | |
| `found_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `interview_history`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `session_id` | TEXT | NOT NULL | — | UUID string |
| `role` | TEXT | NOT NULL | — | Job role for interview |
| `difficulty` | TEXT | CHECK IN ('easy','medium','hard','expert') | `'medium'` | |
| `experience_years` | INTEGER | | `0` | |
| `interview_type` | TEXT | | `'technical'` | |
| `questions` | TEXT | | `'[]'` | JSON array |
| `answers` | TEXT | | `'[]'` | JSON array |
| `evaluations` | TEXT | | `'[]'` | JSON array |
| `communication_score` | INTEGER | | `0` | 0–100 |
| `technical_score` | INTEGER | | `0` | 0–100 |
| `confidence_score` | INTEGER | | `0` | 0–100 |
| `overall_score` | INTEGER | | `0` | 0–100 |
| `feedback` | TEXT | | `''` | |
| `conducted_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `learning_roadmaps`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `target_role` | TEXT | NOT NULL | — | |
| `current_skills` | TEXT | | `'[]'` | JSON array |
| `roadmap_data` | TEXT | | `'{}'` | JSON blob |
| `daily_plan` | TEXT | | `'{}'` | JSON blob |
| `weekly_plan` | TEXT | | `'{}'` | JSON blob |
| `resources` | TEXT | | `'{}'` | JSON blob |
| `progress_percent` | INTEGER | | `0` | 0–100 |
| `status` | TEXT | CHECK IN ('active','completed','paused','archived') | `'active'` | |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `projects`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `domain` | TEXT | NOT NULL | — | |
| `skills` | TEXT | | `'[]'` | JSON array |
| `experience_level` | TEXT | | `'beginner'` | |
| `project_data` | TEXT | | `'{}'` | JSON blob |
| `title` | TEXT | | `''` | |
| `description` | TEXT | | `''` | |
| `generated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `settings`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL UNIQUE, FK→users(id) ON DELETE CASCADE | — | One row per user |
| `theme` | TEXT | | `'dark'` | |
| `notifications` | INTEGER | | `1` | Boolean 0/1 |
| `email_alerts` | INTEGER | | `1` | Boolean 0/1 |
| `preferred_role` | TEXT | | `''` | |
| `preferred_location` | TEXT | | `''` | |
| `expected_salary` | INTEGER | | `0` | |
| `job_type_preference` | TEXT | | `'Full-time'` | |
| `experience_level` | TEXT | | `'fresher'` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `code_reviews`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `language` | TEXT | | `'python'` | |
| `code_input` | TEXT | NOT NULL | — | Raw code submitted |
| `review_data` | TEXT | | `'{}'` | JSON blob |
| `reviewed_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `sql_queries`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `query_input` | TEXT | NOT NULL | — | |
| `analysis_data` | TEXT | | `'{}'` | JSON blob |
| `analyzed_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

---

### 3.2 Migration-Added Tables (from model migration functions)

#### Table: `career_profiles`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL UNIQUE, FK→users(id) ON DELETE CASCADE | — | One row per user |
| `full_name` | TEXT | | `''` | |
| `phone` | TEXT | | `''` | |
| `location` | TEXT | | `''` | |
| `linkedin_url` | TEXT | | `''` | |
| `github_url` | TEXT | | `''` | |
| `portfolio_url` | TEXT | | `''` | |
| `preferred_role` | TEXT | | `''` | |
| `career_goal` | TEXT | | `''` | |
| `expected_salary` | TEXT | | `''` | Note: TEXT, not INTEGER |
| `preferred_location` | TEXT | | `''` | |
| `skills` | TEXT | | `'[]'` | JSON array |
| `top_skills` | TEXT | | `'[]'` | JSON array |
| `soft_skills` | TEXT | | `'[]'` | JSON array |
| `technologies` | TEXT | | `'[]'` | JSON array |
| `certifications` | TEXT | | `'[]'` | JSON array |
| `projects` | TEXT | | `'[]'` | JSON array of objects |
| `experience_summary` | TEXT | | `''` | |
| `education` | TEXT | | `''` | |
| `experience_years` | INTEGER | | `0` | |
| `domain` | TEXT | | `''` | |
| `seniority_level` | TEXT | | `'fresher'` | |
| `ats_score` | INTEGER | | `0` | |
| `profile_completeness` | INTEGER | | `0` | |
| `ai_readiness` | INTEGER | | `0` | |
| `resume_strength` | INTEGER | | `0` | |
| `full_name_is_manual` | INTEGER | | `0` | Boolean flag |
| `phone_is_manual` | INTEGER | | `0` | Boolean flag |
| `location_is_manual` | INTEGER | | `0` | Boolean flag |
| `linkedin_url_is_manual` | INTEGER | | `0` | Boolean flag |
| `github_url_is_manual` | INTEGER | | `0` | Boolean flag |
| `portfolio_url_is_manual` | INTEGER | | `0` | Boolean flag |
| `preferred_role_is_manual` | INTEGER | | `0` | Boolean flag |
| `career_goal_is_manual` | INTEGER | | `0` | Boolean flag |
| `expected_salary_is_manual` | INTEGER | | `0` | Boolean flag |
| `preferred_location_is_manual` | INTEGER | | `0` | Boolean flag |
| `last_resume_sync` | TIMESTAMP | | NULL | |
| `last_manual_update` | TIMESTAMP | | NULL | |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `resume_versions`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `role_target` | TEXT | NOT NULL | — | |
| `version_type` | TEXT | | `'manual_trigger'` | or `'daily_optimization'` |
| `content` | TEXT | | `'{}'` | JSON blob |
| `scores` | TEXT | | `'{}'` | JSON blob |
| `suggestions` | TEXT | | `'[]'` | JSON array |
| `template` | TEXT | | `'modern'` | |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `agent_profiles`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL UNIQUE, FK→users(id) ON DELETE CASCADE | — | |
| `skills` | TEXT | | `'[]'` | JSON array |
| `top_skills` | TEXT | | `'[]'` | JSON array |
| `projects` | TEXT | | `'[]'` | JSON array |
| `experience_years` | INTEGER | | `0` | |
| `education` | TEXT | | `''` | |
| `preferred_role` | TEXT | | `''` | |
| `preferred_location` | TEXT | | `''` | |
| `expected_salary` | TEXT | | `''` | |
| `technologies` | TEXT | | `'[]'` | JSON array |
| `soft_skills` | TEXT | | `'[]'` | JSON array |
| `career_goal` | TEXT | | `''` | |
| `experience_summary` | TEXT | | `''` | |
| `domain` | TEXT | | `''` | |
| `seniority_level` | TEXT | | `'fresher'` | |
| `search_queries` | TEXT | | `'[]'` | JSON array |
| `profile_score` | INTEGER | | `0` | |
| `last_synced` | TIMESTAMP | | NULL | |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `job_notifications`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `title` | TEXT | NOT NULL | — | |
| `company` | TEXT | NOT NULL | — | |
| `company_logo` | TEXT | | `''` | |
| `location` | TEXT | | `''` | |
| `salary_raw` | TEXT | | `''` | |
| `salary_min` | INTEGER | | `0` | |
| `salary_max` | INTEGER | | `0` | |
| `salary_estimate` | TEXT | | `''` | |
| `job_type` | TEXT | | `'Full-time'` | |
| `experience_required` | TEXT | | `''` | |
| `is_remote` | INTEGER | | `0` | Boolean 0/1 |
| `description` | TEXT | | `''` | |
| `apply_link` | TEXT | | `''` | |
| `source` | TEXT | | `''` | |
| `posted_date` | TEXT | | `''` | |
| `freshness` | TEXT | | `'recent'` | |
| `urgency` | TEXT | | `'normal'` | |
| `resume_match` | INTEGER | | `0` | 0–100 |
| `ats_score` | INTEGER | | `0` | |
| `shortlist_probability` | INTEGER | | `0` | |
| `interview_probability` | INTEGER | | `0` | |
| `competition_level` | TEXT | | `'medium'` | |
| `learning_time` | TEXT | | `''` | |
| `required_skills` | TEXT | | `'[]'` | JSON array |
| `missing_skills` | TEXT | | `'[]'` | JSON array |
| `matching_skills` | TEXT | | `'[]'` | JSON array |
| `ai_summary` | TEXT | | `''` | |
| `match_reason` | TEXT | | `''` | |
| `category` | TEXT | | `'medium_match'` | |
| `status` | TEXT | CHECK IN ('new','saved','applied','hidden','expired') | `'new'` | |
| `agent_run_id` | TEXT | | `''` | |
| `found_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

#### Table: `agent_runs`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — | |
| `run_id` | TEXT | NOT NULL | — | UUID string |
| `status` | TEXT | CHECK IN ('running','completed','failed') | `'running'` | |
| `jobs_searched` | INTEGER | | `0` | |
| `jobs_matched` | INTEGER | | `0` | |
| `queries_used` | TEXT | | `'[]'` | JSON array |
| `summary` | TEXT | | `''` | |
| `error` | TEXT | | `''` | |
| `started_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `completed_at` | TIMESTAMP | | NULL | |

#### Table: `admin_users`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `username` | TEXT | UNIQUE NOT NULL | — | |
| `email` | TEXT | UNIQUE NOT NULL | — | |
| `password_hash` | TEXT | NOT NULL | — | bcrypt hash |
| `role` | TEXT | | `'admin'` | |
| `is_active` | INTEGER | | `1` | Boolean 0/1 |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |
| `last_login` | TIMESTAMP | | NULL | |

#### Table: `admin_audit_logs`
| Column | Type | Constraints | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | — | |
| `admin_id` | INTEGER | | NULL | No FK constraint |
| `admin_username` | TEXT | | NULL | Denormalized for safety |
| `action` | TEXT | NOT NULL | — | e.g. `ADMIN_LOGIN`, `VIEW_USER` |
| `target` | TEXT | | NULL | |
| `ip_address` | TEXT | | NULL | |
| `created_at` | TIMESTAMP | | `CURRENT_TIMESTAMP` | |

---

### 3.3 Problem-Solving / Coding Platform Tables

#### Table: `problems`
| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | — | |
| `title` | TEXT NOT NULL | — | |
| `difficulty` | TEXT NOT NULL | — | 'Easy','Medium','Hard','Interview','Contest' |
| `topic` | TEXT NOT NULL | — | 'Arrays','Strings','DP', etc. |
| `subtopics` | TEXT | NULL | Comma-separated |
| `companies` | TEXT | NULL | Comma-separated company names |
| `constraints` | TEXT | NULL | |
| `description` | TEXT NOT NULL | — | |
| `examples` | TEXT | NULL | JSON array |
| `hints` | TEXT | NULL | JSON array |
| `editorial` | TEXT | NULL | |
| `starter_code` | TEXT | NULL | JSON dict (language→code) |
| `tags` | TEXT | NULL | Comma-separated |
| `premium` | INTEGER | `0` | Boolean 0/1 |
| `estimated_time` | INTEGER | `30` | Minutes |
| `created_at` | TEXT | `CURRENT_TIMESTAMP` | Note: TEXT type, not TIMESTAMP |

> [!WARNING]
> `problems.created_at` uses `TEXT` type (not `TIMESTAMP`), unlike other tables. This is inconsistent.

#### Table: `problem_templates`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `problem_id` | INTEGER, FK→problems(id) ON DELETE CASCADE | |
| `language` | TEXT NOT NULL | |
| `function_signature` | TEXT | |
| `return_type` | TEXT | |
| `starter_code` | TEXT | |
| `driver_template` | TEXT | |

#### Table: `problem_test_cases`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `problem_id` | INTEGER, FK→problems(id) ON DELETE CASCADE | |
| `input` | TEXT NOT NULL | |
| `expected_output` | TEXT NOT NULL | |
| `is_hidden` | INTEGER DEFAULT 0 | Boolean 0/1 |

#### Table: `problem_submissions`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `user_id` | INTEGER NOT NULL, FK→problems(id) ON DELETE CASCADE | ⚠️ FK references `problems`, not `users` |
| `problem_id` | INTEGER NOT NULL, FK→problems(id) ON DELETE CASCADE | |
| `code` | TEXT NOT NULL | |
| `language` | TEXT NOT NULL | |
| `status` | TEXT NOT NULL | 'Accepted','Wrong Answer','Time Limit', etc. |
| `execution_time` | INTEGER DEFAULT 0 | ms |
| `memory` | INTEGER DEFAULT 0 | KB |
| `coding_metrics` | TEXT | JSON blob |
| `created_at` | TEXT DEFAULT CURRENT_TIMESTAMP | TEXT type (inconsistent) |

> [!CAUTION]
> `problem_submissions.user_id` has `FOREIGN KEY (problem_id) REFERENCES problems(id)` — the FK **references `problems.id`**, not `users.id`. This appears to be a copy-paste bug. The FK constraint may not be enforced properly for the `user_id` column. Verify before migration.

#### Table: `user_problem_analytics`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `user_id` | INTEGER UNIQUE NOT NULL | No FK constraint declared |
| `streak` | INTEGER DEFAULT 0 | |
| `confidence_score` | INTEGER DEFAULT 50 | |
| `learning_velocity` | REAL DEFAULT 1.0 | Float |
| `last_submission_at` | TEXT | TEXT type |

#### Table: `user_topic_scores`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `user_id` | INTEGER NOT NULL | No FK constraint declared |
| `topic` | TEXT NOT NULL | |
| `score` | INTEGER DEFAULT 0 | |
| UNIQUE | (`user_id`, `topic`) | Composite unique |

#### Table: `ai_problem_feedback`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `submission_id` | INTEGER NOT NULL, FK→problem_submissions(id) ON DELETE CASCADE | |
| `correctness` | INTEGER | 0–100 |
| `time_complexity` | TEXT | |
| `space_complexity` | TEXT | |
| `naming_convention` | INTEGER | |
| `readability` | INTEGER | |
| `logic` | INTEGER | |
| `optimization` | INTEGER | |
| `code_style` | INTEGER | |
| `maintainability` | INTEGER | |
| `edge_cases` | TEXT | |
| `potential_bugs` | TEXT | |
| `interview_quality` | INTEGER | |
| `overall_score` | INTEGER | |
| `feedback_report` | TEXT | JSON blob |
| `created_at` | TEXT DEFAULT CURRENT_TIMESTAMP | TEXT type |

#### Table: `problem_hints_used`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `user_id` | INTEGER NOT NULL | No FK constraint |
| `problem_id` | INTEGER NOT NULL | No FK constraint |
| `hint_index` | INTEGER NOT NULL | 0–4 |
| `created_at` | TEXT DEFAULT CURRENT_TIMESTAMP | TEXT type |
| UNIQUE | (`user_id`, `problem_id`, `hint_index`) | Composite unique |

---

### 3.4 Indexes (verified from schema)

```sql
-- Core indexes
idx_resumes_user_id
idx_resume_analysis_user_id
idx_resume_analysis_resume_id
idx_chat_sessions_user_id
idx_chat_history_user_id
idx_chat_history_session_id
idx_chat_history_module
idx_job_history_user_id
idx_job_history_status
idx_interview_history_user_id
idx_learning_roadmaps_user_id
idx_projects_user_id
idx_code_reviews_user_id
idx_sql_queries_user_id

-- Migration-added indexes
idx_career_profiles_user_id
idx_resume_versions_user_id
idx_agent_profiles_user_id
idx_job_notifications_user_id
idx_job_notifications_status
idx_job_notifications_category
idx_job_notifications_resume_match
idx_agent_runs_user_id
```

---

### 3.5 SQLite-Specific Data Type Patterns (All Tables)

| Pattern | Tables Affected | Notes |
|---|---|---|
| **Boolean as INTEGER (0/1)** | users, resumes, career_profiles, chat_sessions, admin_users, settings, job_notifications, problem_test_cases, problems, problem_hints_used | No native BOOLEAN type |
| **JSON stored as TEXT** | resumes, resume_analysis, career_profiles, chat_history, job_history, job_notifications, agent_profiles, agent_runs, interview_history, learning_roadmaps, projects, code_reviews, sql_queries, resume_versions, problems, problem_submissions, ai_problem_feedback | ~30 JSON columns total |
| **TIMESTAMP as TEXT string** | All timestamp columns, plus `created_at` in problem tables uses `TEXT` explicitly | Python writes ISO 8601 strings via `datetime.now().isoformat()` |
| **REAL** | `user_problem_analytics.learning_velocity` | Only REAL/float column |
| **`sqlite_master` queries** | `db.py::table_exists()` | SQLite-only system table |
| **PRAGMA statements** | `db.py::get_connection()` | `foreign_keys`, `journal_mode` |
| **`CURRENT_TIMESTAMP`** | All tables | SQLite built-in |
| **`datetime('now', '-N days')`** | `admin_service.py` | SQLite date function |
| **`substr()`** | `admin_service.py` | SQLite string function |
| **`AUTOINCREMENT`** | All primary key columns | Slightly different behavior than PostgreSQL SERIAL |

---

## 4. Table-to-File / Function Usage Mapping

### 4.1 Master Mapping Table

| Table | Files Using It | Operations |
|---|---|---|
| `users` | `models/user.py`, `routes/auth.py`, `services/auth_service.py`, `services/admin_service.py`, `routes/admin.py`, `routes/profile.py`, `routes/dashboard.py` | SELECT, INSERT, UPDATE, DELETE |
| `resumes` | `models/resume.py`, `routes/resume.py`, `services/resume_service.py`, `services/admin_service.py`, `models/project.py` | SELECT, INSERT, UPDATE, DELETE |
| `resume_analysis` | `models/project.py` (ResumeAnalysisModel), `routes/resume.py`, `services/resume_service.py`, `routes/dashboard.py` | SELECT, INSERT |
| `chat_sessions` | `models/chat.py` (ChatSessionModel), `routes/chat.py`, `routes/profile.py` | SELECT, INSERT, UPDATE, DELETE |
| `chat_history` | `models/chat.py` (ChatModel), `routes/chat.py`, `routes/profile.py`, `services/admin_service.py` | SELECT, INSERT, DELETE |
| `job_history` | `models/job.py`, `routes/jobs.py`, `services/job_service.py`, `services/autonomous_agent.py`, `routes/dashboard.py` | SELECT, INSERT, UPDATE, DELETE |
| `interview_history` | `models/interview.py`, `routes/interview.py`, `services/interview_service.py`, `routes/dashboard.py`, `routes/profile.py` | SELECT, INSERT, UPDATE, DELETE |
| `learning_roadmaps` | `models/learning.py`, `routes/learning.py`, `services/learning_service.py`, `routes/dashboard.py` | SELECT, INSERT, UPDATE, DELETE |
| `projects` | `models/project.py` (ProjectModel), `routes/projects.py`, `services/project_service.py` | SELECT, INSERT, DELETE |
| `settings` | `models/project.py` (SettingsModel), `routes/profile.py`, `services/auth_service.py` | SELECT, INSERT, UPDATE |
| `code_reviews` | `models/project.py` (CodeReviewModel), `routes/code_review.py`, `services/code_service.py`, `services/admin_service.py` | SELECT, INSERT |
| `sql_queries` | `models/project.py` (SQLQueryModel), `routes/jobs.py` | SELECT, INSERT |
| `career_profiles` | `models/career_profile.py`, `services/career_profile_service.py`, `routes/profile.py`, `services/admin_service.py`, `routes/dashboard.py`, `routes/resume.py`, `services/resume_service.py` | SELECT, INSERT, UPDATE |
| `resume_versions` | `models/resume_version.py`, `services/resume_intelligence_service.py`, `routes/resume.py`, `services/autonomous_agent.py`, `services/admin_service.py` | SELECT, INSERT |
| `agent_profiles` | `models/job_notification.py` (AgentProfileModel), `routes/notifications.py`, `services/job_agent_service.py` | SELECT, INSERT, UPDATE |
| `job_notifications` | `models/job_notification.py` (JobNotificationModel), `routes/notifications.py`, `services/job_agent_service.py` | SELECT, INSERT, UPDATE, DELETE |
| `agent_runs` | `models/job_notification.py` (AgentRunModel), `routes/notifications.py`, `services/job_agent_service.py`, `services/admin_service.py` | SELECT, INSERT, UPDATE |
| `admin_users` | `models/admin.py`, `routes/admin.py`, `services/admin_service.py`, `routes/auth.py` | SELECT, INSERT, UPDATE |
| `admin_audit_logs` | `models/admin.py`, `routes/admin.py`, `services/admin_service.py` | SELECT, INSERT |
| `problems` | `models/problem.py`, `services/problem_service.py`, `routes/problem_solving.py`, `services/admin_service.py` | SELECT, INSERT |
| `problem_templates` | `models/problem.py`, `services/problem_service.py` | SELECT, INSERT |
| `problem_test_cases` | `models/problem.py`, `services/problem_service.py` | SELECT, INSERT |
| `problem_submissions` | `models/problem.py`, `routes/problem_solving.py`, `services/problem_service.py`, `services/admin_service.py` | SELECT, INSERT |
| `user_problem_analytics` | `models/problem.py`, `services/problem_service.py`, `services/admin_service.py` | SELECT, INSERT, UPDATE |
| `user_topic_scores` | `models/problem.py`, `services/problem_service.py`, `services/admin_service.py` | SELECT, INSERT, UPDATE (via INSERT OR REPLACE) |
| `ai_problem_feedback` | `models/problem.py`, `services/problem_service.py`, `services/admin_service.py` | SELECT, INSERT |
| `problem_hints_used` | `models/problem.py`, `services/problem_service.py`, `routes/problem_solving.py` | SELECT, INSERT |

### 4.2 Direct `db.py` Usage (bypassing model layer)

These files call `execute_one`, `execute_query`, or `execute_update` directly:

| File | Purpose |
|---|---|
| `routes/admin.py` | Toggle user `is_active` status directly |
| `routes/problem_solving.py` | Query `problem_submissions` directly |
| `services/admin_service.py` | Complex analytics queries across many tables |
| `services/auth_service.py` | Update `users.password_hash` directly |
| `services/problem_service.py` | Direct queries on coding tables |

---

## 5. Feature-by-Feature Database Dependencies

### 5.1 User Authentication
- **Tables:** `users`, `settings`
- **Registration:** Inserts into `users`, creates default row in `settings`, triggers `AutonomousAgent.on_login()`.
- **Login:** Reads `users` by username or email, verifies bcrypt hash, updates `last_login`, starts background agent tasks.
- **Admin Login:** Reads `admin_users` (separate table from `users`), updates `admin_users.last_login`, writes to `admin_audit_logs`.
- **Password Change:** Updates `users.password_hash`.
- **Session Data:** Stored in Flask server-side session (not database).

### 5.2 User Profile / Career DNA
- **Tables:** `users`, `career_profiles`, `settings`
- **Profile page:** Reads `users` + `career_profiles` + `settings`.
- **Manual update:** Updates `career_profiles` with `*_is_manual = 1` flags.
- **Resume sync:** AI-extracted data updates `career_profiles` fields (respecting manual flags).
- **Profile completeness:** Computed at write time and stored in `career_profiles.profile_completeness`.

### 5.3 Resume Upload and Storage
- **Tables:** `resumes`, `resume_analysis`, `career_profiles`
- **Upload:** Saves PDF to `static/uploads/`, inserts row to `resumes`, triggers career profile sync.
- **PDF text extraction:** Uses `PyPDF2` — text stored in `resumes.raw_text`.
- **Set primary:** Updates `resumes.is_primary`.
- **Delete:** Removes file from filesystem AND deletes `resumes` row (cascades to `resume_analysis`).

### 5.4 Resume Analysis
- **Tables:** `resume_analysis`, `resumes`, `career_profiles`
- **Run analysis:** AI processes `resumes.raw_text`, result saved to `resume_analysis`.
- **View analysis:** Reads `resume_analysis` for a given `resume_id`.
- **Dashboard:** Shows latest `resume_analysis.ats_score`.

### 5.5 AI Resume Intelligence (Resume Builder)
- **Tables:** `resume_versions`, `career_profiles`, `resumes`
- **Generate:** AI creates optimized resume, saved as new row in `resume_versions`.
- **Version history:** Lists all `resume_versions` for user, newest first.
- **Daily optimization:** Background task triggered on login/profile update.

### 5.6 AI Chat / Career Coach
- **Tables:** `chat_sessions`, `chat_history`
- **New session:** Creates row in `chat_sessions`, messages appended to `chat_history`.
- **History:** Reads `chat_history` for session, rendered as conversation.
- **Archive/Pin:** Updates `chat_sessions.is_archived` / `is_pinned`.
- **Delete session:** Deletes all `chat_history` for session, then deletes `chat_sessions` row.
- **Modules supported:** `career_coach`, `interview_prep`, `code_review`, `learning_path`, `job_coach`.

### 5.7 Job Search and History
- **Tables:** `job_history`
- **Background search:** AI job agent (`JobService`) finds jobs, bulk-inserts to `job_history`.
- **Dashboard stats:** Aggregates applied/saved/interviewing counts from `job_history`.
- **Status update:** Changes `job_history.status` field.

### 5.8 AI Job Notification Agent
- **Tables:** `agent_profiles`, `job_notifications`, `agent_runs`
- **Profile extraction:** Reads resume → AI extracts career data → saves to `agent_profiles`.
- **Run agent:** Creates `agent_runs` record, performs job search, bulk-inserts to `job_notifications`.
- **Status update:** User can save/apply/hide jobs in `job_notifications`.
- **Analytics:** Complex aggregations on `job_notifications` for dashboard charts.

### 5.9 Mock Interview
- **Tables:** `interview_history`
- **Start session:** Inserts row with `session_id` (UUID), role, difficulty.
- **Complete session:** Updates `questions`, `answers`, `evaluations`, all score fields, `feedback`.
- **History:** Lists completed interviews ordered by `conducted_at`.

### 5.10 Learning Roadmaps
- **Tables:** `learning_roadmaps`
- **Create:** AI generates roadmap; saved as JSON blobs in `roadmap_data`, `daily_plan`, `weekly_plan`, `resources`.
- **Progress:** Updates `progress_percent`.
- **Status:** Updates `status` (active/paused/completed/archived).

### 5.11 Problem Solving / Coding Platform
- **Tables:** `problems`, `problem_templates`, `problem_test_cases`, `problem_submissions`, `user_problem_analytics`, `user_topic_scores`, `ai_problem_feedback`, `problem_hints_used`
- **Problem browser:** Reads `problems` with filters.
- **Code submission:** Inserts to `problem_submissions`, runs code against `problem_test_cases`, AI feedback saved to `ai_problem_feedback`.
- **Hints:** Tracks used hints per user/problem in `problem_hints_used`.
- **Analytics:** Updates `user_problem_analytics` (streak, confidence), `user_topic_scores`.

### 5.12 Code Review (AI)
- **Tables:** `code_reviews`
- **Submit:** AI reviews code; result saved to `code_reviews`.
- **History:** Lists user's code review history.

### 5.13 SQL Coach
- **Tables:** `sql_queries`
- **Submit:** AI analyzes SQL query; result saved to `sql_queries`.

### 5.14 Project Generator
- **Tables:** `projects`, `career_profiles`
- **Generate:** AI generates project ideas based on career profile; saved to `projects`.
- **History:** Lists user's past generated projects.

### 5.15 Admin Panel
- **Tables:** `admin_users`, `admin_audit_logs`, `users`, `problem_submissions`, `problems`, `chat_history`, `code_reviews`, `agent_runs`, `resume_versions`, `career_profiles`, `settings`, `user_problem_analytics`, `user_topic_scores`
- **Dashboard metrics:** Complex COUNT aggregations across all major tables.
- **User management:** Paginated user list with inline stats (submissions, AI usage).
- **Submission monitoring:** Paginated list of `problem_submissions` with joins.
- **Problem analytics:** Aggregations on `problems` and `problem_submissions`.
- **AI analytics:** Counts from `chat_history`, `code_reviews`, `agent_runs`, `ai_problem_feedback`, `resume_versions`.
- **Audit logs:** Writes/reads `admin_audit_logs`.
- **Toggle user status:** Updates `users.is_active`.

---

## 6. Resume and File Storage Architecture

### 6.1 Upload Directory

```
CareerPilotAI/
  static/
    uploads/           ← All uploaded PDF files live here
      resume_abc123.pdf
      resume_xyz789.pdf
```

The path is **hardcoded** in `ResumeService`:
```python
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static", "uploads"
)
```

The `UPLOAD_FOLDER` env var is defined in config but **ResumeService ignores it** — it always resolves relative to `__file__`.

> [!CAUTION]
> On Render (or any ephemeral container platform), the `static/uploads/` directory is part of the container filesystem. **Files uploaded in production are lost on every re-deploy or container restart.** The database retains the `filename` but the physical file is gone.

### 6.2 Database Columns for File Metadata

| Table | Column | Description |
|---|---|---|
| `resumes` | `filename` | Server-generated secure filename (e.g., `resume_abc123.pdf`) |
| `resumes` | `original_name` | User's original uploaded filename |
| `resumes` | `file_size` | File size in bytes (INTEGER) |
| `resumes` | `raw_text` | Extracted PDF text (stored in DB, not filesystem) |
| `users` | `avatar_url` | Path string (e.g., `/static/images/default-avatar.png`) |

### 6.3 File Lifecycle

1. **Upload:** `ResumeService.upload_resume()` → saves PDF to `static/uploads/` → inserts `resumes` row.
2. **Retrieval/Serving:** Flask serves files via its static file handler from `static/uploads/`.
3. **Re-analysis:** `ResumeService.analyze_resume()` re-reads the physical file if `raw_text` is missing.
4. **Delete:** `routes/resume.py::delete()` removes physical file with `os.remove()` then calls `ResumeModel.delete()`.

### 6.4 File Storage Independence from Database

- The extracted `raw_text` is stored in the database (`resumes.raw_text`). AI analysis can re-run without the original file if `raw_text` is present.
- The physical PDF file is only needed for re-extraction if `raw_text` is empty/failed.
- To make file storage durable, upload storage must be migrated to a persistent service (e.g., AWS S3, Cloudinary, Render Persistent Disks) independently of the database migration.

---

## 7. Deployment and Data-Persistence Risks

### 7.1 Application Launch

The app is launched via `python app.py` (or gunicorn in production, based on startup logs):
```
startup_render.log / startup_render2.log suggest Render is used
```
No `Procfile`, `render.yaml`, or `gunicorn.conf.py` was found outside the `venv/`. This likely means the startup command is configured directly in the Render dashboard.

### 7.2 Database Location in Production

- `DATABASE_PATH` defaults to `"database.db"` (relative path).
- In production on Render, this resolves to the container's working directory.
- **Render's filesystem is ephemeral** — any file written at runtime is destroyed on re-deploy or instance restart.
- The SQLite file is therefore **not persisted between Render deployments**.

> [!CAUTION]
> **Every re-deploy on Render effectively wipes the SQLite database.** All user accounts, resumes, chat history, and problem submissions are permanently lost. This is the primary operational motivation for migrating to PostgreSQL.

### 7.3 Confirmed Live Data (from `database.db`)

The local database at `CareerPilotAI/database.db` was inspected read-only:

| Table | Row Count |
|---|---|
| `users` | 7 |
| `resumes` | 7 |
| `chat_history` | 163 |
| `interview_history` | 10 |
| `problems` | 105 |
| `problem_submissions` | 17 |
| `job_notifications` | 104 |
| `agent_runs` | 14 |
| `resume_versions` | 22 |
| `career_profiles` | 9 |
| `admin_users` | 1 |

### 7.4 Data Loss Risks Summary

| Risk | Severity | Detail |
|---|---|---|
| Re-deploy wipes SQLite on Render | 🔴 Critical | Ephemeral container filesystem |
| Multiple DB files in repo | 🟡 Medium | Confusion about which file is authoritative |
| PDF uploads lost on restart | 🔴 Critical | No persistent file storage |
| No migration tooling (Alembic) | 🟡 Medium | Schema changes done via raw `CREATE TABLE IF NOT EXISTS` |
| `DATABASE_URL` env var defined but never used | 🟡 Medium | Could mislead developers |

---

## 8. SQLite-to-PostgreSQL Compatibility Issues

### 8.1 SQL Syntax Issues

| Issue | SQLite | PostgreSQL Equivalent |
|---|---|---|
| `?` placeholders | `?` in all queries | `%s` (psycopg2) or `$1` (asyncpg) |
| `INTEGER PRIMARY KEY AUTOINCREMENT` | Native | `SERIAL` or `GENERATED ALWAYS AS IDENTITY` |
| `sqlite_master` table | `table_exists()` in `db.py` | `information_schema.tables` or `pg_catalog.pg_tables` |
| `PRAGMA foreign_keys = ON` | `get_connection()` | Not needed; FK enforced by default |
| `PRAGMA journal_mode = WAL` | `get_connection()` | Remove entirely |
| `datetime('now', '-30 days')` | `admin_service.py` (3 occurrences) | `NOW() - INTERVAL '30 days'` |
| `datetime('now', '-7 days')` | `admin_service.py` | `NOW() - INTERVAL '7 days'` |
| `substr(field, 1, 10)` | `admin_service.py` (2 occurrences) | `SUBSTRING(field FROM 1 FOR 10)` or `TO_CHAR(field::date, 'YYYY-MM-DD')` |
| `LOWER(col) = LOWER(?)` | `admin_service.py` | `LOWER(col) = LOWER(%s)` (same, works) |
| `CAST(x AS TEXT)` | `admin_service.py` | `CAST(x AS VARCHAR)` or `x::text` |
| `INSERT OR IGNORE` | `career_profile.py` | `INSERT ... ON CONFLICT DO NOTHING` |
| `INSERT OR REPLACE` | Possibly used | `INSERT ... ON CONFLICT DO UPDATE` |

### 8.2 Data Type Mapping

| SQLite Type | PostgreSQL Type | Notes |
|---|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` or `INTEGER GENERATED ALWAYS AS IDENTITY` | |
| `TEXT` | `TEXT` | Compatible; PostgreSQL has no size limit on TEXT |
| `INTEGER` (boolean 0/1) | `BOOLEAN` | App code uses `0`/`1` integers; queries like `is_active = 1` must become `is_active = TRUE` |
| `REAL` | `REAL` or `DOUBLE PRECISION` | 1 column: `learning_velocity` |
| `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | `TIMESTAMPTZ DEFAULT NOW()` | Consider timezone-aware |
| `TEXT DEFAULT CURRENT_TIMESTAMP` (problem tables) | `TIMESTAMPTZ DEFAULT NOW()` | Requires data conversion |
| JSON stored as TEXT | `JSONB` or `TEXT` | PostgreSQL JSONB enables indexing; TEXT also works |

### 8.3 Boolean Handling

All boolean columns (`is_active`, `is_primary`, `is_pinned`, `is_archived`, `is_remote`, etc.) are stored as `INTEGER` (0/1). Application code uses:

```python
# Current:
if user.get('is_active'):  # 1 is truthy
execute_update("... WHERE is_active = 1")
```

If migrated to PostgreSQL with native `BOOLEAN` columns, all `= 1` / `= 0` comparisons in raw SQL must change to `= TRUE` / `= FALSE`. Alternatively, keep `INTEGER` type in PostgreSQL (less clean but requires no query changes).

### 8.4 JSON Fields

~30 columns store JSON as TEXT strings. The application manually calls `json.dumps()` on write and `json.loads()` on read. These will continue to work with PostgreSQL `TEXT` type. If migrated to `JSONB`, no application-level `json.dumps/loads` changes are needed, and PostgreSQL enables JSON indexing and querying.

### 8.5 Timestamp Fields

All timestamps are written as Python ISO 8601 strings via `datetime.now().isoformat()` (e.g., `2026-10-23T17:00:00`). PostgreSQL accepts these strings. However, `CURRENT_TIMESTAMP` in defaults will be timezone-aware in PostgreSQL — this may cause minor inconsistencies with Python-written strings that lack timezone info.

### 8.6 `AUTOINCREMENT` vs `SERIAL`

SQLite `AUTOINCREMENT` guarantees IDs are never reused; PostgreSQL `SERIAL` / `IDENTITY` behave similarly. The app uses `cursor.lastrowid` after INSERT — `psycopg2` supports `RETURNING id` for this purpose.

### 8.7 Connection Handling

The entire `backend/database/db.py` is SQLite-specific. For PostgreSQL, it must be rewritten using `psycopg2` (sync) or SQLAlchemy (recommended for connection pooling on a production server).

---

## 9. Files Likely to Require Changes

### 9.1 Must Change (Core Database Layer)

| File | Changes Required |
|---|---|
| `backend/database/db.py` | Full rewrite: replace `sqlite3` with `psycopg2` or SQLAlchemy; change `?` → `%s`; remove PRAGMAs; update `table_exists()` to query `pg_catalog`; update `execute_insert()` to use `RETURNING id`; implement connection pooling |
| `backend/database/schema.py` | Replace all SQLite DDL with PostgreSQL DDL; `AUTOINCREMENT` → `SERIAL`; `TEXT` booleans → `BOOLEAN`; add `TIMESTAMPTZ`; remove `PRAGMA`; update `executescript` → psycopg2 `execute_batch` |
| `backend/database/startup.py` | Remove `os.path.exists(db_path)` file-check; adapt to PostgreSQL connection URL |
| `backend/config.py` | Add `DATABASE_URL` env var reading (currently ignored); remove `DATABASE_PATH` logic |

### 9.2 Must Change (Migration Functions)

| File | Changes Required |
|---|---|
| `backend/models/career_profile.py` | DDL in `CAREER_PROFILE_SCHEMA`: replace SQLite types; `migrate_career_profile_table()` rewrites |
| `backend/models/chat.py` | DDL in `migrate_chat_sessions_table()`: update to PG types |
| `backend/models/job_notification.py` | DDL in `NOTIFICATION_SCHEMA_SQL`: update to PG types |
| `backend/models/resume_version.py` | DDL in `RESUME_VERSIONS_SCHEMA`: update to PG types |
| `backend/models/problem.py` | All `CREATE TABLE` strings in `migrate_problem_solving_tables()`: update types |
| `backend/models/admin.py` | DDL in `migrate_admin_tables()`: update to PG types |

### 9.3 Must Change (SQLite-Specific SQL in Services)

| File | Line Range | Changes Required |
|---|---|---|
| `backend/services/admin_service.py` | Lines 67–69, 122–124 | `datetime('now', '-30 days')` → `NOW() - INTERVAL '30 days'` |
| `backend/services/admin_service.py` | Lines 149–153, 159–163 | `substr(created_at, 1, 10)` → `TO_CHAR(created_at, 'YYYY-MM-DD')` |
| `backend/services/admin_service.py` | Lines 268, 270–273 | `CAST(... AS TEXT)` → `... ::text` |
| `backend/models/career_profile.py` | `create_empty()` | `INSERT OR IGNORE` → `INSERT ... ON CONFLICT (user_id) DO NOTHING` |
| `backend/database/db.py` | `table_exists()` | `sqlite_master` query → `pg_catalog.pg_tables` |

### 9.4 Likely to Change (if boolean types changed)

All files that use `WHERE is_active = 1`, `WHERE is_primary = 1`, `WHERE is_pinned = 1`, etc. — about 8–10 files across `models/` and `services/`.

### 9.5 Will NOT Need Changes (unless boolean type changes)

Most model files with straightforward parameterized queries (`?` placeholder change only). After `db.py` is updated to translate `?` → `%s`, the higher-level model files may work without modification (depends on implementation approach).

---

## 10. Data Preservation and Migration Risks

### 10.1 User Records
- 7 users with bcrypt password hashes — hashes are portable and will work identically in PostgreSQL.
- `is_active` values (0/1) must be preserved; if using PostgreSQL `BOOLEAN`, convert to `TRUE`/`FALSE`.
- `avatar_url` values are local static paths — these remain valid after migration.

### 10.2 Resume Data
- 7 resume records with `raw_text` stored in DB — fully portable.
- PDF files in `static/uploads/` must be migrated separately (copy to new server or cloud storage).
- `parsed_data` JSON blobs are TEXT strings — portable.

### 10.3 Chat History
- 163 messages across sessions — large TEXT fields, fully portable.
- `session_id` is a UUID TEXT string used as a primary key — PostgreSQL supports TEXT PKs but `UUID` type is preferred; requires no value changes.

### 10.4 IDs and Foreign Keys
- All `INTEGER` IDs must be preserved exactly to maintain referential integrity.
- During migration, sequences/serials must be reset to `MAX(id) + 1` after data import.

### 10.5 JSON Fields
- All JSON TEXT columns — fully portable. No data transformation needed if keeping TEXT type.

### 10.6 Timestamps
- Mix of `CURRENT_TIMESTAMP` (UTC without timezone) and Python `datetime.now().isoformat()` (local time, no timezone).
- In PostgreSQL, if using `TIMESTAMPTZ`, all existing values should be re-interpreted as a known timezone. This requires coordination.

### 10.7 Admin User Seed
- `admin_users` has 1 row seeded by `AdminModel.seed_default_admin()`. This will be re-created on first startup if the table is empty — no data migration needed for this table if re-seeded.

---

## 11. Missing Information and Unresolved Questions

| # | Question | Impact |
|---|---|---|
| 1 | Is there a Render deployment configuration (dashboard settings, start command)? Not found in codebase. | Migration plan must include updating Render settings to point to PostgreSQL |
| 2 | Is `careerpilot.db` (root-level, 0 bytes) referenced anywhere? | Likely unused; confirm before migration |
| 3 | `problem_submissions.user_id` has FK reference to `problems(id)` — is this a bug or intentional? | Must clarify before creating PG FK constraints |
| 4 | `DATABASE_URL` is defined in `.env` files but never used. Was SQLAlchemy planned? | Determines whether to use `psycopg2` directly or SQLAlchemy |
| 5 | Are there any Celery, APScheduler, or cron jobs outside the ThreadPoolExecutor? | Background tasks must be verified to work with a pooled PG connection |
| 6 | The `test_ui.db` file — is it seeded separately? Does the test suite need updating? | Test migration scope |
| 7 | `UPLOAD_FOLDER` config is set but ResumeService ignores it. Is this intentional? | Must fix before migration and before solving file persistence |
| 8 | The `.env.production` file contains a plaintext API key. Should this be rotated before making the migration? | Security concern, not blocking migration |
| 9 | What is the expected PostgreSQL service (Render managed PG, Supabase, Neon, etc.)? | Affects connection URL format and SSL requirements |
| 10 | Will Alembic or manual SQL migrations be used going forward? | Long-term schema management strategy |

---

## 12. Recommended Migration Plan (Phased)

### Phase 1 — Preparation (No Code Changes)

1. Create a full backup of `database.db`.
2. Export all data using `sqlite3` `.dump` command to a `.sql` file.
3. Provision a PostgreSQL database (Render Managed PG, Supabase, or Neon recommended).
4. Obtain the PostgreSQL `DATABASE_URL` connection string.
5. Confirm the `problem_submissions.user_id` FK bug — fix in Phase 2 schema.
6. Decide on boolean strategy: keep `INTEGER` or migrate to `BOOLEAN`.
7. Decide on JSON strategy: keep `TEXT` or migrate to `JSONB`.

### Phase 2 — Database Layer Rewrite

1. Replace `backend/database/db.py` entirely:
   - Use `psycopg2` + connection pool (e.g., `psycopg2.pool.ThreadedConnectionPool`) or SQLAlchemy core.
   - Change all `?` placeholders to `%s`.
   - Replace `cursor.lastrowid` with `RETURNING id` clause.
   - Remove all `PRAGMA` statements.
   - Update `table_exists()` to use `information_schema.tables`.
2. Update `backend/config.py` to read `DATABASE_URL` from environment.
3. Update all schema DDL files (`schema.py` and all model migration functions) with PostgreSQL-compatible DDL.
4. Update `startup.py` to drop the SQLite file-existence check.

### Phase 3 — SQL Query Updates

1. Fix all `datetime('now', '-N days')` → `NOW() - INTERVAL 'N days'` in `admin_service.py`.
2. Fix all `substr()` → `SUBSTRING()` or `TO_CHAR()` in `admin_service.py`.
3. Fix `INSERT OR IGNORE` → `INSERT ... ON CONFLICT DO NOTHING` in `career_profile.py`.
4. If using `BOOLEAN` type: update all `WHERE col = 1` / `= 0` queries.

### Phase 4 — Data Migration

1. Transform SQLite dump:
   - Replace `?` parameter format as needed.
   - Convert boolean integers to `TRUE`/`FALSE` if using `BOOLEAN` type.
   - Convert `TEXT DEFAULT CURRENT_TIMESTAMP` columns in problem tables to proper timestamps.
2. Import data into PostgreSQL preserving all IDs.
3. Reset all sequences: `SELECT setval('table_id_seq', (SELECT MAX(id) FROM table))` for every table.
4. Verify row counts match between SQLite export and PostgreSQL import.

### Phase 5 — File Storage Migration

1. Copy all PDF files from `static/uploads/` to a persistent storage service (S3, Cloudinary, or Render Persistent Disk).
2. Update `ResumeService.UPLOAD_FOLDER` to use `Config.UPLOAD_FOLDER` from environment.
3. Update file serving URLs if using external storage.

### Phase 6 — Testing

1. Run all existing QA scripts (`qa_audit.py`, `qa_e2e_audit.py`, `qa_user_journey.py`) against a staging environment with PostgreSQL.
2. Manually test all 13 blueprints (auth, dashboard, resume, chat, learning, interview, jobs, code_review, projects, profile, admin, notifications, problem_solving).
3. Verify admin panel analytics queries return correct data.
4. Test concurrent requests (WAL was previously handling this in SQLite; verify PG connection pool handles it).

### Phase 7 — Deployment

1. Update Render environment variables: set `DATABASE_URL` to PostgreSQL connection string.
2. Remove `DATABASE_PATH` from environment (or keep as fallback).
3. Deploy and verify startup logs confirm PostgreSQL connection.
4. Monitor for errors in first 24 hours.

---

## 13. Verification Checklist

Use this checklist after migration to confirm all existing features work correctly.

### Authentication
- [ ] New user registration creates `users` + `settings` rows
- [ ] Login with username works
- [ ] Login with email works
- [ ] Wrong password returns error
- [ ] Inactive account blocks login
- [ ] Session persists across requests
- [ ] Logout clears session
- [ ] Admin login redirects to admin panel
- [ ] Password change works

### Dashboard
- [ ] Dashboard loads with correct user stats
- [ ] Resume ATS score displayed correctly
- [ ] Job stats shown (applied/saved/interviewing counts)
- [ ] Interview stats shown
- [ ] Recent chat sessions listed
- [ ] Learning progress bar shown
- [ ] Career DNA snapshot populated

### Resume
- [ ] PDF upload succeeds and saves to `resumes` table
- [ ] PDF text extracted and stored in `raw_text`
- [ ] Career profile auto-synced on upload
- [ ] Resume analysis runs and saves to `resume_analysis`
- [ ] Primary resume set/changed correctly
- [ ] Resume delete removes file and DB row
- [ ] Resume version generated and saved

### Career Profile
- [ ] Profile page loads with all fields
- [ ] Manual fields update and set `*_is_manual = 1`
- [ ] Manual fields not overwritten by resume sync
- [ ] Profile completeness calculated correctly
- [ ] Settings save and sync to career profile

### AI Chat
- [ ] New chat session creates `chat_sessions` row
- [ ] Messages saved to `chat_history`
- [ ] Session title auto-updated
- [ ] Pin/archive session works
- [ ] Delete session removes all messages
- [ ] Chat history listed in profile

### Job Search
- [ ] Background job search runs on login
- [ ] Jobs saved to `job_history`
- [ ] Job status update (save/apply) works
- [ ] Job stats correct on dashboard

### AI Job Notification Agent
- [ ] Agent run creates `agent_runs` row
- [ ] Job notifications saved to `job_notifications`
- [ ] Status update (save/apply/hide) works
- [ ] Dashboard stats aggregate correctly
- [ ] Missing skills summary works

### Mock Interview
- [ ] Interview created with UUID `session_id`
- [ ] Scores and feedback saved on completion
- [ ] Interview history listed
- [ ] Stats aggregated correctly

### Learning Roadmaps
- [ ] Roadmap created with JSON data
- [ ] Progress update works
- [ ] Status (active/paused) update works

### Problem Solving
- [ ] Problems list loads (105 problems)
- [ ] Code submission saved to `problem_submissions`
- [ ] Test cases evaluated correctly
- [ ] AI feedback saved to `ai_problem_feedback`
- [ ] Hints tracked in `problem_hints_used`
- [ ] Analytics updated (streak, confidence, topic scores)

### Code Review
- [ ] Code review submission saved
- [ ] Review history listed

### SQL Coach
- [ ] SQL query analysis saved
- [ ] Analysis history listed

### Project Generator
- [ ] Generated project saved to `projects`
- [ ] Project history listed

### Admin Panel
- [ ] Admin login works (separate from user login)
- [ ] Dashboard metrics all non-zero and accurate
- [ ] User list paginates correctly
- [ ] User detail page loads all stats
- [ ] Toggle user active/inactive works
- [ ] Submissions list loads and filters correctly
- [ ] Problem analytics loads
- [ ] AI analytics loads
- [ ] Audit logs recorded and listed
- [ ] Admin logout records audit log

---

> **Safety Confirmation:** This audit was performed in read-only mode. No project source files, database files, environment files, or configurations were modified. Only the audit report file (`DATABASE_MIGRATION_AUDIT.md`) was created. No SQL commands were executed against the live database beyond `SELECT`/`.tables` queries.
