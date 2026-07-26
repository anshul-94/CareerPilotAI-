"""
CareerPilot AI — Career Profile Model
The single source of truth for a user's career DNA.

Priority rules enforced at service layer:
    1. Manual user edits   (field has *_is_manual = 1 → NEVER overwritten by resume)
    2. Resume AI extraction (fills empty/unmarked fields only)
    3. Empty / blank
"""

import json
from datetime import datetime
from typing import Optional
from backend.database.db import execute_query, execute_one, execute_insert, execute_update


# ─────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────

CAREER_PROFILE_SCHEMA = """
CREATE TABLE IF NOT EXISTS career_profiles (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                    INTEGER NOT NULL UNIQUE,

    -- Identity (Priority: manual > resume)
    full_name                  TEXT DEFAULT '',
    phone                      TEXT DEFAULT '',
    location                   TEXT DEFAULT '',
    linkedin_url               TEXT DEFAULT '',
    github_url                 TEXT DEFAULT '',
    portfolio_url              TEXT DEFAULT '',

    -- Career Goal (Priority: manual > resume)
    preferred_role             TEXT DEFAULT '',
    career_goal                TEXT DEFAULT '',
    expected_salary            TEXT DEFAULT '',
    preferred_location         TEXT DEFAULT '',

    -- Technical Profile (resume-extracted, no manual override)
    skills                     TEXT DEFAULT '[]',
    top_skills                 TEXT DEFAULT '[]',
    soft_skills                TEXT DEFAULT '[]',
    technologies               TEXT DEFAULT '[]',
    certifications             TEXT DEFAULT '[]',
    projects                   TEXT DEFAULT '[]',
    experience_summary         TEXT DEFAULT '',
    education                  TEXT DEFAULT '',
    experience_years           INTEGER DEFAULT 0,
    domain                     TEXT DEFAULT '',
    seniority_level            TEXT DEFAULT 'fresher',

    -- AI-Computed Scores
    ats_score                  INTEGER DEFAULT 0,
    profile_completeness       INTEGER DEFAULT 0,
    ai_readiness               INTEGER DEFAULT 0,
    resume_strength            INTEGER DEFAULT 0,

    -- Manual-override flags (1 = user set this manually, don't overwrite from resume)
    full_name_is_manual        INTEGER DEFAULT 0,
    phone_is_manual            INTEGER DEFAULT 0,
    location_is_manual         INTEGER DEFAULT 0,
    linkedin_url_is_manual     INTEGER DEFAULT 0,
    github_url_is_manual       INTEGER DEFAULT 0,
    portfolio_url_is_manual    INTEGER DEFAULT 0,
    preferred_role_is_manual   INTEGER DEFAULT 0,
    career_goal_is_manual      INTEGER DEFAULT 0,
    expected_salary_is_manual  INTEGER DEFAULT 0,
    preferred_location_is_manual INTEGER DEFAULT 0,

    -- Source tracking
    last_resume_sync           TIMESTAMP,
    last_manual_update         TIMESTAMP,
    created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_career_profiles_user_id ON career_profiles(user_id);
"""


def migrate_career_profile_table() -> None:
    """Run schema migration to add career_profiles table."""
    from backend.database.db import get_db_path
    import sqlite3
    path = get_db_path()
    with sqlite3.connect(path) as conn:
        conn.executescript(CAREER_PROFILE_SCHEMA)
        conn.commit()


# ─────────────────────────────────────────────────────────────
# JSON fields that need serialization
# ─────────────────────────────────────────────────────────────
_JSON_FIELDS = ["skills", "top_skills", "soft_skills", "technologies",
                "certifications", "projects"]

# Fields that can be set manually (have *_is_manual flags)
MANUAL_OVERRIDE_FIELDS = [
    "full_name", "phone", "location", "linkedin_url", "github_url",
    "portfolio_url", "preferred_role", "career_goal",
    "expected_salary", "preferred_location",
]


# ─────────────────────────────────────────────────────────────
# CareerProfileModel
# ─────────────────────────────────────────────────────────────

