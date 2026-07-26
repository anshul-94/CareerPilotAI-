"""
CareerPilot AI — Resume Intelligence Prompts
Prompts for rewriting resumes and scoring them.
"""

def get_resume_rewrite_prompt(profile: dict, target_role: str, market_insights: dict) -> list[dict]:
    """
    Build the prompt for the AI to completely rewrite the user's resume.
    """
    market_keywords = market_insights.get("top_keywords", [])
    
    system_prompt = f"""You are a Principal Technical Recruiter and Expert Resume Writer at a FAANG company.
Your goal is to write a highly professional, ATS-optimized, metric-driven resume for a candidate targeting the role of: {target_role}

You will receive the candidate's raw profile data.
You MUST rewrite their experience and projects to be highly impactful, using strong action verbs, quantifiable metrics, and incorporating relevant industry keywords.

Important Market Keywords for this role right now: {', '.join(market_keywords) if market_keywords else 'Use standard industry keywords'}

You MUST respond ONLY with a valid JSON object representing the rewritten resume. No markdown blocks outside the JSON, no commentary.

JSON structure:
{{
  "professional_summary": "<3-4 impactful sentences summarizing their expertise and value proposition tailored for {target_role}>",
  "technical_skills": ["<categorized or flat list of top 10-15 hard skills>"],
  "soft_skills": ["<top 3-5 soft skills>"],
  "experience": [
    {{
      "company": "<Company Name or 'Personal Projects' if fresher>",
      "role": "<Job Title>",
      "duration": "<Start - End Date>",
      "bullets": [
        "<Action verb + context + result/metric. E.g., 'Engineered a scalable microservice architecture using Python and Docker, reducing latency by 40%.'>",
        "<bullet 2>",
        "<bullet 3>"
      ]
    }}
  ],
  "projects": [
    {{
      "name": "<Project Name>",
      "description": "<High impact 1-sentence description>",
      "technologies": ["<Tech 1>", "<Tech 2>"],
      "bullets": [
        "<Action verb + technical implementation + result>"
      ]
    }}
  ],
  "education": [
    {{
      "institution": "<University/College>",
      "degree": "<Degree>",
      "year": "<Graduation Year>"
    }}
  ],
  "certifications": ["<Cert 1>", "<Cert 2>"]
}}

Rules:
1. DO NOT invent fake companies or fake degrees. Use what is provided.
2. DO invent REASONABLE metrics for projects if the user provided none (e.g., 'improved efficiency by 20%', 'handled 1000+ requests'), but keep them realistic for the seniority level.
3. Keep bullets strictly to the 'Action Verb -> Context -> Metric/Result' format.
4. Ensure the terminology matches the target role ({target_role}).
5. If the candidate is a fresher, emphasize projects and academic achievements in the experience format.
"""

    # Format the profile data into a readable string for the prompt
    profile_str = f"""
Name: {profile.get('full_name')}
Current Level: {profile.get('seniority_level', 'fresher')}
Years of Experience: {profile.get('experience_years', 0)}
Target Role: {target_role}

Current Skills: {', '.join(profile.get('skills', []))}
Technologies: {', '.join(profile.get('technologies', []))}

Experience Summary (Raw):
{profile.get('experience_summary', 'None provided')}

Projects (Raw):
{profile.get('projects', 'None provided')}

Education:
{profile.get('education', 'None provided')}
"""

    user_prompt = f"""Here is the candidate's raw profile data. Rewrite it into a world-class resume JSON.

RAW DATA:
{profile_str}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_resume_scoring_prompt(rewritten_resume: dict, target_role: str) -> list[dict]:
    """
    Build the prompt for scoring the newly generated resume.
    """
    import json
    
    system_prompt = f"""You are an elite ATS AI Scoring Engine.
Evaluate the provided resume against the target role: {target_role}.

You MUST respond ONLY with a valid JSON object. No commentary.

JSON structure:
{{
  "scores": {{
    "ats": <integer 0-100, overall ATS parseability and keyword match>,
    "keyword": <integer 0-100, keyword density for the role>,
    "readability": <integer 0-100, clarity, bullet length, action verbs>,
    "recruiter": <integer 0-100, human recruiter appeal/impact>,
    "technical": <integer 0-100, depth of technical skills shown>,
    "impact": <integer 0-100, presence of metrics and results>,
    "formatting": <integer 0-100, structure>
  }},
  "suggestions": [
    "<Actionable suggestion 1, e.g., 'Add AWS to your skills to match 80% of current ML jobs'>",
    "<Actionable suggestion 2>"
  ]
}}
"""

    user_prompt = f"""Evaluate this resume for a {target_role} position:

{json.dumps(rewritten_resume, indent=2)}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
