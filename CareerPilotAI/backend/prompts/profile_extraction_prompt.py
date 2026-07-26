"""
CareerPilot AI — Profile Extraction Prompts
Deep LLM extraction of 20+ career fields from resume text.
Used by CareerProfileService.sync_from_resume().
"""


def get_deep_profile_extraction_prompt(resume_text: str) -> list[dict]:
    """
    Build the deep extraction prompt to parse all career DNA fields.
    Returns list of message dicts for the Ollama / Groq API.
    
    Extracts: name, phone, location, linkedin, github, portfolio,
              preferred_role, career_goal, expected_salary,
              skills, top_skills, soft_skills, technologies,
              certifications, projects, experience_summary,
              education, experience_years, domain, seniority_level,
              ats_score, ai_readiness, resume_strength.
    """
    system_prompt = """You are an expert AI Career Profile Extractor.
Your job is to deeply analyze a resume and extract a comprehensive career profile.

You MUST respond with ONLY valid JSON (no markdown, no commentary).

JSON structure:
{
  "full_name": "<full name from resume>",
  "phone": "<phone number or empty string>",
  "email": "<email or empty string>",
  "location": "<city, state or country — e.g. Indore, India>",
  "linkedin_url": "<linkedin profile URL or empty>",
  "github_url": "<github profile URL or empty>",
  "portfolio_url": "<portfolio or personal website URL or empty>",

  "preferred_role": "<single best-fit job title e.g. Machine Learning Engineer>",
  "domain": "<technical domain e.g. AI/ML, Web Development, Data Engineering>",
  "career_goal": "<one sentence career objective inferred from the resume>",
  "seniority_level": "<fresher | junior | mid | senior>",
  "experience_years": <integer — total years of relevant experience>,

  "skills": ["<skill1>", "<skill2>", ...],
  "top_skills": ["<most important skill 1>", ...],
  "soft_skills": ["<soft skill1>", ...],
  "technologies": ["<tech/tool1>", ...],
  "certifications": ["<cert1>", ...],

  "projects": [
    {
      "name": "<project title>",
      "description": "<1-2 sentence description>",
      "tech_stack": ["<tech>", ...]
    }
  ],

  "education": "<Highest degree — e.g. B.Tech Computer Science, RGPV, 2025>",
  "experience_summary": "<2-3 sentence summary of work/internship experience>",

  "expected_salary": "<e.g. ₹8-12 LPA or $80k-100k or empty>",
  "preferred_location": "<preferred work city/remote preference or empty>",

  "ats_score": <integer 0-100 — estimated ATS compatibility>,
  "ai_readiness": <integer 0-100 — readiness for AI/tech industry roles>,
  "resume_strength": <integer 0-100 — overall resume quality score>
}

Rules:
- skills should contain all technical and domain skills (20-40 items max)
- top_skills should contain only the 5-8 most prominent skills
- technologies should focus on tools, frameworks, libraries, platforms
- soft_skills are things like Leadership, Communication, Problem Solving
- seniority_level is ALWAYS one of: fresher, junior, mid, senior
- experience_years for freshers = 0
- If something is not found, use empty string "" or empty array []
- Never hallucinate contact information — only extract what's explicitly in the resume"""

    user_prompt = f"""Extract the complete career profile from this resume:

---RESUME START---
{resume_text[:6000]}
---RESUME END---

Return ONLY the JSON object. No explanation."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt}
    ]


def get_career_health_prompt(profile: dict) -> list[dict]:
    """
    Generate a holistic AI career health assessment from a career profile.
    Returns JSON with health score, strengths, gaps, and recommendations.
    """
    skills    = profile.get("top_skills", profile.get("skills", []))[:8]
    role      = profile.get("preferred_role", "Software Developer")
    level     = profile.get("seniority_level", "fresher")
    exp_years = profile.get("experience_years", 0)
    ats       = profile.get("ats_score", 0)
    certs     = profile.get("certifications", [])

    system_prompt = """You are an AI Career Health Advisor.
Given a candidate profile, generate a career health assessment.

Respond ONLY with valid JSON:
{
  "career_health_score": <integer 0-100>,
  "ai_readiness": <integer 0-100>,
  "strengths": ["<strength1>", ...],
  "skill_gaps": ["<missing skill1>", ...],
  "recommended_skills": ["<skill to learn>", ...],
  "recommended_roles": ["<role1>", "<role2>"],
  "best_cities": ["<city1>", "<city2>", "<city3>"],
  "career_insight": "<2-sentence AI insight about this person's career>",
  "action_items": ["<action item 1>", ...]
}"""

    user_prompt = f"""Career Profile:
- Target Role: {role}
- Level: {level} ({exp_years} years)
- Top Skills: {', '.join(skills)}
- Certifications: {', '.join(certs) if certs else 'None'}
- ATS Score: {ats}

Generate career health assessment JSON."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt}
    ]