class CareerProfileModel:
    """CRUD for career_profiles — the canonical user career identity."""

    @staticmethod
    def get_by_user(user_id: int) -> Optional[dict]:
        """Fetch the career profile for a user. Returns parsed dict or None."""
        row = execute_one(
            "SELECT * FROM career_profiles WHERE user_id = ?", (user_id,)
        )
        return CareerProfileModel._parse(row) if row else None

    @staticmethod
    def create_empty(user_id: int) -> int:
        """Create an empty career profile stub for a new user."""
        return execute_insert(
            "INSERT OR IGNORE INTO career_profiles (user_id) VALUES (?)",
            (user_id,)
        )

    @staticmethod
    def update_from_resume(user_id: int, resume_data: dict) -> None:
        """
        Merge resume-extracted data into the profile.
        Respects manual override flags — never overwrites fields marked as manual.
        """
        existing = CareerProfileModel.get_by_user(user_id)
        if not existing:
            CareerProfileModel.create_empty(user_id)
            existing = CareerProfileModel.get_by_user(user_id) or {}

        now = datetime.now().isoformat()
        updates: dict[str, object] = {}

        # --- Apply override-protected fields only when NOT manual ---
        for field in MANUAL_OVERRIDE_FIELDS:
            if not existing.get(f"{field}_is_manual", 0):
                val = resume_data.get(field, "")
                if val:
                    updates[field] = val

        # --- Always update non-protected resume fields ---
        for field in ["skills", "top_skills", "soft_skills", "technologies",
                      "certifications", "projects", "experience_summary",
                      "education", "domain", "seniority_level",
                      "experience_years", "ats_score", "ai_readiness",
                      "resume_strength"]:
            val = resume_data.get(field)
            if val is not None and val != "" and val != [] and val != 0:
                updates[field] = val

        if not updates:
            return

        updates["last_resume_sync"] = now
        updates["updated_at"]       = now
        updates["profile_completeness"] = CareerProfileModel._compute_completeness(
            {**existing, **updates}
        )

        CareerProfileModel._apply_update(user_id, updates)

    @staticmethod
    def update_manual(user_id: int, manual_data: dict) -> None:
        """
        Apply manual user edits.
        Sets *_is_manual = 1 for every field the user explicitly provided.
        """
        existing = CareerProfileModel.get_by_user(user_id)
        if not existing:
            CareerProfileModel.create_empty(user_id)
            existing = {}

        now = datetime.now().isoformat()
        updates: dict[str, object] = {}

        for field, value in manual_data.items():
            if value is None:
                continue
            updates[field] = value
            if field in MANUAL_OVERRIDE_FIELDS:
                updates[f"{field}_is_manual"] = 1 if str(value).strip() else 0

        if not updates:
            return

        updates["last_manual_update"] = now
        updates["updated_at"]         = now
        updates["profile_completeness"] = CareerProfileModel._compute_completeness(
            {**existing, **updates}
        )

        CareerProfileModel._apply_update(user_id, updates)

    @staticmethod
    def _apply_update(user_id: int, updates: dict) -> None:
        """Execute an UPDATE with the given field-value dict."""
        fields, values = [], []
        for k, v in updates.items():
            if isinstance(v, (list, dict)):
                v = json.dumps(v)
            fields.append(f"{k} = ?")
            values.append(v)

        if not fields:
            return

        values.append(user_id)
        execute_update(
            f"UPDATE career_profiles SET {', '.join(fields)} WHERE user_id = ?",
            tuple(values)
        )

    @staticmethod
    def _compute_completeness(profile: dict) -> int:
        """
        Compute profile completeness percentage (0-100).
        Based on how many key fields are non-empty.
        """
        key_fields = [
            "full_name", "preferred_role", "skills", "location",
            "education", "experience_years", "career_goal",
            "linkedin_url", "github_url", "expected_salary",
        ]
        filled = 0
        for f in key_fields:
            val = profile.get(f)
            if val and val not in ("", "[]", [], 0):
                filled += 1
        return int((filled / len(key_fields)) * 100)

    @staticmethod
    def _parse(row: dict) -> dict:
        """Parse JSON fields in a profile row."""
        if not row:
            return {}
        for f in _JSON_FIELDS:
            val = row.get(f, "[]")
            if isinstance(val, str):
                try:
                    row[f] = json.loads(val)
                except Exception:
                    row[f] = []
        return row

    @staticmethod
    def get_prefill_for_module(user_id: int, module: str) -> dict:
        """
        Return a slim dict of prefill values for a specific module.
        Modules: 'jobs', 'learning', 'interview', 'agent', 'chat', 'project'
        """
        profile = CareerProfileModel.get_by_user(user_id)
        if not profile:
            return {}

        base = {
            "skills":          profile.get("skills", []),
            "top_skills":      profile.get("top_skills", []),
            "preferred_role":  profile.get("preferred_role", ""),
            "location":        profile.get("location") or profile.get("preferred_location", ""),
            "seniority_level": profile.get("seniority_level", "fresher"),
            "experience_years": profile.get("experience_years", 0),
            "domain":          profile.get("domain", ""),
        }

        if module == "jobs":
            base.update({
                "preferred_location": profile.get("preferred_location") or profile.get("location", ""),
                "expected_salary":    profile.get("expected_salary", ""),
                "technologies":       profile.get("technologies", []),
            })
        elif module == "learning":
            base.update({
                "target_role":        profile.get("preferred_role", ""),
                "current_skills":     profile.get("skills", []),
                "experience_level":   profile.get("seniority_level", "fresher"),
            })
        elif module == "interview":
            base.update({
                "role":               profile.get("preferred_role", "Software Developer"),
                "experience_years":   profile.get("experience_years", 0),
                "difficulty":         CareerProfileModel._seniority_to_difficulty(
                                          profile.get("seniority_level", "fresher")),
            })
        elif module == "agent":
            base.update({
                "search_queries":     CareerProfileModel._build_search_queries(profile),
                "technologies":       profile.get("technologies", []),
                "education":          profile.get("education", ""),
                "career_goal":        profile.get("career_goal", ""),
            })
        elif module == "project":
            base.update({
                "domain":       profile.get("domain", ""),
                "technologies": profile.get("technologies", []),
                "experience_level": profile.get("seniority_level", "beginner"),
            })

        return base

    @staticmethod
    def _seniority_to_difficulty(level: str) -> str:
        return {"fresher": "easy", "junior": "medium",
                "mid": "medium", "senior": "hard"}.get(level, "medium")

    @staticmethod
    def _build_search_queries(profile: dict) -> list[str]:
        role   = profile.get("preferred_role", "Software Developer")
        skills = profile.get("top_skills", profile.get("skills", []))[:4]
        loc    = profile.get("preferred_location") or profile.get("location", "")
        level  = profile.get("seniority_level", "fresher")

        queries = [f"{role} {level} hiring"]
        if skills:
            queries.append(f"{' '.join(skills[:3])} developer jobs {level}")
        if loc:
            queries.append(f"{role} jobs {loc}")
        return queries[:5]
