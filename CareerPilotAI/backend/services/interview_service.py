"""
CareerPilot AI — Interview Service
Handles mock interview sessions and evaluations.
"""

import json
import uuid
from typing import Optional
from backend.services.ai_service import AIService
from backend.models.interview import InterviewModel
from backend.utils.helpers import safe_json_loads


class InterviewService:
    """Business logic for mock interview operations."""

    @staticmethod
    def start_session(user_id: int, role: str, difficulty: str = "medium",
                      experience_years: int = 0,
                      interview_type: str = "technical") -> dict:
        """Start a new mock interview session and generate questions."""
        # Create session
        interview_id = InterviewModel.create(
            user_id=user_id,
            role=role,
            difficulty=difficulty,
            experience_years=experience_years,
            interview_type=interview_type
        )
        
        # Generate questions
        questions_data = AIService.generate_interview_questions(
            role, difficulty, experience_years, interview_type
        )
        
        questions = questions_data.get("questions", [])
        
        # Save questions to the session
        if questions:
            interview = InterviewModel.get_by_id(interview_id)
            from backend.database.db import execute_update
            execute_update(
                "UPDATE interview_history SET questions = ? WHERE id = ?",
                (json.dumps(questions), interview_id)
            )
        
        return {
            "interview_id": interview_id,
            "questions": questions,
            "role": role,
            "difficulty": difficulty,
            "mock": questions_data.get("mock", False)
        }

    @staticmethod
    def evaluate_session(interview_id: int, answers: list) -> dict:
        """Evaluate all answers in an interview session."""
        interview = InterviewModel.get_by_id(interview_id)
        if not interview:
            return {"error": "Interview session not found"}
        
        questions = safe_json_loads(interview.get('questions', '[]'), [])
        if not questions:
            return {"error": "No questions found for this session"}
        
        evaluations = []
        total_comm = 0
        total_tech = 0
        total_conf = 0
        
        for i, q in enumerate(questions):
            answer = answers[i] if i < len(answers) else ""
            if answer:
                evaluation = AIService.evaluate_answer(
                    q.get("question", ""), answer, interview.get("role", "")
                )
                evaluations.append(evaluation)
                total_comm += evaluation.get("communication_score", 0)
                total_tech += evaluation.get("technical_score", 0)
                total_conf += evaluation.get("confidence_score", 0)
            else:
                evaluations.append({
                    "communication_score": 0, "technical_score": 0,
                    "confidence_score": 0, "overall_score": 0,
                    "feedback": "No answer provided"
                })
        
        answered = max(1, sum(1 for a in answers if a))
        avg_comm = round(total_comm / answered)
        avg_tech = round(total_tech / answered)
        avg_conf = round(total_conf / answered)
        overall = round((avg_comm + avg_tech + avg_conf) / 3)
        
        # Generate overall feedback
        feedback = InterviewService._generate_feedback(avg_comm, avg_tech, avg_conf)
        
        # Save results
        InterviewModel.update_results(
            interview_id=interview_id,
            questions=questions,
            answers=answers,
            evaluations=evaluations,
            communication_score=avg_comm,
            technical_score=avg_tech,
            confidence_score=avg_conf,
            overall_score=overall,
            feedback=feedback
        )
        
        return {
            "interview_id": interview_id,
            "evaluations": evaluations,
            "communication_score": avg_comm,
            "technical_score": avg_tech,
            "confidence_score": avg_conf,
            "overall_score": overall,
            "feedback": feedback
        }

    @staticmethod
    def get_user_history(user_id: int) -> list[dict]:
        """Get interview history for a user."""
        interviews = InterviewModel.get_by_user(user_id)
        for interview in interviews:
            interview['questions'] = safe_json_loads(interview.get('questions', '[]'), [])
            interview['evaluations'] = safe_json_loads(interview.get('evaluations', '[]'), [])
        return interviews

    @staticmethod
    def get_stats(user_id: int) -> dict:
        """Get interview statistics."""
        return InterviewModel.get_stats(user_id)

    @staticmethod
    def _generate_feedback(comm: int, tech: int, conf: int) -> str:
        """Generate overall feedback based on scores."""
        overall = (comm + tech + conf) / 3
        
        if overall >= 80:
            return "Excellent performance! You demonstrated strong technical knowledge and communicated your ideas clearly. Keep up the great work and focus on maintaining consistency."
        elif overall >= 60:
            return "Good effort! You showed solid understanding in several areas. Focus on strengthening your weaker areas and practice structuring your answers more concisely."
        elif overall >= 40:
            return "Fair performance with room for improvement. Review the fundamental concepts, practice explaining your thought process aloud, and work on building confidence in your answers."
        else:
            return "This session highlighted several areas for improvement. Focus on building your foundational knowledge, practice daily with sample questions, and consider mock sessions with peers."
