"""
CareerPilot AI — Resume Analysis Prompts
Reusable prompt templates for ATS resume analysis.
"""


def get_resume_analysis_prompt(resume_text: str, target_role: str = "") -> list[dict]:
    """
    Build the prompt for comprehensive resume analysis.
    
    Args:
        resume_text: Extracted text from the resume PDF
        target_role: Optional target job role for tailored analysis
        
    Returns:
        List of message dicts for the Ollama API
    """
    role_context = f" targeting the role of {target_role}" if target_role else ""
    
    system_prompt = f"""You are an expert ATS (Applicant Tracking System) Resume Analyst and Career Consultant with 15+ years of experience in technical recruitment.

Your task is to analyze the given resume{role_context} and provide a comprehensive evaluation.

You MUST respond in valid JSON format with the following structure:
{{
    "ats_score": <integer 0-100>,
    "strong_skills": ["<skill with brief explanation>", ...],
    "weak_skills": ["<skill gap with recommendation>", ...],
    "missing_keywords": ["<keyword>", ...],
    "grammar_issues": ["<issue description with line reference>", ...],
    "experience_analysis": "<detailed analysis of work experience section>",
    "project_analysis": "<detailed analysis of projects section>",
    "summary": "<overall assessment and key takeaways>",
    "action_plan": ["<actionable improvement step>", ...]
}}

Scoring Guidelines:
- 90-100: Excellent — ATS optimized, strong keywords, quantified achievements
- 75-89: Good — Minor improvements needed
- 60-74: Fair — Several areas need attention
- Below 60: Needs significant improvement

Be specific, actionable, and constructive in your feedback."""

    user_prompt = f"""Please analyze this resume thoroughly:

---
{resume_text[:5000]}
---

Provide your analysis in the JSON format specified."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_resume_improvement_prompt(resume_text: str, analysis: dict) -> list[dict]:
    """Build prompt for generating specific resume improvements."""
    system_prompt = """You are an expert resume writer. Based on the previous analysis, provide specific rewritten sections that would improve the resume's ATS score and impact.

Respond in JSON format:
{
    "improved_summary": "<rewritten professional summary>",
    "improved_bullets": ["<rewritten achievement bullet>", ...],
    "keywords_to_add": ["<keyword>", ...],
    "formatting_tips": ["<tip>", ...]
}"""

    user_prompt = f"""Original Resume:
{resume_text[:3000]}

Previous Analysis Score: {analysis.get('ats_score', 'N/A')}
Key Issues: {', '.join(analysis.get('weak_skills', [])[:5])}

Please provide improved content."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_skills_extraction_prompt(resume_text: str) -> list[dict]:
    """Build prompt to extract structured skills from resume."""
    system_prompt = """Extract all technical and soft skills from this resume. Categorize them.

Respond in JSON:
{
    "technical_skills": ["<skill>", ...],
    "soft_skills": ["<skill>", ...],
    "tools": ["<tool/platform>", ...],
    "certifications": ["<cert>", ...],
    "experience_years": <estimated total years>,
    "education_level": "<highest education>",
    "preferred_role": "<best matching role title>"
}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Extract skills from this resume:\n\n{resume_text[:4000]}"}
    ]
