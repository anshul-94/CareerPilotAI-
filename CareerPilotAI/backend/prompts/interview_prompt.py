"""
CareerPilot AI — Interview Prompts
Reusable prompt templates for mock interview Q&A generation and evaluation.
"""


def get_interview_questions_prompt(role: str, difficulty: str = "medium",
                                    experience_years: int = 0,
                                    interview_type: str = "technical") -> list[dict]:
    """
    Build prompt to generate interview questions.
    
    Args:
        role: Target job role
        difficulty: easy/medium/hard/expert
        experience_years: Years of experience
        interview_type: technical/behavioral/system_design/mixed
    """
    system_prompt = f"""You are a senior technical interviewer at a top tech company.

Generate exactly 5 interview questions for a {role} position.

Difficulty: {difficulty}
Experience Level: {experience_years} years
Interview Type: {interview_type}

Respond in JSON:
{{
    "questions": [
        {{
            "id": <number>,
            "question": "<detailed question>",
            "difficulty": "<Easy/Medium/Hard>",
            "category": "<category>",
            "expected_time": "<minutes>",
            "key_points": ["<what a good answer should cover>", ...]
        }},
        ...
    ]
}}

Make questions:
1. Progressive in difficulty
2. Relevant to current industry practices
3. Mix of conceptual and practical
4. Include at least one scenario-based question"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate {difficulty} level interview questions for {role} with {experience_years} years experience. Type: {interview_type}"}
    ]


def get_answer_evaluation_prompt(question: str, answer: str,
                                  role: str = "") -> list[dict]:
    """Build prompt to evaluate an interview answer."""
    system_prompt = f"""You are evaluating a candidate's interview answer for a {role or 'Software Developer'} position.

Score the answer on these dimensions (0-100 each):
- Communication: Clarity, structure, articulation
- Technical: Accuracy, depth, correctness
- Confidence: Assertiveness, examples, conviction

Respond in JSON:
{{
    "communication_score": <0-100>,
    "technical_score": <0-100>,
    "confidence_score": <0-100>,
    "overall_score": <0-100>,
    "feedback": "<detailed constructive feedback>",
    "strengths": ["<what was done well>", ...],
    "improvements": ["<specific improvement suggestion>", ...],
    "ideal_answer_points": ["<key point that should be mentioned>", ...]
}}

Be fair but constructive. Provide specific, actionable feedback."""

    user_prompt = f"""Question: {question}

Candidate's Answer: {answer}

Evaluate this answer comprehensively."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_interview_tips_prompt(role: str, scores: dict = None) -> list[dict]:
    """Build prompt for personalized interview tips based on past performance."""
    system_prompt = """You are an interview coach. Based on the candidate's past performance, provide targeted improvement tips.

Respond in JSON:
{
    "focus_areas": ["<area to improve>", ...],
    "practice_exercises": ["<exercise>", ...],
    "resources": ["<resource>", ...],
    "tips": ["<specific tip>", ...]
}"""

    scores_text = ""
    if scores:
        scores_text = f"\nPast Scores: Communication {scores.get('communication', 'N/A')}/100, Technical {scores.get('technical', 'N/A')}/100, Confidence {scores.get('confidence', 'N/A')}/100"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Role: {role}{scores_text}\n\nProvide targeted interview preparation tips."}
    ]
