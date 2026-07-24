"""
CareerPilot AI — Project Service
Handles AI project generation operations.
"""

import json
from backend.services.ai_service import AIService
from backend.models.project import ProjectModel
from backend.utils.helpers import safe_json_loads


class ProjectService:
    """Business logic for project generation."""

    @staticmethod
    def generate(user_id: int, domain: str, skills: list,
                 experience_level: str = "beginner") -> dict:
        """Generate portfolio project ideas and save them."""
        result = AIService.generate_projects(domain, skills, experience_level)
        
        projects = result.get("projects", [])
        
        # Save each project
        for project in projects:
            try:
                ProjectModel.create(
                    user_id=user_id,
                    domain=domain,
                    skills=skills,
                    experience_level=experience_level,
                    project_data=project,
                    title=project.get("title", ""),
                    description=project.get("description", "")
                )
            except Exception as e:
                print(f"[WARN] Failed to save project: {str(e)}")
        
        return result

    @staticmethod
    def get_user_projects(user_id: int) -> list[dict]:
        """Get generated projects for a user."""
        projects = ProjectModel.get_by_user(user_id)
        for p in projects:
            p['project_data'] = safe_json_loads(p.get('project_data', '{}'), {})
            p['skills'] = safe_json_loads(p.get('skills', '[]'), [])
        return projects
