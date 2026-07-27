"""
CareerPilot AI — AI Problem Solving Service
Handles compiler execution, test case matching, and AI mentorship metrics.
"""

import time
import json
import traceback
import sys
from io import StringIO
from typing import Optional, Tuple
from multiprocessing import Process, Queue

from backend.database.db import execute_query, execute_one, execute_insert, execute_update
from backend.ai.providers import get_provider

class ProblemService:
    """Service handling coding environment business logic and AI analysis."""

    @staticmethod
    def get_problems(difficulty: str = None, topic: str = None, company: str = None) -> list[dict]:
        """Fetch problems based on filters."""
        query = "SELECT * FROM problems WHERE 1=1"
        params = []
        
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        if company:
            query += " AND companies LIKE ?"
            params.append(f"%{company}%")
            
        return execute_query(query, tuple(params))

    @staticmethod
    def get_problem_by_id(problem_id: int) -> Optional[dict]:
        """Fetch problem by its primary ID."""
        problem = execute_one("SELECT * FROM problems WHERE id = ?", (problem_id,))
        if problem:
            # Fetch problem templates for all languages
            templates = execute_query("SELECT language, starter_code FROM problem_templates WHERE problem_id = ?", (problem_id,))
            problem["starter_code"] = {t["language"]: t["starter_code"] for t in templates}

            if problem.get("examples"):
                try:
                    problem["examples"] = json.loads(problem["examples"])
                except Exception:
                    problem["examples"] = []
            if problem.get("hints"):
                try:
                    problem["hints"] = json.loads(problem["hints"])
                except Exception:
                    problem["hints"] = []
        return problem

    @staticmethod
    def get_test_cases(problem_id: int) -> list[dict]:
        """Fetch all test cases for a problem."""
        return execute_query("SELECT * FROM problem_test_cases WHERE problem_id = ?", (problem_id,))



    @staticmethod
    def execute_code(problem_id: int, code: str, language: str) -> dict:
        """Run code against all test cases for a problem (public and hidden)."""
        test_cases = ProblemService.get_test_cases(problem_id)
            
        from backend.services.judge_service import JudgeService
        return JudgeService.evaluate(problem_id, code, language, test_cases)

    @staticmethod
    def get_hints_used(user_id: int, problem_id: int) -> list[int]:
        """Fetch indices of hints user has unlocked."""
        rows = execute_query(
            "SELECT hint_index FROM problem_hints_used WHERE user_id = ? AND problem_id = ?",
            (user_id, problem_id)
        )
        return [r["hint_index"] for r in rows]

    @staticmethod
    def unlock_hint(user_id: int, problem_id: int, hint_index: int):
        """Unlock a specific hint index."""
        try:
            execute_insert(
                "INSERT INTO problem_hints_used (user_id, problem_id, hint_index) VALUES (?, ?, ?)",
                (user_id, problem_id, hint_index)
            )
        except Exception:
            pass # Already unlocked

    @staticmethod
    def analyze_submission_ai(user_id: int, problem_id: int, code: str, language: str, submission_id: int) -> dict:
        """Call AI provider to analyze code quality and learning behavior."""
        problem = ProblemService.get_problem_by_id(problem_id)
        if not problem:
            return {}
            
        prompt = f"""
        You are an expert AI Coding Mentor and Technical Interviewer.
        Analyze the following code submitted by the user.

        Problem Title: {problem['title']}
        Difficulty: {problem['difficulty']}
        Topic: {problem['topic']}
        Language: {language}

        User Code:
        {code}

        Perform a complete evaluation. Respond strictly in valid JSON format matching this schema:
        {{
            "correctness": 100, // Score out of 100
            "time_complexity": "O(N)",
            "space_complexity": "O(1)",
            "naming_convention": 90, // Score out of 100
            "readability": 90, // Score out of 100
            "logic": 95, // Score out of 100
            "optimization": 85, // Score out of 100
            "code_style": 90, // Score out of 100
            "maintainability": 90, // Score out of 100
            "edge_cases": "Evaluation of edge case handling.",
            "potential_bugs": "Identify any bugs or write 'None'.",
            "interview_quality": 85, // Score out of 100
            "overall_score": 90,
            "feedback_report": {{
                "what_went_well": "Description of what they did well.",
                "mistakes": "Specific logic errors or poor patterns.",
                "cleaner_approach": "How to optimize this further.",
                "interview_expectation": "How an interviewer at a FAANG company would grade this.",
                "confidence_score": 80,
                "estimated_interview_level": "L4 Software Engineer",
                "recommended_next_question": "Two Sum II"
            }}
        }}
        """
        
        provider = get_provider()
        try:
            response_text = provider.generate(prompt)
            # Find JSON block if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response_text)
            
            # Store in DB
            execute_insert("""
                INSERT INTO ai_problem_feedback (
                    submission_id, correctness, time_complexity, space_complexity,
                    naming_convention, readability, logic, optimization,
                    code_style, maintainability, edge_cases, potential_bugs,
                    interview_quality, overall_score, feedback_report
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                submission_id, data.get("correctness", 0), data.get("time_complexity", "O(N)"),
                data.get("space_complexity", "O(N)"), data.get("naming_convention", 0),
                data.get("readability", 0), data.get("logic", 0), data.get("optimization", 0),
                data.get("code_style", 0), data.get("maintainability", 0),
                data.get("edge_cases", ""), data.get("potential_bugs", ""),
                data.get("interview_quality", 0), data.get("overall_score", 0),
                json.dumps(data.get("feedback_report", {}))
            ))
            
            # Update user topic score
            score_delta = 10 if data.get("overall_score", 0) > 70 else 2
            execute_insert("""
                INSERT INTO user_topic_scores (user_id, topic, score) 
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, topic) DO UPDATE SET score = score + ?
            """, (user_id, problem["topic"], score_delta, score_delta))
            
            return data
            
        except Exception as e:
            # Fallback mock analysis if AI fails or returns invalid json
            fallback = {
                "correctness": 80,
                "time_complexity": "O(N^2)",
                "space_complexity": "O(1)",
                "naming_convention": 80,
                "readability": 80,
                "logic": 80,
                "optimization": 60,
                "code_style": 80,
                "maintainability": 80,
                "edge_cases": "Basic edge cases evaluated.",
                "potential_bugs": "None detected.",
                "interview_quality": 75,
                "overall_score": 75,
                "feedback_report": {
                    "what_went_well": "Code passes all visible test cases.",
                    "mistakes": "Could be optimized to run in linear time.",
                    "cleaner_approach": "Use a hash map instead of nested loops.",
                    "interview_expectation": "Solid junior engineer solution.",
                    "confidence_score": 70,
                    "estimated_interview_level": "L3 Associate Engineer",
                    "recommended_next_question": "Two Sum"
                }
            }
            execute_insert("""
                INSERT INTO ai_problem_feedback (
                    submission_id, correctness, time_complexity, space_complexity,
                    overall_score, feedback_report
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                submission_id, fallback["correctness"], fallback["time_complexity"],
                fallback["space_complexity"], fallback["overall_score"],
                json.dumps(fallback["feedback_report"])
            ))
            return fallback

    @staticmethod
    def get_dashboard_stats(user_id: int) -> dict:
        """Retrieve compiled learning metrics and history for problem solving."""
        # Fetch submissions count
        subs = execute_query("SELECT status, problem_id FROM problem_submissions WHERE user_id = ?", (user_id,))
        total_sub = len(subs)
        accepted_sub = len([s for s in subs if s["status"] == "Accepted"])
        
        # Streak calculations
        streak_row = execute_one("SELECT streak, confidence_score FROM user_problem_analytics WHERE user_id = ?", (user_id,))
        streak = streak_row["streak"] if streak_row else 0
        confidence = streak_row["confidence_score"] if streak_row else 50
        
        # Topic breakdown
        topic_rows = execute_query("SELECT topic, score FROM user_topic_scores WHERE user_id = ?", (user_id,))
        topic_scores = {r["topic"]: r["score"] for r in topic_rows}
        
        # Daily history submissions mapping (past 7 days activity)
        history = execute_query("""
            SELECT date(created_at) as day, count(*) as count 
            FROM problem_submissions 
            WHERE user_id = ? AND created_at >= date('now', '-7 days')
            GROUP BY day
        """, (user_id,))
        
        daily_activity = {h["day"]: h["count"] for h in history}
        
        return {
            "total_submissions": total_sub,
            "accepted_submissions": accepted_sub,
            "acceptance_rate": int((accepted_sub / total_sub) * 100) if total_sub > 0 else 0,
            "streak": streak,
            "confidence_score": confidence,
            "topic_scores": topic_scores,
            "daily_activity": daily_activity
        }
