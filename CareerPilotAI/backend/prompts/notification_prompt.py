"""
CareerPilot AI — AI Job Notification Agent Prompts
Reusable LLM prompts for:
  - Career profile extraction from resume text
  - Intelligent job scoring (match%, ATS%, shortlist%, interview%)
  - Daily AI job market summary generation
"""

from typing import Optional


# ─────────────────────────────────────────────────────────────
# 1. Resume → AI Career Profile Extraction
# ─────────────────────────────────────────────────────────────

def get_profile_extraction_prompt(resume_text: str) -> list[dict]:
    """
    Extract a structured AI career profile from raw resume text.
    Returns a messages list for the LLM chat API.
    """
    system = """You are an expert AI Career Intelligence Engine.
Your task is to deeply analyze a resume and extract a rich, structured career profile.

Return ONLY valid JSON with exactly this structure:
{
    "skills": ["<skill1>", "<skill2>", ...],
    "top_skills": ["<top 5 skills that stand out>"],
    "technologies": ["<technology1>", ...],
    "soft_skills": ["<soft skill1>", ...],
    "projects": ["<project1 summary>", "<project2 summary>"],
    "experience_years": <integer 0-20>,
    "education": "<degree + institution + year>",
    "preferred_role": "<most likely target job title>",
    "preferred_location": "<city or 'Remote' or 'Open to all'>",
    "expected_salary": "<salary range like '6-10 LPA' or 'Not mentioned'>",
    "career_goal": "<one sentence career objective>",
    "experience_summary": "<2 sentence experience summary>",
    "domain": "<primary domain e.g. Machine Learning, Web Development, Data Engineering>",
    "seniority_level": "<one of: fresher, junior, mid, senior>",
    "profile_score": <integer 0-100 based on resume completeness and strength>,
    "search_queries": [
        "<query1 for job search like 'Python Machine Learning Developer Fresher'>",
        "<query2>",
        "<query3>",
        "<query4>",
        "<query5>"
    ]
}

Rules:
- Extract ONLY what is present in the resume, infer logically.
- search_queries should be realistic job board search strings.
- profile_score: 0-40 weak, 41-70 average, 71-100 strong.
- skills list should be comprehensive (15-30 skills).
- top_skills should be the candidate's strongest 5.
"""

    user = f"""Analyze this resume and extract the career profile:

---RESUME START---
{resume_text[:4000]}
---RESUME END---

Return ONLY the JSON object, no explanation."""

    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user}
    ]


# ─────────────────────────────────────────────────────────────
# 2. Job Scoring — AI Match Intelligence
# ─────────────────────────────────────────────────────────────

def get_job_scoring_prompt(
    profile: dict,
    job_title: str,
    job_description: str,
    company: str,
    location: str,
    salary: str,
    source: str
) -> list[dict]:
    """
    Score a single job against a candidate's AI profile.
    Returns a messages list for the LLM chat API.
    """
    system = """You are an elite AI Recruitment Intelligence Engine.
You analyze job postings against candidate profiles with the precision of a senior recruiter at a top tech company.

Your scoring is data-driven and NOT random:
- Resume Match %: Skill overlap (weighted by skill importance and count)
- ATS Score %: How well the resume keywords match ATS requirements in the JD
- Shortlist Probability %: Composite score considering match, experience, education, projects
- Interview Probability %: Based on shortlist% adjusted for competition level and role demand

Return ONLY valid JSON:
{
    "resume_match": <integer 0-100>,
    "ats_score": <integer 0-100>,
    "shortlist_probability": <integer 0-100>,
    "interview_probability": <integer 0-100>,
    "competition_level": "<low|medium|high|very_high>",
    "salary_estimate": "<estimated salary like '8-12 LPA' or 'Not disclosed'>",
    "salary_min": <integer in LPA or 0>,
    "salary_max": <integer in LPA or 0>,
    "required_skills": ["<skill1>", "<skill2>", ...],
    "missing_skills": ["<skill candidate lacks>", ...],
    "matching_skills": ["<skill candidate has that matches>", ...],
    "ai_summary": "<2 sentence AI summary of this job opportunity for this candidate>",
    "match_reason": "<1 specific reason why this is a good match, mentioning actual skills>",
    "freshness": "<today|this_week|recent|old>",
    "urgency": "<urgent|normal|low>",
    "learning_time": "<how long to close skill gaps, e.g. '2-3 weeks for Docker'>",
    "is_remote": <true|false>
}

Scoring guidelines:
- resume_match 90-100: >85% skill overlap
- resume_match 70-89: 60-85% skill overlap  
- resume_match 50-69: 40-60% skill overlap
- resume_match < 50: < 40% skill overlap
- shortlist_probability should be 10-20 points lower than resume_match (realistic recruiter behavior)
- interview_probability = shortlist_probability * 0.6 (most shortlisted don't get interviews)
"""

    candidate_summary = f"""
Skills: {', '.join(profile.get('skills', [])[:20])}
Top Skills: {', '.join(profile.get('top_skills', []))}
Experience: {profile.get('experience_years', 0)} years
Domain: {profile.get('domain', 'Technology')}
Seniority: {profile.get('seniority_level', 'fresher')}
Education: {profile.get('education', 'Not specified')}
Projects: {'; '.join(profile.get('projects', [])[:3])}
Career Goal: {profile.get('career_goal', 'Not specified')}
"""

    user = f"""Score this job opportunity for the candidate:

=== CANDIDATE PROFILE ===
{candidate_summary}

=== JOB POSTING ===
Title: {job_title}
Company: {company}
Location: {location}
Salary: {salary or 'Not mentioned'}
Source: {source}

Job Description:
{job_description[:1500]}

Return ONLY the JSON object."""

    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user}
    ]


