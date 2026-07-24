"""
CareerPilot AI — Agent Planner
Intelligently decides which sub-module or action to trigger based on user intent.
"""
from backend.ai.ollama_service import ollama
from backend.ai.response_parser import parse_json_response

class AgentPlanner:
    """LLM-based router to decide application actions dynamically."""

    @staticmethod
    def plan_action(user_input: str, user_context: dict = None) -> dict:
        """
        Ask the LLM to classify the user intent into a specific module/action.
        """
        system_prompt = """You are the core routing agent for CareerPilot AI.
Your job is to analyze the user's input and decide which module should handle it.

Modules available:
- 'career_coach': General career advice, interview tips, salary negotiation.
- 'analyze_resume': User wants feedback on a resume.
- 'search_jobs': User wants to find job openings.
- 'generate_roadmap': User wants a learning path to learn a skill or role.
- 'review_code': User wants to debug or optimize code.
- 'sql_coach': User wants help with a SQL query.
- 'mock_interview': User wants to practice interviewing.

Return ONLY a JSON response in the following format:
{
    "selected_module": "<module_name>",
    "extracted_parameters": {
        // Any parameters you can extract (e.g., target_role, language, query, skills)
    },
    "confidence": 0.95
}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        # Call Ollama API
        response = ollama.chat(messages, temperature=0.1, json_mode=True)
        
        fallback = {
            "selected_module": "career_coach",
            "extracted_parameters": {},
            "confidence": 0.5
        }

        if response.get("success"):
            return parse_json_response(response["content"], fallback_structure=fallback)
        
        return fallback
