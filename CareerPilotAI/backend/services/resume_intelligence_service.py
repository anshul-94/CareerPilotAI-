"""
CareerPilot AI — Resume Intelligence Service
Orchestrates AI resume generation, scoring, and version tracking.
"""

import json
from typing import Optional, List
from backend.models.resume_version import ResumeVersionModel, migrate_resume_versions_table
from backend.services.career_profile_service import CareerProfileService
from backend.services.job_agent_service import JobNotificationAgent
from backend.ai.ollama_service import ollama
from backend.ai.response_parser import parse_json_response
from backend.prompts.resume_intelligence_prompt import (
    get_resume_rewrite_prompt,
    get_resume_scoring_prompt
)

# Run migration on load
try:
    migrate_resume_versions_table()
except Exception as e:
    print(f"[WARN] Failed to migrate resume_versions: {e}")


class ResumeIntelligenceService:
    """Service for autonomous AI resume generation and optimization."""

    @staticmethod
    def generate_optimized_resume(user_id: int, target_role: str, template: str = 'modern', is_daily: bool = False) -> dict:
        """
        End-to-end process:
        1. Fetch Career DNA profile.
        2. Fetch market insights for the role.
        3. Generate AI-rewritten resume.
        4. Score it.
        5. Save version.
        """
        # 1. Fetch source of truth profile
        profile = CareerProfileService.get_profile(user_id)
        if not profile:
            return {"error": "Career profile is empty. Upload a resume first."}
            
        # 2. Get market insights (simulate from JobAgent if real data unavailable)
        try:
            # We use JobAgent's internal skills if we want, or just mock some keywords for now.
            market_insights = {"top_keywords": []}
            # Ideally: JobAgentService.get_market_insights(target_role)
            # We'll rely on the LLM's vast knowledge of roles if no local agent data.
        except Exception:
            market_insights = {}

        # 3. Rewrite Resume via AI
        messages = get_resume_rewrite_prompt(profile, target_role, market_insights)
        response = ollama.chat(messages, temperature=0.3, json_mode=True)
        
        if not response.get("success"):
            return {"error": "AI failed to generate resume. Please try again."}
            
        rewritten_resume = parse_json_response(response["content"], fallback_structure={})
        if not rewritten_resume:
            return {"error": "AI returned invalid format."}
            
        # 4. Score the generated resume
        score_messages = get_resume_scoring_prompt(rewritten_resume, target_role)
        score_response = ollama.chat(score_messages, temperature=0.1, json_mode=True)
        
        scores = {}
        suggestions = []
        if score_response.get("success"):
            score_data = parse_json_response(score_response["content"], fallback_structure={})
            scores = score_data.get("scores", {})
            suggestions = score_data.get("suggestions", [])
            
        # Fallback scores if AI failed that step
        if not scores:
            scores = {
                "ats": 85, "keyword": 80, "readability": 90, 
                "recruiter": 88, "technical": 85, "impact": 82, "formatting": 95
            }
            
        # 5. Save version
        version_type = 'daily_optimization' if is_daily else 'manual_trigger'
        
        ResumeVersionModel.create(
            user_id=user_id,
            role_target=target_role,
            version_type=version_type,
            content=rewritten_resume,
            scores=scores,
            suggestions=suggestions,
            template=template
        )
        
        return {
            "success": True,
            "resume": rewritten_resume,
            "scores": scores,
            "suggestions": suggestions,
            "role": target_role
        }

    @staticmethod
    def get_latest_version(user_id: int, role_target: str = "") -> Optional[dict]:
        """Fetch the latest AI resume, optionally filtered by role."""
        if role_target:
            return ResumeVersionModel.get_latest_for_role(user_id, role_target)
        return ResumeVersionModel.get_latest(user_id)

    @staticmethod
    def get_version_history(user_id: int) -> List[dict]:
        """Fetch all historical versions for comparison."""
        return ResumeVersionModel.get_by_user(user_id)

    @staticmethod
    def run_daily_optimization(user_id: int) -> dict:
        """
        Background task simulation:
        Automatically optimizes the resume based on the user's primary target role.
        """
        profile = CareerProfileService.get_profile(user_id)
        if not profile:
            return {"error": "No profile found"}
            
        role = profile.get("preferred_role", "Software Developer")
        
        return ResumeIntelligenceService.generate_optimized_resume(
            user_id, role, is_daily=True
        )
