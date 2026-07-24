"""
CareerPilot AI — Code Review Prompts
Reusable prompt templates for AI code review and bug detection.
"""


def get_code_review_prompt(code: str, language: str = "python") -> list[dict]:
    """
    Build prompt for comprehensive code review.
    
    Args:
        code: Source code to review
        language: Programming language
    """
    system_prompt = f"""You are a senior {language} code reviewer with expertise in software engineering best practices.

Analyze the given code and provide a comprehensive review.

Respond in valid JSON format:
{{
    "overall_quality": "<Excellent/Good/Fair/Poor>",
    "score": <0-100>,
    "bugs": [
        {{"line": <number>, "severity": "High/Medium/Low", "description": "<bug description>"}}
    ],
    "optimizations": ["<optimization suggestion>", ...],
    "complexity": {{
        "time": "<Big-O time complexity>",
        "space": "<Big-O space complexity>",
        "cyclomatic": "<cyclomatic complexity estimate>"
    }},
    "code_quality": {{
        "readability": "<assessment>",
        "maintainability": "<assessment>",
        "documentation": "<assessment>",
        "testing": "<assessment>"
    }},
    "suggestions": ["<improvement suggestion>", ...],
    "security_issues": ["<security concern if any>", ...],
    "best_practices": ["<best practice recommendation>", ...]
}}

Be thorough but constructive. Focus on actionable improvements."""

    user_prompt = f"""Review this {language} code:

```{language}
{code[:5000]}
```

Provide a comprehensive code review."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_code_optimization_prompt(code: str, language: str = "python") -> list[dict]:
    """Build prompt for code optimization suggestions."""
    system_prompt = f"""You are a {language} performance optimization expert. 
Analyze the code and provide an optimized version with explanations.

Respond in JSON:
{{
    "optimized_code": "<optimized version of the code>",
    "changes": ["<what was changed and why>", ...],
    "performance_improvement": "<estimated improvement>",
    "explanation": "<detailed explanation of optimizations>"
}}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Optimize this {language} code:\n\n```{language}\n{code[:4000]}\n```"}
    ]
