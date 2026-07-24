"""
CareerPilot AI — Prompt Builder
Centralized class to handle building dynamic prompts for the local Ollama LLM.
"""
from backend.prompts.career_prompt import get_career_chat_prompt, get_suggested_questions
from backend.prompts.resume_prompt import (
    get_resume_analysis_prompt,
    get_skills_extraction_prompt,
    get_resume_improvement_prompt
)
from backend.prompts.roadmap_prompt import get_roadmap_prompt
from backend.prompts.code_review_prompt import get_code_review_prompt
from backend.prompts.sql_prompt import get_sql_analysis_prompt
from backend.prompts.interview_prompt import (
    get_interview_questions_prompt,
    get_answer_evaluation_prompt
)
from backend.prompts.job_prompt import get_job_match_prompt

class PromptBuilder:
    """Builder class for dynamically assembling prompts based on context."""
    
    @staticmethod
    def build_career_prompt(user_message: str, history: list, context: dict):
        return get_career_chat_prompt(user_message, history, context)
        
    @staticmethod
    def build_resume_analysis_prompt(resume_text: str, target_role: str):
        return get_resume_analysis_prompt(resume_text, target_role)
        
    @staticmethod
    def build_skills_extraction_prompt(resume_text: str):
        return get_skills_extraction_prompt(resume_text)
        
    @staticmethod
    def build_roadmap_prompt(current_skills: list, target_role: str, experience: str):
        return get_roadmap_prompt(current_skills, target_role, experience)
        
    @staticmethod
    def build_code_review_prompt(code: str, language: str):
        return get_code_review_prompt(code, language)
        
    @staticmethod
    def build_sql_prompt(query: str):
        return get_sql_analysis_prompt(query)
        
    @staticmethod
    def build_interview_prompt(role: str, diff: str, years: int, int_type: str):
        return get_interview_questions_prompt(role, diff, years, int_type)
        
    @staticmethod
    def build_evaluation_prompt(question: str, answer: str, role: str):
        return get_answer_evaluation_prompt(question, answer, role)
        
    @staticmethod
    def build_job_match_prompt(user_skills: list, job_description: str):
        return get_job_match_prompt(user_skills, job_description)
