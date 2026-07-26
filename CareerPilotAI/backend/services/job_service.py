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
import logging

logger = logging.getLogger("careerpilot.job_service")


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
        import time
        start_time = time.time()
        
        resume = ResumeModel.get_primary(user_id)
        skills = []
        resume_loaded = "Yes" if resume else "No"
        
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
        
        # Execute search with error handling
        try:
            all_jobs = search_multiple_queries(queries, max_results_per_query=5)
        except Exception as e:
            logger.error(f"[JobService] search_multiple_queries completely failed for User {user_id}: {e}")
            return {
                "error": str(e),
                "jobs": [],
                "total": 0,
                "queries_used": queries,
                "user_skills": skills
            }
        
        retrieved_count = len(all_jobs)
        
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
        
        saved_count = 0
        # Save to history
        if all_jobs:
            saved_count = len(all_jobs[:20])
            JobModel.bulk_create(user_id, all_jobs[:20])
            
        duration = int((time.time() - start_time) * 1000)
        
        from backend.utils.logger import jobs_logger
        import os
        job_provider = os.getenv('JOB_PROVIDER', 'tavily')
        
        log_msg = f"""
========== JOB SEARCH ==========
User            : {user_id}
Career DNA      : Loaded
Resume Loaded   : {resume_loaded}
Role            : {role or 'Not specified'}
Skills          : {len(skills)} extracted
Location        : {location or 'Not specified'}
Generated Query : {', '.join(queries)}
Provider        : {job_provider}
Jobs Retrieved  : {retrieved_count}
Jobs Filtered   : {len(all_jobs)}
Jobs Saved      : {saved_count}
Completed in    : {duration} ms
================================"""
        jobs_logger.info(log_msg)
        
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
    def get_user_jobs(
        user_id: int, 
        limit: int = None,
        offset: int = 0,
        order_by: str = "created_at",
        descending: bool = True,
        status: str = None
    ) -> list[dict]:
        """Get all jobs for a user with parsed match details."""
        import time
        from backend.utils.logger import jobs_logger
        
        start = time.time()
        
        try:
            if limit is not None:
                limit = int(limit)
            offset = int(offset)
            
            jobs = JobModel.get_by_user(
                user_id=user_id, 
                status=status, 
                limit=limit, 
                offset=offset, 
                order_by=order_by, 
                descending=descending
            )
            
            for job in jobs:
                if isinstance(job.get('match_details'), str):
                    job['match_details'] = safe_json_loads(job['match_details'], {})
            
            duration = int((time.time() - start) * 1000)
            log_msg = f"\n========== JOB CACHE ==========\nUser            : {user_id}\nLimit           : {limit if limit is not None else 'All'}\nRows Returned   : {len(jobs)}\nExecution Time  : {duration} ms\n==============================="
            jobs_logger.info(log_msg)
            
            return jobs
            
        except Exception as e:
            jobs_logger.warning(f"Failed to fetch user jobs for User {user_id}: {e}")
            return []

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
