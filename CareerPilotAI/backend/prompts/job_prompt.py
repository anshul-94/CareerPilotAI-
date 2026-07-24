"""
CareerPilot AI — Job Search & Matching Prompts
Reusable prompt templates for job search query generation and match analysis.
"""


def get_job_search_query_prompt(skills: list, role: str = "",
                                 location: str = "", experience: str = "") -> list[dict]:
    """Build prompt to generate optimal job search queries."""
    system_prompt = """You are a job search optimization expert. Generate effective search queries to find relevant job listings.

Respond in JSON:
{
    "queries": ["<search query>", ...],
    "job_boards": ["<recommended platform>", ...],
    "alternative_titles": ["<related job title>", ...]
}

Generate 3-5 targeted search queries combining skills, role, and preferences."""

    user_prompt = f"""Generate job search queries for:
Skills: {', '.join(skills[:10])}
Target Role: {role or 'Software Developer'}
Location: {location or 'India/Remote'}
Experience: {experience or 'Fresher'}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_job_match_prompt(resume_skills: list, job_description: str) -> list[dict]:
    """Build prompt for AI job matching analysis."""
    system_prompt = """You are an AI recruitment matching engine. Analyze how well a candidate matches a job posting.

Respond in JSON:
{
    "match_score": <0-100>,
    "matching_skills": ["<skill>", ...],
    "missing_skills": ["<skill>", ...],
    "strengths": ["<strength for this role>", ...],
    "weaknesses": ["<gap or concern>", ...],
    "improvement_suggestions": ["<actionable suggestion>", ...],
    "application_tips": ["<tip for applying>", ...]
}"""

    user_prompt = f"""Analyze match between:

Candidate Skills: {', '.join(resume_skills[:15])}

Job Description:
{job_description[:2000]}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_job_summary_prompt(jobs: list) -> list[dict]:
    """Build prompt to summarize and rank found jobs."""
    system_prompt = """Summarize and rank these job listings by relevance. Provide insights on the job market trends visible from these listings.

Respond in JSON:
{
    "summary": "<market overview>",
    "top_recommendations": [{"title": "<job>", "reason": "<why recommended>"}],
    "market_trends": ["<trend>", ...],
    "advice": "<job search advice>"
}"""

    jobs_text = "\n".join([f"- {j.get('title', '')} at {j.get('company', '')} ({j.get('location', '')})" 
                           for j in jobs[:10]])
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Jobs found:\n{jobs_text}"}
    ]
