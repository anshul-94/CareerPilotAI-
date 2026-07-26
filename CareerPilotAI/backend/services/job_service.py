"""
CareerPilot AI — Job Service
Handles job searching, matching, and tracking.
"""

import json
from typing import Optional
from backend.ai.tavily_client import search_jobs, build_job_search_queries, search_multiple_queries
from backend.services.ai_service import AIService
from backend.ai.response_parser import parse_json_response
from backend.prompts.job_prompt import get_job_match_prompt
from backend.models.job import JobModel
from backend.models.resume import ResumeModel
from backend.utils.helpers import extract_skills_from_text, calculate_match_score, safe_json_loads


class JobService:
    """Business logic for job search and matching."""

    @staticmethod
    def search_for_user(user_id: int, custom_query: str = "",
                        role: str = "", location: str = "") -> dict:
        """
        Search for jobs based on user's resume and preferences.
        
        Returns:
            Dict with 'jobs', 'total', 'query_used'
        """
        # Get user's primary resume for skill extraction
        resume = ResumeModel.get_primary(user_id)
        skills = []
        
        if resume and resume.get('raw_text'):
            skills = extract_skills_from_text(resume['raw_text'])
        
        # Build search queries
        if custom_query:
            queries = [custom_query]
        else:
            queries = build_job_search_queries(
                skills=skills,
                role=role,
                location=location,
                experience="fresher"
            )
        
        # Execute search
        all_jobs = search_multiple_queries(queries, max_results_per_query=5)
        
        # Calculate match scores
        for job in all_jobs:
            if skills:
                job_skills = job.get("skills_required", [])
                if not job_skills:
                    # Extract skills from description
                    desc = job.get("description", "") + " " + job.get("title", "")
                    job_skills = extract_skills_from_text(desc)
                
                job["match_score"] = calculate_match_score(skills, job_skills) if job_skills else 65
            else:
                job["match_score"] = job.get("match_score", 50)
        
        # Sort by match score
        all_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        # Save to history
        if all_jobs:
            JobModel.bulk_create(user_id, all_jobs[:20])
        
        return {
            "jobs": all_jobs,
            "total": len(all_jobs),
            "queries_used": queries,
            "user_skills": skills
        }

    @staticmethod
    def get_match_analysis(user_id: int, job_id: int) -> dict:
        """Get detailed AI match analysis for a specific job."""
        job = JobModel.get_by_id(job_id)
        if not job:
            return {"error": "Job not found"}
        
        resume = ResumeModel.get_primary(user_id)
        if not resume:
            return {"error": "No resume found. Please upload your resume first."}
        
        skills = extract_skills_from_text(resume.get('raw_text', ''))
        description = job.get('description', '') or f"{job['title']} at {job['company']}"
        
        messages = get_job_match_prompt(skills, description)
        response = AIService.chat_completion(messages, temperature=0.3, json_mode=True)
        
        if response.get("success"):
            analysis = parse_json_response(response["content"], fallback_structure={
                "match_score": 50, "missing_skills": [], "matching_skills": [], "recommendation": "Analysis unavailable."
            })
            analysis["mock"] = False
            return analysis
        
        return {"error": "Analysis failed", "mock": False, "match_score": 0, "missing_skills": [], "matching_skills": []}

    @staticmethod
    def update_job_status(job_id: int, status: str) -> bool:
        """Update the status of a job entry."""
        valid_statuses = ['discovered', 'saved', 'applied', 'interviewing', 'rejected', 'offered']
        if status not in valid_statuses:
            return False
        return JobModel.update_status(job_id, status) > 0

    @staticmethod
    def get_user_jobs(user_id: int, status: str = None) -> list[dict]:
        """Get all jobs for a user with parsed match details."""
        jobs = JobModel.get_by_user(user_id, status)
        for job in jobs:
            if isinstance(job.get('match_details'), str):
                job['match_details'] = safe_json_loads(job['match_details'], {})
        return jobs

    @staticmethod
    def get_dashboard_stats(user_id: int) -> dict:
        """Get job-related dashboard statistics."""
        stats = JobModel.get_stats(user_id)
        return {
            "total_jobs": stats.get("total_jobs", 0),
            "applied": stats.get("applied", 0),
            "saved": stats.get("saved", 0),
            "interviewing": stats.get("interviewing", 0),
            "avg_match": round(stats.get("avg_match_score", 0) or 0)
        }