# ─────────────────────────────────────────────────────────────
# 3. Batch Job Scoring (lighter prompt for multiple jobs)
# ─────────────────────────────────────────────────────────────

def get_batch_job_scoring_prompt(profile: dict, jobs: list[dict]) -> list[dict]:
    """
    Score multiple jobs at once (faster, less detailed than individual scoring).
    Used for quick batch analysis when Tavily returns many results.
    """
    system = """You are an AI Recruitment Engine. Score multiple jobs for a candidate.

Return ONLY valid JSON array — one object per job IN THE SAME ORDER:
[
    {
        "resume_match": <0-100>,
        "ats_score": <0-100>,
        "shortlist_probability": <0-100>,
        "interview_probability": <0-100>,
        "missing_skills": ["<skill>", ...],
        "matching_skills": ["<skill>", ...],
        "salary_estimate": "<range or 'Not disclosed'>",
        "ai_summary": "<1 sentence>",
        "match_reason": "<specific reason>",
        "competition_level": "<low|medium|high|very_high>",
        "is_remote": <true|false>,
        "urgency": "<urgent|normal|low>"
    },
    ...
]

Be realistic. Scores should reflect actual skill overlap, not be uniformly high."""

    candidate = (
        f"Skills: {', '.join(profile.get('skills', [])[:15])}\n"
        f"Experience: {profile.get('experience_years', 0)} yrs, "
        f"Domain: {profile.get('domain', 'Tech')}, "
        f"Level: {profile.get('seniority_level', 'fresher')}, "
        f"Top Skills: {', '.join(profile.get('top_skills', []))}"
    )

    jobs_text = "\n".join([
        f"{i+1}. {j.get('title','')} at {j.get('company','')} | "
        f"{j.get('location','')} | "
        f"Desc: {j.get('description','')[:200]}"
        for i, j in enumerate(jobs[:10])
    ])

    user = f"Candidate:\n{candidate}\n\nJobs to score:\n{jobs_text}\n\nReturn JSON array only."

    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user}
    ]


# ─────────────────────────────────────────────────────────────
# 4. Daily AI Summary Generator
# ─────────────────────────────────────────────────────────────

def get_daily_summary_prompt(profile: dict, stats: dict, top_jobs: list[dict]) -> list[dict]:
    """
    Generate an AI daily job market summary for the user.
    Feels like a premium AI recruiter briefing.
    """
    system = """You are CareerPilot AI — a premium AI Career Recruiter.
Write an engaging, personalized daily job market briefing for the candidate.

Make it feel like LinkedIn Premium + Perplexity AI combined.
Mention specific numbers, specific skills, specific companies.
Be encouraging but honest. Maximum 4 sentences.
Write in second person ("You have...", "Your profile...").

Return ONLY valid JSON:
{
    "headline": "<catchy briefing headline under 10 words>",
    "summary": "<4 sentence personalized briefing>",
    "top_insight": "<single most important insight>",
    "action_item": "<1 specific action the candidate should take today>",
    "unlock_tip": "<which skill to learn to unlock the most jobs>"
}"""

    top_jobs_text = "\n".join([
        f"- {j.get('title','')} at {j.get('company','')} — {j.get('resume_match',0)}% match"
        for j in top_jobs[:5]
    ])

    user = f"""Generate a daily briefing for:
Role Target: {profile.get('preferred_role', 'Software Developer')}
Domain: {profile.get('domain', 'Technology')}
Top Skills: {', '.join(profile.get('top_skills', []))}

Today's Stats:
- Total jobs analyzed: {stats.get('total', 0)}
- High match (80%+): {stats.get('high_match', 0)}
- Shortlist probability 80%+: {stats.get('high_shortlist', 0)}
- Remote opportunities: {stats.get('remote_count', 0)}
- Average match score: {round(stats.get('avg_match', 0) or 0)}%

Top 5 Jobs Found:
{top_jobs_text}

Return JSON only."""

    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user}
    ]


# ─────────────────────────────────────────────────────────────
# 5. AI Insight Generator
# ─────────────────────────────────────────────────────────────

def get_insights_prompt(profile: dict, missing_skills: list[dict], stats: dict) -> list[dict]:
    """Generate actionable AI insights for the notification panel."""
    system = """You are an AI Career Intelligence Engine.
Generate 5 specific, actionable career insights for the candidate.

Return ONLY valid JSON:
{
    "insights": [
        {
            "type": "<opportunity|warning|tip|achievement|trend>",
            "icon": "<single emoji>",
            "text": "<specific insight text, mention numbers and skills>"
        },
        ...
    ]
}"""

    top_missing = [s["skill"] for s in missing_skills[:5]] if missing_skills else []

    user = f"""Generate insights for:
Target Role: {profile.get('preferred_role', 'Software Developer')}
Top Missing Skills: {', '.join(top_missing) or 'None identified'}
High Match Jobs: {stats.get('high_match', 0)}
High Shortlist Jobs: {stats.get('high_shortlist', 0)}
Total Jobs Found: {stats.get('total', 0)}
Avg Match: {round(stats.get('avg_match', 0) or 0)}%

Return JSON only."""

    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user}
    ]
