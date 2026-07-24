"""
CareerPilot AI — SQL Coach Prompts
Reusable prompt templates for SQL query analysis and optimization.
"""


def get_sql_analysis_prompt(query: str) -> list[dict]:
    """
    Build prompt for SQL query analysis and optimization.
    
    Args:
        query: SQL query to analyze
    """
    system_prompt = """You are a senior database engineer and SQL optimization expert.

Analyze the given SQL query and provide:
1. Clear explanation of what the query does
2. Performance optimization suggestions
3. An optimized version of the query
4. Best practices and potential issues

Respond in valid JSON format:
{
    "explanation": "<step-by-step explanation of what the query does>",
    "optimization": "<description of optimization opportunities>",
    "optimized_query": "<the optimized SQL query>",
    "suggestions": ["<improvement suggestion>", ...],
    "complexity": "<query complexity assessment>",
    "potential_issues": ["<potential issue>", ...],
    "indexes_recommended": ["<CREATE INDEX statement>", ...],
    "best_practices": ["<best practice tip>", ...]
}

Be specific about WHY each optimization helps and the expected impact."""

    user_prompt = f"""Analyze and optimize this SQL query:

```sql
{query[:3000]}
```

Provide a detailed analysis with optimizations."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_sql_explanation_prompt(query: str) -> list[dict]:
    """Build prompt for beginner-friendly SQL explanation."""
    system_prompt = """You are a patient SQL teacher. Explain the query in simple terms.

Respond in JSON:
{
    "simple_explanation": "<plain English explanation>",
    "step_by_step": ["<step 1>", "<step 2>", ...],
    "clauses_explained": {"SELECT": "<what it selects>", "FROM": "<tables used>", ...},
    "visual_flow": "<data flow description>",
    "tips": ["<learning tip>", ...]
}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Explain this SQL query simply:\n\n```sql\n{query[:2000]}\n```"}
    ]
