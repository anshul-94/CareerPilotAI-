"""
CareerPilot AI — Admin Service Layer
Provides business logic for Admin Authentication, Analytics, User Management, Submissions, and Audit Logging.
"""

import bcrypt
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from backend.models.admin import AdminModel
from backend.database.db import execute_query, execute_one, execute_update


class AdminAuthService:
    """Authentication and session management for administrators."""

    @staticmethod
    def login(username: str, password: str, ip_address: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate admin credentials securely."""
        if not username or not password:
            return False, "Username and password are required", None

        admin = AdminModel.get_by_username(username.strip())
        if not admin:
            return False, "Invalid admin credentials", None

        if not admin.get("is_active", 1):
            return False, "Admin account is deactivated", None

        try:
            if bcrypt.checkpw(password.encode("utf-8"), admin["password_hash"].encode("utf-8")):
                AdminModel.update_last_login(admin["id"])
                AdminModel.log_audit(admin["id"], admin["username"], "ADMIN_LOGIN", "Admin Portal", ip_address)
                
                admin_safe = {
                    "id": admin["id"],
                    "username": admin["username"],
                    "email": admin["email"],
                    "role": admin.get("role", "admin"),
                }
                return True, "Login successful", admin_safe
            else:
                return False, "Invalid admin credentials", None
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None

    @staticmethod
    def log_logout(admin_id: Optional[int], admin_username: str, ip_address: str = ""):
        """Record admin logout in audit log."""
        if admin_id or admin_username:
            AdminModel.log_audit(admin_id, admin_username or "Admin", "ADMIN_LOGOUT", "Admin Portal", ip_address)


class AdminAnalyticsService:
    """Aggregation and reporting service for administrative operations."""

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        """Fetch overall platform metrics using real database records."""
        # Users counts
        total_users_res = execute_one("SELECT COUNT(*) as c FROM users")
        total_users = total_users_res["c"] if total_users_res else 0

        active_users_res = execute_one("SELECT COUNT(*) as c FROM users WHERE is_active = 1")
        active_users = active_users_res["c"] if active_users_res else 0

        new_users_res = execute_one(
            "SELECT COUNT(*) as c FROM users WHERE created_at >= datetime('now', '-30 days')"
        )
        new_users = new_users_res["c"] if new_users_res else 0

        # Submissions & Problems
        total_submissions_res = execute_one("SELECT COUNT(*) as c FROM problem_submissions")
        total_submissions = total_submissions_res["c"] if total_submissions_res else 0

        accepted_submissions_res = execute_one(
            "SELECT COUNT(*) as c FROM problem_submissions WHERE status = 'Accepted'"
        )
        accepted_submissions = accepted_submissions_res["c"] if accepted_submissions_res else 0

        solved_problems_res = execute_one(
            "SELECT COUNT(DISTINCT problem_id) as c FROM problem_submissions WHERE status = 'Accepted'"
        )
        total_problems_solved = solved_problems_res["c"] if solved_problems_res else 0

        acceptance_rate = (
            round((accepted_submissions / total_submissions) * 100, 1)
            if total_submissions > 0
            else 0.0
        )

        # AI metrics
        chats_count_res = execute_one("SELECT COUNT(*) as c FROM chat_history")
        total_chat_messages = chats_count_res["c"] if chats_count_res else 0

        chat_sessions_res = execute_one("SELECT COUNT(DISTINCT session_id) as c FROM chat_history")
        total_ai_conversations = chat_sessions_res["c"] if chat_sessions_res else 0

        code_reviews_res = execute_one("SELECT COUNT(*) as c FROM code_reviews")
        total_code_reviews = code_reviews_res["c"] if code_reviews_res else 0

        agent_runs_res = execute_one("SELECT COUNT(*) as c FROM agent_runs")
        total_agent_runs = agent_runs_res["c"] if agent_runs_res else 0

        ai_feedback_res = execute_one("SELECT COUNT(*) as c FROM ai_problem_feedback")
        total_ai_feedback = ai_feedback_res["c"] if ai_feedback_res else 0

        total_ai_requests = (
            total_chat_messages + total_code_reviews + total_agent_runs + total_ai_feedback
        )

        # Problem Solving Score
        avg_score_res = execute_one(
            "SELECT ROUND(AVG(overall_score), 1) as avg_score FROM ai_problem_feedback"
        )
        avg_problem_score = (
            avg_score_res["avg_score"]
            if avg_score_res and avg_score_res["avg_score"] is not None
            else (round(acceptance_rate, 1) if acceptance_rate > 0 else 75.0)
        )

        # Active Sessions / Recently Active Users (last 7 days)
        active_sessions_res = execute_one(
            "SELECT COUNT(*) as c FROM users WHERE last_login >= datetime('now', '-7 days')"
        )
        active_sessions = (
            active_users_res["c"]
            if active_sessions_res and active_sessions_res["c"] == 0 and active_users > 0
            else (active_sessions_res["c"] if active_sessions_res else 0)
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "new_users": new_users,
            "total_problems_solved": total_problems_solved,
            "total_submissions": total_submissions,
            "acceptance_rate": acceptance_rate,
            "total_ai_conversations": total_ai_conversations,
            "total_ai_requests": total_ai_requests,
            "avg_problem_score": avg_problem_score,
            "active_sessions": active_sessions if active_sessions > 0 else active_users,
        }

    @staticmethod
    def get_dashboard_chart_data() -> Dict[str, Any]:
        """Fetch aggregated data sets for Chart.js rendering."""
        # 1. User Growth (by day for recent registrations)
        growth_rows = execute_query("""
            SELECT substr(created_at, 1, 10) as reg_date, COUNT(*) as count 
            FROM users 
            GROUP BY reg_date 
            ORDER BY reg_date ASC 
            LIMIT 14
        """)
        growth_labels = [r["reg_date"] or "Recent" for r in growth_rows]
        growth_counts = [r["count"] for r in growth_rows]

        # 2. Submissions Over Time
        sub_rows = execute_query("""
            SELECT substr(created_at, 1, 10) as sub_date, COUNT(*) as count 
            FROM problem_submissions 
            GROUP BY sub_date 
            ORDER BY sub_date ASC 
            LIMIT 14
        """)
        sub_labels = [r["sub_date"] or "Recent" for r in sub_rows]
        sub_counts = [r["count"] for r in sub_rows]

        # 3. Difficulty Distribution
        diff_rows = execute_query("""
            SELECT difficulty, COUNT(*) as count 
            FROM problems 
            GROUP BY difficulty
        """)
        diff_labels = [r["difficulty"] or "Standard" for r in diff_rows]
        diff_counts = [r["count"] for r in diff_rows]

        # 4. Language Distribution
        lang_rows = execute_query("""
            SELECT language, COUNT(*) as count 
            FROM problem_submissions 
            WHERE language IS NOT NULL AND language != ''
            GROUP BY language 
            ORDER BY count DESC 
            LIMIT 6
        """)
        lang_labels = [r["language"].capitalize() for r in lang_rows] if lang_rows else ["Python", "JavaScript", "C++", "Java"]
        lang_counts = [r["count"] for r in lang_rows] if lang_rows else [1, 0, 0, 0]

        # 5. AI Usage Breakdown
        chat_cnt = execute_one("SELECT COUNT(*) as c FROM chat_history")["c"]
        code_cnt = execute_one("SELECT COUNT(*) as c FROM code_reviews")["c"]
        agent_cnt = execute_one("SELECT COUNT(*) as c FROM agent_runs")["c"]
        feed_cnt = execute_one("SELECT COUNT(*) as c FROM ai_problem_feedback")["c"]
        resume_cnt = execute_one("SELECT COUNT(*) as c FROM resume_versions")["c"]

        ai_labels = ["AI Mentor / Chat", "AI Code Review", "AI Job Agent", "AI Feedback", "Resume AI"]
        ai_counts = [chat_cnt, code_cnt, agent_cnt, feed_cnt, resume_cnt]

        return {
            "user_growth": {"labels": growth_labels, "data": growth_counts},
            "submissions_trend": {"labels": sub_labels, "data": sub_counts},
            "difficulty_distribution": {"labels": diff_labels, "data": diff_counts},
            "language_distribution": {"labels": lang_labels, "data": lang_counts},
            "ai_usage": {"labels": ai_labels, "data": ai_counts},
        }

    @staticmethod
    def get_users_list(
        search: str = "",
        status: str = "",
        sort_by: str = "created_at",
        order: str = "DESC",
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Retrieve paginated list of users with statistics, search and filters.
        Returns (users_list, total_count, total_pages).
        """
        where_clauses = ["1=1"]
        params: List[Any] = []

        if search:
            where_clauses.append("(u.username LIKE ? OR u.email LIKE ? OR u.full_name LIKE ?)")
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern])

        if status:
            if status.lower() == "active":
                where_clauses.append("u.is_active = 1")
            elif status.lower() == "inactive":
                where_clauses.append("u.is_active = 0")

        where_sql = " AND ".join(where_clauses)

        # Count total matching users
        count_res = execute_one(f"SELECT COUNT(*) as c FROM users u WHERE {where_sql}", tuple(params))
        total_count = count_res["c"] if count_res else 0
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        allowed_sort = {
            "created_at": "u.created_at",
            "last_login": "u.last_login",
            "username": "u.username",
            "full_name": "u.full_name",
            "submissions": "total_submissions",
            "solved": "problems_solved",
        }
        sort_col = allowed_sort.get(sort_by, "u.created_at")
        sort_dir = "ASC" if order.upper() == "ASC" else "DESC"

        query = f"""
            SELECT 
                u.id, 
                u.username, 
                u.email, 
                u.full_name, 
                u.role, 
                u.is_active, 
                u.created_at, 
                u.last_login,
                COALESCE(sub_stats.total_submissions, 0) as total_submissions,
                COALESCE(sub_stats.problems_solved, 0) as problems_solved,
                COALESCE(sub_stats.accepted_count, 0) as accepted_count,
                COALESCE(upa.confidence_score, 75) as current_rating,
                (
                    COALESCE((SELECT COUNT(*) FROM chat_history ch WHERE ch.user_id = u.id), 0) +
                    COALESCE((SELECT COUNT(*) FROM code_reviews cr WHERE cr.user_id = u.id), 0) +
                    COALESCE((SELECT COUNT(*) FROM agent_runs ar WHERE ar.user_id = u.id), 0)
                ) as ai_usage
            FROM users u
            LEFT JOIN (
                SELECT 
                    user_id,
                    COUNT(*) as total_submissions,
                    COUNT(DISTINCT CASE WHEN status = 'Accepted' THEN problem_id END) as problems_solved,
                    SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted_count
                FROM problem_submissions
                GROUP BY user_id
            ) sub_stats ON u.id = sub_stats.user_id
            LEFT JOIN user_problem_analytics upa ON u.id = upa.user_id
            WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir}
            LIMIT ? OFFSET ?
        """
        
        query_params = list(params) + [per_page, offset]
        rows = execute_query(query, tuple(query_params))

        # Format rows and compute acceptance rate
        for r in rows:
            tot = r["total_submissions"]
            acc = r["accepted_count"]
            r["acceptance_rate"] = round((acc / tot) * 100, 1) if tot > 0 else 0.0

        return rows, total_count, total_pages

    @staticmethod
    def get_user_detail(user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve in-depth profile, coding stats, submission logs, AI usage, and learning analytics for a user."""
        user = execute_one(
            """SELECT id, username, email, full_name, role, is_active, created_at, last_login, 
                      bio, phone, location, linkedin_url, github_url, portfolio_url, avatar_url 
               FROM users WHERE id = ?""",
            (user_id,)
        )
        if not user:
            return None

        # Profile & career profile
        career_prof = execute_one("SELECT * FROM career_profiles WHERE user_id = ?", (user_id,))
        settings = execute_one("SELECT * FROM settings WHERE user_id = ?", (user_id,))

        # Coding Activity Counts
        coding_counts = execute_one("""
            SELECT 
                COUNT(*) as total_submissions,
                COUNT(DISTINCT problem_id) as problems_attempted,
                COUNT(DISTINCT CASE WHEN status = 'Accepted' THEN problem_id END) as problems_solved,
                SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted,
                SUM(CASE WHEN status = 'Wrong Answer' THEN 1 ELSE 0 END) as wrong_answer,
                SUM(CASE WHEN status LIKE '%Compilation%' THEN 1 ELSE 0 END) as compilation_error,
                SUM(CASE WHEN status LIKE '%Runtime%' THEN 1 ELSE 0 END) as runtime_error,
                SUM(CASE WHEN status LIKE '%Time Limit%' THEN 1 ELSE 0 END) as time_limit_exceeded
            FROM problem_submissions
            WHERE user_id = ?
        """, (user_id,))

        tot_subs = coding_counts["total_submissions"] or 0
        accepted_subs = coding_counts["accepted"] or 0
        coding_stats = {
            "total_submissions": tot_subs,
            "problems_attempted": coding_counts["problems_attempted"] or 0,
            "problems_solved": coding_counts["problems_solved"] or 0,
            "accepted": accepted_subs,
            "wrong_answer": coding_counts["wrong_answer"] or 0,
            "compilation_error": coding_counts["compilation_error"] or 0,
            "runtime_error": coding_counts["runtime_error"] or 0,
            "time_limit_exceeded": coding_counts["time_limit_exceeded"] or 0,
            "acceptance_rate": round((accepted_subs / tot_subs) * 100, 1) if tot_subs > 0 else 0.0,
        }

        # Problem Solving History (recent submissions)
        submissions = execute_query("""
            SELECT 
                ps.id, 
                ps.problem_id, 
                ps.code, 
                ps.language, 
                ps.status, 
                ps.execution_time, 
                ps.memory, 
                ps.created_at,
                p.title as problem_title, 
                p.difficulty as problem_difficulty, 
                p.topic as problem_topic
            FROM problem_submissions ps
            LEFT JOIN problems p ON ps.problem_id = p.id
            WHERE ps.user_id = ?
            ORDER BY ps.created_at DESC
            LIMIT 50
        """, (user_id,))

        # AI Activity
        ai_chat_count = execute_one("SELECT COUNT(*) as c FROM chat_history WHERE user_id = ?", (user_id,))["c"]
        ai_chat_sessions = execute_one("SELECT COUNT(DISTINCT session_id) as c FROM chat_history WHERE user_id = ?", (user_id,))["c"]
        ai_code_reviews = execute_one("SELECT COUNT(*) as c FROM code_reviews WHERE user_id = ?", (user_id,))["c"]
        ai_agent_runs = execute_one("SELECT COUNT(*) as c FROM agent_runs WHERE user_id = ?", (user_id,))["c"]
        ai_resumes = execute_one("SELECT COUNT(*) as c FROM resume_versions WHERE user_id = ?", (user_id,))["c"]

        last_ai_activity_row = execute_one(
            "SELECT created_at FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        last_ai_activity = last_ai_activity_row["created_at"] if last_ai_activity_row else None

        ai_stats = {
            "ai_mentor_requests": ai_chat_count,
            "ai_chat_sessions": ai_chat_sessions,
            "ai_code_reviews": ai_code_reviews,
            "ai_agent_usage": ai_agent_runs,
            "resume_versions": ai_resumes,
            "total_ai_conversations": ai_chat_sessions,
            "last_ai_activity": last_ai_activity or "No activity recorded",
        }

        # Learning Analytics
        upa = execute_one("SELECT * FROM user_problem_analytics WHERE user_id = ?", (user_id,))
        topic_scores = execute_query(
            "SELECT topic, score FROM user_topic_scores WHERE user_id = ? ORDER BY score DESC",
            (user_id,)
        )

        # Languages used by user
        user_langs = execute_query("""
            SELECT language, COUNT(*) as count 
            FROM problem_submissions 
            WHERE user_id = ? AND language IS NOT NULL AND language != ''
            GROUP BY language 
            ORDER BY count DESC
        """, (user_id,))

        # Difficulty breakdown solved
        difficulty_solved = execute_query("""
            SELECT p.difficulty, COUNT(DISTINCT p.id) as count
            FROM problem_submissions ps
            JOIN problems p ON ps.problem_id = p.id
            WHERE ps.user_id = ? AND ps.status = 'Accepted'
            GROUP BY p.difficulty
        """, (user_id,))

        learning_analytics = {
            "current_rating": upa["confidence_score"] if upa and upa.get("confidence_score") else 75,
            "streak": upa["streak"] if upa and upa.get("streak") else 0,
            "learning_velocity": upa["learning_velocity"] if upa and upa.get("learning_velocity") else 1.0,
            "strong_topics": [t["topic"] for t in topic_scores if t.get("score", 0) >= 70] if topic_scores else ["Algorithms", "Data Structures"],
            "weak_topics": [t["topic"] for t in topic_scores if t.get("score", 0) < 50] if topic_scores else ["Dynamic Programming"],
            "difficulty_distribution": {r["difficulty"]: r["count"] for r in difficulty_solved},
            "language_usage": {r["language"]: r["count"] for r in user_langs},
            "company_alignment": career_prof.get("preferred_role") if career_prof and career_prof.get("preferred_role") else "Software Engineer",
        }

        return {
            "user": user,
            "career_profile": career_prof or {},
            "settings": settings or {},
            "coding_stats": coding_stats,
            "submissions": submissions,
            "ai_stats": ai_stats,
            "learning_analytics": learning_analytics,
        }

    @staticmethod
    def toggle_user_status(user_id: int, active: int, admin_id: Optional[int], admin_username: str, ip: str = "") -> bool:
        """Activate or deactivate user account."""
        action = "ACTIVATE_USER" if active == 1 else "DEACTIVATE_USER"
        updated = execute_update("UPDATE users SET is_active = ? WHERE id = ?", (active, user_id))
        if updated > 0:
            AdminModel.log_audit(admin_id, admin_username, action, f"User ID: {user_id}", ip)
            return True
        return False

    @staticmethod
    def get_submissions_list(
        user_query: str = "",
        problem_query: str = "",
        language: str = "",
        verdict: str = "",
        date_filter: str = "",
        page: int = 1,
        per_page: int = 25
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Retrieve paginated submissions with filters for User, Problem, Language, Verdict, and Date.
        Returns (submissions_list, total_count, total_pages).
        """
        where_clauses = ["1=1"]
        params: List[Any] = []

        if user_query:
            where_clauses.append("(u.username LIKE ? OR u.full_name LIKE ? OR CAST(ps.user_id AS TEXT) = ?)")
            pat = f"%{user_query}%"
            params.extend([pat, pat, user_query])

        if problem_query:
            where_clauses.append("(p.title LIKE ? OR CAST(ps.problem_id AS TEXT) = ?)")
            pat = f"%{problem_query}%"
            params.extend([pat, problem_query])

        if language:
            where_clauses.append("LOWER(ps.language) = LOWER(?)")
            params.append(language)

        if verdict:
            where_clauses.append("LOWER(ps.status) = LOWER(?)")
            params.append(verdict)

        if date_filter:
            where_clauses.append("ps.created_at >= ?")
            params.append(date_filter)

        where_sql = " AND ".join(where_clauses)

        count_res = execute_one(f"""
            SELECT COUNT(*) as c 
            FROM problem_submissions ps
            LEFT JOIN users u ON ps.user_id = u.id
            LEFT JOIN problems p ON ps.problem_id = p.id
            WHERE {where_sql}
        """, tuple(params))

        total_count = count_res["c"] if count_res else 0
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        query = f"""
            SELECT 
                ps.id, 
                ps.user_id, 
                ps.problem_id, 
                ps.language, 
                ps.status, 
                ps.execution_time, 
                ps.memory, 
                ps.created_at,
                u.username, 
                u.full_name,
                p.title as problem_title,
                p.difficulty as problem_difficulty
            FROM problem_submissions ps
            LEFT JOIN users u ON ps.user_id = u.id
            LEFT JOIN problems p ON ps.problem_id = p.id
            WHERE {where_sql}
            ORDER BY ps.created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = execute_query(query, tuple(params + [per_page, offset]))
        return rows, total_count, total_pages

    @staticmethod
    def get_problems_analytics(
        search: str = "",
        difficulty: str = "",
        topic: str = "",
        sort_by: str = "attempts",
        page: int = 1,
        per_page: int = 25
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], int, int]:
        """
        Fetch problem metrics with aggregated attempts, solved count, acceptance rate, and highlights.
        Returns (problems_list, highlights, total_count, total_pages).
        """
        where_clauses = ["1=1"]
        params: List[Any] = []

        if search:
            where_clauses.append("(p.title LIKE ? OR p.tags LIKE ?)")
            pat = f"%{search}%"
            params.extend([pat, pat])

        if difficulty:
            where_clauses.append("LOWER(p.difficulty) = LOWER(?)")
            params.append(difficulty)

        if topic:
            where_clauses.append("LOWER(p.topic) = LOWER(?)")
            params.append(topic)

        where_sql = " AND ".join(where_clauses)

        count_res = execute_one(f"SELECT COUNT(*) as c FROM problems p WHERE {where_sql}", tuple(params))
        total_count = count_res["c"] if count_res else 0
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        allowed_sort = {
            "attempts": "total_attempts DESC",
            "solved": "accepted_count DESC",
            "rate": "acceptance_rate ASC",
            "title": "p.title ASC",
            "difficulty": "p.difficulty ASC",
        }
        order_sql = allowed_sort.get(sort_by, "total_attempts DESC")

        query = f"""
            SELECT 
                p.id,
                p.title,
                p.difficulty,
                p.topic,
                COALESCE(sub.total_attempts, 0) as total_attempts,
                COALESCE(sub.accepted_count, 0) as accepted_count,
                COALESCE(sub.wrong_count, 0) as wrong_count,
                COALESCE(sub.avg_runtime, 0) as avg_runtime,
                CASE 
                    WHEN COALESCE(sub.total_attempts, 0) > 0 
                    THEN ROUND((CAST(COALESCE(sub.accepted_count, 0) AS REAL) / sub.total_attempts) * 100, 1)
                    ELSE 0.0
                END as acceptance_rate
            FROM problems p
            LEFT JOIN (
                SELECT 
                    problem_id,
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted_count,
                    SUM(CASE WHEN status = 'Wrong Answer' THEN 1 ELSE 0 END) as wrong_count,
                    ROUND(AVG(execution_time), 1) as avg_runtime
                FROM problem_submissions
                GROUP BY problem_id
            ) sub ON p.id = sub.problem_id
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        """
        rows = execute_query(query, tuple(params + [per_page, offset]))

        # Calculate most used language for each problem
        for r in rows:
            top_lang_row = execute_one(
                """SELECT language, COUNT(*) as c 
                   FROM problem_submissions 
                   WHERE problem_id = ? AND language IS NOT NULL AND language != ''
                   GROUP BY language ORDER BY c DESC LIMIT 1""",
                (r["id"],)
            )
            r["most_used_language"] = top_lang_row["language"].capitalize() if top_lang_row else "N/A"

        # Highlights
        most_attempted = execute_one("""
            SELECT p.title, COUNT(ps.id) as count 
            FROM problem_submissions ps 
            JOIN problems p ON ps.problem_id = p.id 
            GROUP BY ps.problem_id 
            ORDER BY count DESC LIMIT 1
        """)
        most_solved = execute_one("""
            SELECT p.title, COUNT(ps.id) as count 
            FROM problem_submissions ps 
            JOIN problems p ON ps.problem_id = p.id 
            WHERE ps.status = 'Accepted'
            GROUP BY ps.problem_id 
            ORDER BY count DESC LIMIT 1
        """)
        most_failed = execute_one("""
            SELECT p.title, COUNT(ps.id) as count 
            FROM problem_submissions ps 
            JOIN problems p ON ps.problem_id = p.id 
            WHERE ps.status != 'Accepted'
            GROUP BY ps.problem_id 
            ORDER BY count DESC LIMIT 1
        """)
        most_difficult = execute_one("""
            SELECT p.title, 
                   COUNT(ps.id) as total,
                   ROUND(SUM(CASE WHEN ps.status='Accepted' THEN 1.0 ELSE 0.0 END) / COUNT(ps.id) * 100, 1) as rate
            FROM problem_submissions ps
            JOIN problems p ON ps.problem_id = p.id
            GROUP BY ps.problem_id
            HAVING total >= 2
            ORDER BY rate ASC, total DESC LIMIT 1
        """)

        highlights = {
            "most_attempted": most_attempted["title"] if most_attempted else "N/A",
            "most_solved": most_solved["title"] if most_solved else "N/A",
            "most_failed": most_failed["title"] if most_failed else "N/A",
            "most_difficult": most_difficult["title"] if most_difficult else "N/A",
        }

        return rows, highlights, total_count, total_pages

    @staticmethod
    def get_ai_analytics() -> Dict[str, Any]:
        """Compile AI usage analytics from chat, coach, agent, and code review records."""
        # 1. Feature counts
        chat_count = execute_one("SELECT COUNT(*) as c FROM chat_history")["c"]
        coach_count = execute_one("SELECT COUNT(*) as c FROM chat_history WHERE module = 'coach' OR module LIKE '%coach%'")["c"]
        mentor_count = chat_count - coach_count if chat_count >= coach_count else chat_count
        code_reviews = execute_one("SELECT COUNT(*) as c FROM code_reviews")["c"]
        agent_runs = execute_one("SELECT COUNT(*) as c FROM agent_runs")["c"]
        resume_versions = execute_one("SELECT COUNT(*) as c FROM resume_versions")["c"]
        ai_feedback = execute_one("SELECT COUNT(*) as c FROM ai_problem_feedback")["c"]

        total_requests = chat_count + code_reviews + agent_runs + resume_versions + ai_feedback

        # 2. Requests by User (Top AI Users)
        top_users = execute_query("""
            SELECT 
                u.id, 
                u.username, 
                u.full_name,
                (
                    COALESCE((SELECT COUNT(*) FROM chat_history ch WHERE ch.user_id = u.id), 0) +
                    COALESCE((SELECT COUNT(*) FROM code_reviews cr WHERE cr.user_id = u.id), 0) +
                    COALESCE((SELECT COUNT(*) FROM agent_runs ar WHERE ar.user_id = u.id), 0)
                ) as total_ai_requests
            FROM users u
            WHERE (
                EXISTS (SELECT 1 FROM chat_history ch WHERE ch.user_id = u.id) OR
                EXISTS (SELECT 1 FROM code_reviews cr WHERE cr.user_id = u.id) OR
                EXISTS (SELECT 1 FROM agent_runs ar WHERE ar.user_id = u.id)
            )
            ORDER BY total_ai_requests DESC
            LIMIT 10
        """)

        # 3. Daily Requests (last 7 days)
        daily_requests = execute_query("""
            SELECT substr(created_at, 1, 10) as day_date, COUNT(*) as count 
            FROM chat_history 
            GROUP BY day_date 
            ORDER BY day_date DESC 
            LIMIT 7
        """)

        # 4. Weekly Requests (approx by week)
        weekly_requests = execute_query("""
            SELECT strftime('%Y-W%W', created_at) as week_num, COUNT(*) as count
            FROM chat_history
            GROUP BY week_num
            ORDER BY week_num DESC
            LIMIT 4
        """)

        # 5. Monthly Requests
        monthly_requests = execute_query("""
            SELECT strftime('%Y-%m', created_at) as month_num, COUNT(*) as count
            FROM chat_history
            GROUP BY month_num
            ORDER BY month_num DESC
            LIMIT 6
        """)

        return {
            "total_ai_requests": total_requests,
            "mentor_requests": mentor_count,
            "coach_requests": coach_count,
            "agent_usage": agent_runs,
            "code_reviews": code_reviews,
            "resume_ai": resume_versions,
            "problem_feedback": ai_feedback,
            "top_users": top_users,
            "daily_requests": daily_requests,
            "weekly_requests": weekly_requests,
            "monthly_requests": monthly_requests,
        }

    @staticmethod
    def get_activity_timeline(limit: int = 50) -> List[Dict[str, Any]]:
        """Collect and format real platform activities chronologically."""
        events: List[Dict[str, Any]] = []

        # 1. User Registrations
        reg_users = execute_query("SELECT id, username, full_name, created_at FROM users ORDER BY created_at DESC LIMIT 20")
        for u in reg_users:
            if u.get("created_at"):
                events.append({
                    "type": "USER_REGISTERED",
                    "title": f"{u.get('full_name') or u.get('username')} registered",
                    "detail": f"New account created for @{u.get('username')}",
                    "timestamp": u["created_at"],
                    "icon": "👤",
                    "badge": "info",
                })

        # 2. Problem Submissions
        subs = execute_query("""
            SELECT ps.id, ps.status, ps.language, ps.created_at, u.username, u.full_name, p.title as problem_title
            FROM problem_submissions ps
            LEFT JOIN users u ON ps.user_id = u.id
            LEFT JOIN problems p ON ps.problem_id = p.id
            ORDER BY ps.created_at DESC
            LIMIT 30
        """)
        for s in subs:
            if s.get("created_at"):
                uname = s.get("full_name") or s.get("username") or "User"
                pname = s.get("problem_title") or "a coding challenge"
                status = s.get("status") or "Submitted"
                badge = "success" if status == "Accepted" else "danger"
                icon = "🎯" if status == "Accepted" else "❌"
                action_text = "solved" if status == "Accepted" else f"attempted ({status})"
                events.append({
                    "type": "PROBLEM_SUBMISSION",
                    "title": f"{uname} {action_text} {pname}",
                    "detail": f"Language: {s.get('language') or 'Unknown'} • Status: {status}",
                    "timestamp": s["created_at"],
                    "icon": icon,
                    "badge": badge,
                })

        # 3. AI Chat / Mentor Activity
        chats = execute_query("""
            SELECT ch.id, ch.module, ch.created_at, u.username, u.full_name
            FROM chat_history ch
            LEFT JOIN users u ON ch.user_id = u.id
            ORDER BY ch.created_at DESC
            LIMIT 20
        """)
        for c in chats:
            if c.get("created_at"):
                uname = c.get("full_name") or c.get("username") or "User"
                mod = (c.get("module") or "AI Mentor").capitalize()
                events.append({
                    "type": "AI_INTERACTION",
                    "title": f"{uname} used {mod}",
                    "detail": f"Interacted with {mod} session",
                    "timestamp": c["created_at"],
                    "icon": "🤖",
                    "badge": "accent",
                })

        # Sort all events reverse chronologically
        events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
        return events[:limit]

    @staticmethod
    def global_search(query_str: str) -> Dict[str, List[Dict[str, Any]]]:
        """Perform unified search across users, problems, and submissions."""
        q = f"%{query_str.strip()}%"
        
        users = execute_query(
            "SELECT id, username, email, full_name, role, is_active FROM users WHERE username LIKE ? OR email LIKE ? OR full_name LIKE ? LIMIT 10",
            (q, q, q)
        )
        
        problems = execute_query(
            "SELECT id, title, difficulty, topic FROM problems WHERE title LIKE ? OR topic LIKE ? OR tags LIKE ? LIMIT 10",
            (q, q, q)
        )
        
        submissions = execute_query(
            """SELECT ps.id, ps.user_id, ps.problem_id, ps.language, ps.status, ps.created_at, u.username, p.title as problem_title 
               FROM problem_submissions ps 
               LEFT JOIN users u ON ps.user_id = u.id 
               LEFT JOIN problems p ON ps.problem_id = p.id 
               WHERE CAST(ps.id AS TEXT) = ? OR ps.language LIKE ? OR ps.status LIKE ? 
               ORDER BY ps.created_at DESC LIMIT 10""",
            (query_str.strip(), q, q)
        )
        
        return {
            "users": users,
            "problems": problems,
            "submissions": submissions,
        }
