"""
CareerPilot AI — Learning Roadmap Prompts
Reusable prompt templates for AI-generated learning roadmaps.
"""


def get_roadmap_prompt(current_skills: list, target_role: str,
                       experience_level: str = "beginner") -> list[dict]:
    """
    Build prompt for generating a comprehensive learning roadmap.
    
    Args:
        current_skills: List of current skills
        target_role: Target job role
        experience_level: Current experience level
    """
    system_prompt = """You are an expert career and education advisor specializing in technology learning paths.

Generate a comprehensive, personalized learning roadmap based on the student's current skills and target role.

Respond in valid JSON format:
{
    "target_role": "<role>",
    "estimated_duration": "<e.g., 6 months>",
    "daily_plan": {
        "morning": "<2 hours activity>",
        "afternoon": "<2 hours activity>",
        "evening": "<1 hour activity>",
        "night": "<30 min activity>"
    },
    "weekly_plan": [
        {"week": "Week 1-2", "focus": "<topic>", "hours": <number>},
        ...
    ],
    "courses": [
        {"name": "<course>", "platform": "<platform>", "duration": "<duration>", "priority": "High/Medium/Low"},
        ...
    ],
    "books": [
        {"name": "<book>", "author": "<author>", "priority": "Must Read/Recommended/Reference"},
        ...
    ],
    "projects": [
        {"name": "<project>", "difficulty": "Beginner/Intermediate/Advanced", "duration": "<time>"},
        ...
    ],
    "interview_topics": ["<topic>", ...],
    "certifications": ["<cert>", ...],
    "milestones": [
        {"month": 1, "goal": "<milestone>"},
        ...
    ]
}

Make the roadmap:
1. Progressive — start with fundamentals, build to advanced
2. Practical — include hands-on projects at each stage
3. Realistic — achievable timeline for a dedicated student
4. Industry-aligned — focus on skills companies actually hire for"""

    skills_str = ", ".join(current_skills) if current_skills else "No specific skills mentioned"
    
    user_prompt = f"""Create a personalized learning roadmap:

Current Skills: {skills_str}
Target Role: {target_role}
Experience Level: {experience_level}

Generate a detailed, actionable roadmap that bridges the gap between current skills and the target role."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_skill_gap_prompt(current_skills: list, target_skills: list) -> list[dict]:
    """Build prompt for skill gap analysis."""
    system_prompt = """Analyze the gap between current skills and required skills for the target role.

Respond in JSON:
{
    "matching_skills": ["<skill>", ...],
    "missing_critical": ["<skill with priority>", ...],
    "missing_nice_to_have": ["<skill>", ...],
    "learning_priority": ["<ordered skill to learn>", ...],
    "estimated_time": "<total time to close gaps>"
}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Current: {', '.join(current_skills)}\nRequired: {', '.join(target_skills)}"}
    ]
