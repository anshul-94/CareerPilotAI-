"""
CareerPilot AI — Learning Service
Handles learning roadmap generation and progress tracking.
"""

import json
from typing import Optional
from backend.services.ai_service import AIService
from backend.models.learning import LearningModel
from backend.utils.helpers import safe_json_loads


class LearningService:
    """Business logic for learning roadmap operations."""

    @staticmethod
    def generate_roadmap(user_id: int, target_role: str,
                         current_skills: list,
                         experience_level: str = "beginner") -> dict:
        """Generate and save a learning roadmap."""
        # Generate via AI
        roadmap_data = AIService.generate_roadmap(
            current_skills, target_role, experience_level
        )
        
        if "error" not in roadmap_data:
            # Save to database
            roadmap_id = LearningModel.create(
                user_id=user_id,
                target_role=target_role,
                current_skills=current_skills,
                roadmap_data=roadmap_data
            )
            
            # Update with detailed plans
            LearningModel.update_roadmap(
                roadmap_id,
                roadmap_data=roadmap_data,
                daily_plan=roadmap_data.get("daily_plan", {}),
                weekly_plan={"weeks": roadmap_data.get("weekly_plan", [])},
                resources={
                    "courses": roadmap_data.get("courses", []),
                    "books": roadmap_data.get("books", []),
                    "projects": roadmap_data.get("projects", [])
                }
            )
            
            roadmap_data["id"] = roadmap_id
        
        return roadmap_data

    @staticmethod
    def get_user_roadmaps(user_id: int) -> list[dict]:
        """Get all roadmaps for a user with parsed data."""
        roadmaps = LearningModel.get_by_user(user_id)
        for rm in roadmaps:
            rm['roadmap_data'] = safe_json_loads(rm.get('roadmap_data', '{}'), {})
            rm['current_skills'] = safe_json_loads(rm.get('current_skills', '[]'), [])
            rm['daily_plan'] = safe_json_loads(rm.get('daily_plan', '{}'), {})
            rm['weekly_plan'] = safe_json_loads(rm.get('weekly_plan', '{}'), {})
            rm['resources'] = safe_json_loads(rm.get('resources', '{}'), {})
        return roadmaps

    @staticmethod
    def get_active_roadmap(user_id: int) -> Optional[dict]:
        """Get the active roadmap for a user."""
        rm = LearningModel.get_active(user_id)
        if rm:
            rm['roadmap_data'] = safe_json_loads(rm.get('roadmap_data', '{}'), {})
            rm['current_skills'] = safe_json_loads(rm.get('current_skills', '[]'), [])
            rm['daily_plan'] = safe_json_loads(rm.get('daily_plan', '{}'), {})
            rm['weekly_plan'] = safe_json_loads(rm.get('weekly_plan', '{}'), {})
            rm['resources'] = safe_json_loads(rm.get('resources', '{}'), {})
        return rm

    @staticmethod
    def update_progress(roadmap_id: int, progress: int) -> bool:
        """Update roadmap progress."""
        return LearningModel.update_progress(roadmap_id, progress) > 0
