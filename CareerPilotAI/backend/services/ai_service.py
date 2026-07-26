"""
CareerPilot AI — AI Service
Orchestrates AI calls for career coaching, roadmaps, code review, SQL coaching,
and projects using the active AI provider (Ollama locally, Groq in production).

Routes call ONLY this service — never the underlying provider directly.
"""

from typing import Generator
from backend.ai.providers import ai_gateway
from backend.ai.response_parser import parse_json_response, format_markdown_to_html
from backend.ai.conversation_manager import ConversationManager
from backend.prompts.career_prompt import get_suggested_questions
from backend.prompts.roadmap_prompt import get_roadmap_prompt
from backend.prompts.code_review_prompt import get_code_review_prompt
from backend.prompts.sql_prompt import get_sql_analysis_prompt
from backend.prompts.interview_prompt import (
    get_interview_questions_prompt,
    get_answer_evaluation_prompt
)


class AIService:
    """Orchestrates all AI operations across modules via the active AI provider."""
    
    @staticmethod
    def generate(prompt: str, temperature: float = 0.7, json_mode: bool = False) -> dict:
        """Universal text generation abstraction."""
        return ai_gateway.generate(prompt, temperature=temperature, json_mode=json_mode)

    @staticmethod
    def chat_completion(messages: list, temperature: float = 0.7, json_mode: bool = False) -> dict:
        """Universal chat completion abstraction (bypasses conversation manager)."""
        return ai_gateway.chat(messages, temperature=temperature, json_mode=json_mode)

    # ── Career Coach ──────────────────────────────────────────────
    
    @staticmethod
    def chat(user_id: int, message: str, session_id: str,
             user_context: dict = None) -> dict:
        """Process a career coaching chat message."""
        result = ConversationManager.handle_message(user_id, message, session_id, user_context)
        result["response_html"] = format_markdown_to_html(result["response"])
        result["suggested_questions"] = get_suggested_questions("general")
        result["mock"] = False
        return result

    @staticmethod
    def stream_chat(user_id: int, message: str, session_id: str,
                    user_context: dict = None) -> Generator[str, None, None]:
        """Stream a career coaching response for typing animation."""
        return ConversationManager.stream_message(user_id, message, session_id, user_context)

    # ── Learning Roadmap ──────────────────────────────────────────
    
    @staticmethod
    def generate_roadmap(current_skills: list, target_role: str,
                         experience_level: str = "beginner") -> dict:
        """Generate a personalized learning roadmap using LLM."""
        messages = get_roadmap_prompt(current_skills, target_role, experience_level)
        response = ai_gateway.chat(messages, temperature=0.5, json_mode=True)
        
        if response.get("success"):
            roadmap = parse_json_response(response["content"], fallback_structure={
                "weekly_plan": [], "courses": [], "title": "Learning Roadmap", "estimated_duration": ""
            })
            roadmap["mock"] = False
            return roadmap
        
        return {"error": response.get("error", "Failed to generate roadmap"), "mock": False, "weekly_plan": []}

    # ── Mock Interview ────────────────────────────────────────────
    
    @staticmethod
    def generate_interview_questions(role: str, difficulty: str = "medium",
                                      experience_years: int = 0,
                                      interview_type: str = "technical") -> dict:
        """Generate interview questions for a mock session dynamically."""
        messages = get_interview_questions_prompt(
            role, difficulty, experience_years, interview_type
        )
        response = ai_gateway.chat(messages, temperature=0.6, json_mode=True)
        
        if response.get("success"):
            data = parse_json_response(response["content"], fallback_structure={"questions": []})
            data["mock"] = False
            return data
        
        return {"error": response.get("error", "Failed to generate questions"), "mock": False, "questions": []}

    @staticmethod
    def evaluate_answer(question: str, answer: str, role: str = "") -> dict:
        """Evaluate a candidate's interview answer."""
        messages = get_answer_evaluation_prompt(question, answer, role)
        response = ai_gateway.chat(messages, temperature=0.3, json_mode=True)
        
        if response.get("success"):
            evaluation = parse_json_response(response["content"], fallback_structure={
                "communication_score": 0, "technical_score": 0, "confidence_score": 0, 
                "overall_score": 0, "feedback": "Failed to parse evaluation response."
            })
            evaluation["mock"] = False
            return evaluation
        
        return {"error": response.get("error", "Failed to evaluate answer"), "mock": False,
                "communication_score": 0, "technical_score": 0, "confidence_score": 0, 
                "overall_score": 0, "feedback": response.get("error", "API error")}

    # ── Code Review ───────────────────────────────────────────────
    
    @staticmethod
    def review_code(code: str, language: str = "python") -> dict:
        """Perform a real AI code review."""
        messages = get_code_review_prompt(code, language)
        response = ai_gateway.chat(messages, temperature=0.3, json_mode=True)
        
        if response.get("success"):
            review = parse_json_response(response["content"], fallback_structure={
                "overall_quality": "Unknown", "score": 0, "bugs": [], "optimizations": []
            })
            review["mock"] = False
            return review
        
        return {"error": response.get("error", "Failed to review code"), "mock": False, "overall_quality": "Error", "bugs": []}

    # ── SQL Coach ─────────────────────────────────────────────────
    
    @staticmethod
    def analyze_sql(query: str) -> dict:
        """Analyze and optimize a SQL query using the active AI provider."""
        messages = get_sql_analysis_prompt(query)
        response = ai_gateway.chat(messages, temperature=0.3, json_mode=True)
        
        if response.get("success"):
            analysis = parse_json_response(response["content"], fallback_structure={
                "explanation": "Failed to parse analysis.", "optimization": "", "optimized_query": "", "suggestions": []
            })
            analysis["mock"] = False
            return analysis
        
        return {"error": response.get("error", "Failed to analyze SQL"), "mock": False, "explanation": "Error", "optimized_query": ""}

    # ── Project Generator ─────────────────────────────────────────
    
    @staticmethod
    def generate_projects(domain: str, skills: list,
                          experience_level: str = "beginner") -> dict:
        """Generate portfolio project ideas."""
        system_prompt = """You are a senior software architect. Generate 3 unique portfolio project ideas based on the user's domain and skills.

Respond ONLY in JSON format:
{
    "projects": [
        {
            "title": "<project name>",
            "description": "<2-3 sentence description>",
            "tech_stack": ["<tech>", ...],
            "architecture": "<architecture pattern>",
            "folder_structure": "<directory tree>",
            "difficulty": "Beginner/Intermediate/Advanced",
            "timeline": "<estimated time>",
            "learning_outcomes": ["<outcome>", ...]
        }
    ]
}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Domain: {domain}\nSkills: {', '.join(skills)}\nLevel: {experience_level}"}
        ]
        
        response = ai_gateway.chat(messages, temperature=0.7, json_mode=True)
        
        if response.get("success"):
            data = parse_json_response(response["content"], fallback_structure={"projects": []})
            data["mock"] = False
            return data
        
        return {"error": response.get("error", "Failed to generate projects"), "mock": False, "projects": []}

