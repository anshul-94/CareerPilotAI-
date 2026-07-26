"""
CareerPilot AI — Career Profile Service
Single source of truth for user career data.

Design principles:
  - get_profile() is called by ALL modules — never read from UserModel or
    SettingsModel directly for career/preference data.
  - sync_from_resume() auto-runs after every upload — respects manual flags.
  - Every module calls get_prefill_for_module(user_id, module_name) to get
    pre-populated form data without asking the user again.
"""

from __future__ import annotations

import json
from typing import Optional

from backend.models.career_profile import CareerProfileModel, migrate_career_profile_table
from backend.models.user import UserModel
from backend.models.project import SettingsModel
from backend.services.ai_service import AIService
from backend.ai.response_parser import parse_json_response
from backend.prompts.profile_extraction_prompt import (
    get_deep_profile_extraction_prompt,
    get_career_health_prompt,
)


# ─────────────────────────────────────────────────────────────
# Public Service Class
# ─────────────────────────────────────────────────────────────

class CareerProfileService:
    """
    Orchestrates the Smart User Profile System.

    Priority rule:
        Manual > Resume-Extracted > Empty
    """

    # ── Main getter — the single source of truth ───────────────────────────────
    @staticmethod
    def get_profile(user_id: int) -> dict:
        """
        Return the merged Career DNA profile for a user.
        Falls back to combining UserModel + SettingsModel data
        if no career_profile row exists yet.
        """
        profile = CareerProfileModel.get_by_user(user_id)
        if not profile:
            # First-time: bootstrap from existing user + settings data
            profile = CareerProfileService._bootstrap_profile(user_id)

        return profile or {}

    @staticmethod
    def _bootstrap_profile(user_id: int) -> dict:
        """
        Build a minimal profile from existing users/settings tables
        for first-time users or users who haven't uploaded a resume.
        """
        CareerProfileModel.create_empty(user_id)
        user     = UserModel.get_by_id(user_id) or {}
        settings = SettingsModel.get_by_user(user_id) or {}

        seed = {}
        # Pull from users table
        for field in ["full_name", "phone", "location",
                      "linkedin_url", "github_url", "portfolio_url"]:
            val = user.get(field) or user.get(field.replace("_url", "_url"), "")
            if val:
                seed[field] = val
                seed[f"{field}_is_manual"] = 1

        # Pull from settings table
        if settings.get("preferred_role"):
            seed["preferred_role"]          = settings["preferred_role"]
            seed["preferred_role_is_manual"]= 1
        if settings.get("preferred_location"):
            seed["preferred_location"]          = settings["preferred_location"]
            seed["preferred_location_is_manual"]= 1
        if settings.get("expected_salary"):
            seed["expected_salary"]          = str(settings["expected_salary"])
            seed["expected_salary_is_manual"]= 1
        if settings.get("experience_level"):
            seed["seniority_level"] = settings["experience_level"]

        if seed:
            CareerProfileModel.update_manual(user_id, seed)

        return CareerProfileModel.get_by_user(user_id)

    # ── Resume sync — called automatically after every upload ─────────────────
    @staticmethod
    def sync_from_resume(user_id: int, resume_text: str) -> dict:
        """
        Run deep AI extraction on resume_text and merge into career_profiles.
        Respects manual override flags.
        Returns the final merged profile.
        """
        if not resume_text or len(resume_text.strip()) < 50:
            return CareerProfileService.get_profile(user_id)

        # 1. LLM extraction
        messages = get_deep_profile_extraction_prompt(resume_text)
        response = AIService.chat_completion(messages, temperature=0.1, json_mode=True)

        extracted: dict = {}
        if response.get("success"):
            extracted = parse_json_response(
                response["content"],
                fallback_structure={}
            )
        else:
            # Deterministic fallback: basic text-based extraction
            extracted = CareerProfileService._deterministic_extract(resume_text)

        if not extracted:
            return CareerProfileService.get_profile(user_id)

        # 2. Also sync with UserModel (full_name, phone, linkedin, github, portfolio)
        user_fields = {}
        for field in ["full_name", "phone", "linkedin_url", "github_url", "portfolio_url"]:
            val = extracted.get(field, "")
            if val:
                user_fields[field] = val
        if user_fields:
            try:
                UserModel.update_profile(user_id, **user_fields)
            except Exception:
                pass

        # 3. Merge into career_profiles (priority rules respected in model)
        CareerProfileModel.update_from_resume(user_id, extracted)

        # 4. Compute and store career health
        try:
            CareerProfileService._update_career_health(user_id)
        except Exception as _e:
            print(f"[WARN] Career health update: {_e}")

        return CareerProfileService.get_profile(user_id)

    @staticmethod
    def _update_career_health(user_id: int) -> None:
        """Run LLM career health assessment and store scores."""
        profile = CareerProfileModel.get_by_user(user_id)
        if not profile:
            return

        messages = get_career_health_prompt(profile)
        response = AIService.chat_completion(messages, temperature=0.2, json_mode=True)

        if not response.get("success"):
            return

        health = parse_json_response(response["content"], fallback_structure={})
        if not health:
            return

        updates = {}
        if health.get("ai_readiness"):
            updates["ai_readiness"] = health["ai_readiness"]
        if health.get("career_health_score"):
            updates["resume_strength"] = health["career_health_score"]

        if updates:
            CareerProfileModel.update_manual(user_id, updates)

        # Store full health data in career_profiles as JSON extension
        # (we reuse career_goal field for the insight text if empty)
        insight = health.get("career_insight", "")
        profile = CareerProfileModel.get_by_user(user_id) or {}
        if insight and not profile.get("career_goal_is_manual"):
            CareerProfileModel._apply_update(user_id, {"career_goal": insight})

    # ── Manual profile save (from profile page form) ───────────────────────────
    @staticmethod
    def save_manual(user_id: int, form_data: dict) -> dict:
        """
        Save manually entered profile data.
        Marks all provided fields as manual (won't be overwritten by next resume upload).
        """
        # Filter only known fields
        allowed = [
            "full_name", "phone", "location", "linkedin_url", "github_url",
            "portfolio_url", "preferred_role", "career_goal",
            "expected_salary", "preferred_location", "seniority_level",
            "experience_years", "domain",
        ]
        clean = {k: v for k, v in form_data.items()
                 if k in allowed and v is not None}

        CareerProfileModel.update_manual(user_id, clean)

        # Mirror identity fields back to users table
        user_fields = {k: v for k, v in clean.items()
                       if k in ["full_name", "phone", "location",
                                 "linkedin_url", "github_url", "portfolio_url"]}
        if user_fields:
            try:
                UserModel.update_profile(user_id, **user_fields)
            except Exception:
                pass

        # Mirror career settings to settings table
        try:
            settings_data = {}
            if clean.get("preferred_role"):
                settings_data["preferred_role"] = clean["preferred_role"]
            if clean.get("preferred_location"):
                settings_data["preferred_location"] = clean.get("preferred_location", "")
            if clean.get("seniority_level"):
                settings_data["experience_level"] = clean["seniority_level"]
            if settings_data:
                SettingsModel.create_or_update(user_id, **settings_data)
        except Exception:
            pass

        return CareerProfileService.get_profile(user_id)

    # ── Per-module prefill builder ─────────────────────────────────────────────
    @staticmethod
    def get_prefill_for_module(user_id: int, module: str) -> dict:
        """
        Return structured prefill data for a specific module.
        Called by routes to auto-populate search fields/forms.
        """
        return CareerProfileModel.get_prefill_for_module(user_id, module)

    # ── Career Snapshot for Dashboard / Profile page ───────────────────────────
    @staticmethod
    def get_career_snapshot(user_id: int) -> dict:
        """
        Return a rich Career Snapshot object for the Dashboard / Profile page.
        """
        profile  = CareerProfileService.get_profile(user_id)
        user     = UserModel.get_by_id(user_id) or {}

        # Latest resume analysis for ATS score
        from backend.services.resume_service import ResumeService
        analysis = ResumeService.get_latest_analysis(user_id)

        ats_score  = analysis.get("ats_score", 0) if analysis else profile.get("ats_score", 0)
        strong     = analysis.get("strong_skills", [])[:5] if analysis else []
        missing    = analysis.get("missing_keywords", [])[:5] if analysis else []
        last_scan  = analysis.get("created_at", "") if analysis else ""

        completeness = profile.get("profile_completeness", 0)

        return {
            "full_name":         user.get("full_name") or profile.get("full_name", ""),
            "preferred_role":    profile.get("preferred_role", ""),
            "domain":            profile.get("domain", ""),
            "seniority_level":   profile.get("seniority_level", "fresher"),
            "experience_years":  profile.get("experience_years", 0),
            "top_skills":        profile.get("top_skills", [])[:8],
            "skills":            profile.get("skills", []),
            "soft_skills":       profile.get("soft_skills", [])[:5],
            "technologies":      profile.get("technologies", []),
            "certifications":    profile.get("certifications", []),
            "strong_skills":     strong,
            "missing_skills":    missing,
            "ats_score":         ats_score,
            "ai_readiness":      profile.get("ai_readiness", 0),
            "resume_strength":   profile.get("resume_strength", 0),
            "profile_completeness": completeness,
            "expected_salary":   profile.get("expected_salary", ""),
            "preferred_location":profile.get("preferred_location") or profile.get("location", ""),
            "career_goal":       profile.get("career_goal", ""),
            "last_resume_scan":  last_scan,
            "linkedin_url":      profile.get("linkedin_url", ""),
            "github_url":        profile.get("github_url", ""),
            "portfolio_url":     profile.get("portfolio_url", ""),
            "has_profile":       bool(profile.get("preferred_role") or profile.get("skills")),
        }

    # ── Deterministic fallback extraction (no AI required) ────────────────────
    @staticmethod
    def _deterministic_extract(text: str) -> dict:
        """
        Regex/heuristic-based extraction when LLM is unavailable.
        Returns a best-effort profile dict from raw text.
        """
        import re

        result = {}

        # Email
        m = re.search(r'[\w.+-]+@[\w.-]+\.\w+', text)
        if m: result["email"] = m.group()

        # Phone
        m = re.search(r'[\+]?[\d\s\-\(\)]{10,14}', text)
        if m: result["phone"] = m.group().strip()

        # LinkedIn
        m = re.search(r'linkedin\.com/in/[\w-]+', text)
        if m: result["linkedin_url"] = "https://" + m.group()

        # GitHub
        m = re.search(r'github\.com/[\w-]+', text)
        if m: result["github_url"] = "https://" + m.group()

        # Skills (from common tech keyword matching)
        from backend.utils.helpers import extract_skills_from_text
        skills = extract_skills_from_text(text)
        if skills:
            result["skills"]     = skills
            result["top_skills"] = skills[:5]

        # Experience years
        m = re.search(r'(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)', text, re.I)
        if m: result["experience_years"] = int(m.group(1))

        return result
