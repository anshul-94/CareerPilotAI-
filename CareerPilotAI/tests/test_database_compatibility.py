"""
CareerPilot AI — Comprehensive Database Compatibility & Regression Test Suite
Tests CRUD operations, parameter binding, transactions, rollbacks, and business
logic models across all core modules under SQLite and PostgreSQL.
"""

import os
import unittest
import uuid
import json
import bcrypt

# Ensure testing database path
TEST_DB_PATH = "test_db_compatibility.db"
os.environ["DATABASE_PATH"] = TEST_DB_PATH

from backend.config import Config
Config.DATABASE_PATH = TEST_DB_PATH

from backend.database.schema import init_db
from backend.database.startup import initialize_database
from backend.database.db import (
    execute_query, execute_one, execute_insert, execute_update,
    execute_many, table_exists, get_table_count, adapt_query_placeholders,
    is_postgres
)
from backend.models.user import UserModel
from backend.models.resume import ResumeModel
from backend.models.resume_version import ResumeVersionModel
from backend.models.chat import ChatSessionModel, ChatModel
from backend.models.career_profile import CareerProfileModel
from backend.models.job_notification import JobNotificationModel, AgentProfileModel, AgentRunModel
from backend.models.admin import AdminModel
from backend.services.auth_service import AuthService
from backend.services.admin_service import AdminAuthService, AdminAnalyticsService
from backend.services.problem_service import ProblemService


class DatabaseCompatibilityTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_PATH"] = TEST_DB_PATH
        Config.DATABASE_PATH = TEST_DB_PATH
        if not is_postgres() and os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        initialize_database()

    @classmethod
    def tearDownClass(cls):
        if not is_postgres() and os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def test_01_placeholder_adapter(self):
        """Verify placeholder adaptation from '?' to '%s'."""
        sql_with_params = "SELECT * FROM users WHERE email = ? AND is_active = ?"
        adapted = adapt_query_placeholders(sql_with_params, target_is_postgres=True)
        self.assertEqual(adapted, "SELECT * FROM users WHERE email = %s AND is_active = %s")

        # Test ignoring ? inside literal quotes
        sql_with_literal = "SELECT * FROM users WHERE status = '?' AND email = ?"
        adapted_literal = adapt_query_placeholders(sql_with_literal, target_is_postgres=True)
        self.assertEqual(adapted_literal, "SELECT * FROM users WHERE status = '?' AND email = %s")

    def test_02_user_registration_and_auth(self):
        """Verify user creation, password verification, and retrieval."""
        test_email = f"user_{uuid.uuid4().hex[:8]}@careerpilot.ai"
        test_user = f"user_{uuid.uuid4().hex[:8]}"
        password = "SecurePassword123!"

        success, msg, user_id = AuthService.register(
            username=test_user,
            email=test_email,
            password=password,
            confirm_password=password,
            full_name="Test User"
        )
        self.assertTrue(success, f"Registration failed: {msg}")
        self.assertIsNotNone(user_id)
        self.assertGreater(user_id, 0)

        # Retrieve user
        user = UserModel.get_by_email(test_email)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], test_user)

        # Authenticate password via AuthService
        auth_ok, auth_msg, logged_user = AuthService.login(test_email, password)
        self.assertTrue(auth_ok, f"Login failed: {auth_msg}")
        self.assertEqual(logged_user["id"], user_id)

        # Failed login attempt
        bad_ok, _, _ = AuthService.login(test_email, "WrongPassword")
        self.assertFalse(bad_ok)

        # Profile update
        UserModel.update_profile(user_id, bio="A passionate AI engineer", location="San Francisco")
        updated = UserModel.get_by_id(user_id)
        self.assertEqual(updated["bio"], "A passionate AI engineer")
        self.assertEqual(updated["location"], "San Francisco")

    def test_03_resume_and_version_management(self):
        """Verify resume creation, JSON parsed data, and AI version generation."""
        email = f"resume_{uuid.uuid4().hex[:6]}@careerpilot.ai"
        username = f"res_{uuid.uuid4().hex[:6]}"
        pw = "Password123!"
        ok, _, user_id = AuthService.register(username, email, pw, pw)
        self.assertTrue(ok)

        parsed_json = {"skills": ["Python", "Flask", "PostgreSQL"], "experience": 3}
        resume_id = ResumeModel.create(
            user_id=user_id,
            filename="test_resume.pdf",
            original_name="Original_Resume.pdf",
            raw_text="Experienced Python Flask Developer with SQL expertise.",
            file_size=10240
        )
        self.assertGreater(resume_id, 0)
        ResumeModel.update_parsed_data(resume_id, parsed_json)

        resume = ResumeModel.get_by_id(resume_id)
        self.assertIsNotNone(resume)
        self.assertEqual(resume["user_id"], user_id)
        self.assertIn("Python", resume["raw_text"])

        # Resume Version creation
        version_id = ResumeVersionModel.create(
            user_id=user_id,
            role_target="Senior Software Engineer",
            version_type="tailored",
            content={"summary": "Expert Python Engineer"},
            scores={"ats": 85},
            suggestions=["Add Docker certifications"]
        )
        self.assertGreater(version_id, 0)

        versions = ResumeVersionModel.get_by_user(user_id)
        self.assertGreaterEqual(len(versions), 1)

    def test_04_chat_sessions_and_history(self):
        """Verify chat session creation, message storage, pinning, and retrieval."""
        email = f"chat_{uuid.uuid4().hex[:6]}@careerpilot.ai"
        username = f"chat_{uuid.uuid4().hex[:6]}"
        pw = "Password123!"
        ok, _, user_id = AuthService.register(username, email, pw, pw)
        self.assertTrue(ok)

        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        created_sid = ChatSessionModel.create(session_id, user_id, title="Career Advice Session")
        self.assertEqual(created_sid, session_id)

        session = ChatSessionModel.get(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session["title"], "Career Advice Session")

        # Add messages
        msg_id_1 = ChatModel.create(user_id, session_id, role="user", message="How do I transition to AI?")
        msg_id_2 = ChatModel.create(user_id, session_id, role="assistant", message="Start with Python and PyTorch.")
        self.assertGreater(msg_id_1, 0)
        self.assertGreater(msg_id_2, 0)

        messages = ChatModel.get_session(session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_05_job_notifications_and_agent(self):
        """Verify agent profile, notification generation, and bookmarking."""
        email = f"job_{uuid.uuid4().hex[:6]}@careerpilot.ai"
        username = f"job_{uuid.uuid4().hex[:6]}"
        pw = "Password123!"
        ok, _, user_id = AuthService.register(username, email, pw, pw)
        self.assertTrue(ok)

        profile_id = AgentProfileModel.upsert(
            user_id=user_id,
            profile_data={
                "skills": ["Python", "PostgreSQL"],
                "top_skills": ["Python"],
                "target_roles": ["Backend Developer"]
            }
        )
        self.assertGreater(profile_id, 0)

        notif_id = JobNotificationModel.create(
            user_id=user_id,
            job={
                "title": "Senior Python Backend Developer",
                "company": "Tech Corp",
                "location": "Remote",
                "salary_raw": "$140,000",
                "job_type": "Full-time",
                "apply_link": "https://example.com/job/123",
                "resume_match": 92
            }
        )
        self.assertGreater(notif_id, 0)

        notifs = JobNotificationModel.get_by_user(user_id)
        self.assertGreaterEqual(len(notifs), 1)

        # Update status
        updated_rows = JobNotificationModel.update_status(notif_id, "saved")
        self.assertEqual(updated_rows, 1)

    def test_06_admin_auth_and_analytics(self):
        """Verify admin user seeding, password authentication, and dashboard metric queries."""
        admin = AdminModel.get_by_username("adminuser85")
        self.assertIsNotNone(admin)
        ok, msg, admin_dict = AdminAuthService.login("adminuser85", "adminuser85")
        self.assertTrue(ok, f"Admin login failed: {msg}")

        metrics = AdminAnalyticsService.get_dashboard_metrics()
        self.assertIn("total_users", metrics)
        self.assertIn("active_users", metrics)
        self.assertIn("acceptance_rate", metrics)

        chart_data = AdminAnalyticsService.get_dashboard_chart_data()
        self.assertIn("user_growth", chart_data)
        self.assertIn("submissions_trend", chart_data)

    def test_07_transaction_rollback(self):
        """Verify that transactions safely rollback when a unique constraint fails."""
        duplicate_email = f"tx_{uuid.uuid4().hex[:6]}@careerpilot.ai"
        hash_pw = bcrypt.hashpw(b"test", bcrypt.gensalt()).decode('utf-8')
        UserModel.create(username="unique_tx1", email=duplicate_email, password_hash=hash_pw)

        with self.assertRaises(Exception):
            # Duplicate email must violate unique constraint and trigger rollback
            UserModel.create(username="unique_tx2", email=duplicate_email, password_hash=hash_pw)

    def test_08_table_exists_and_counts(self):
        """Verify table_exists and get_table_count functionality."""
        self.assertTrue(table_exists("users"))
        self.assertTrue(table_exists("resumes"))
        self.assertTrue(table_exists("chat_sessions"))
        self.assertFalse(table_exists("non_existent_table_9999"))
        self.assertGreater(get_table_count("users"), 0)

    def test_09_problem_dashboard_heatmap_and_timeline(self):
        """Verify problem dashboard heatmap and timeline date aggregation queries."""
        test_email = f"prob_user_{uuid.uuid4().hex[:8]}@careerpilot.ai"
        _, _, user_id = AuthService.register(
            username=f"puser_{uuid.uuid4().hex[:8]}",
            email=test_email,
            password="Password123!",
            confirm_password="Password123!",
            full_name="Problem User"
        )
        problem = execute_one("SELECT id FROM problems LIMIT 1")
        problem_id = problem["id"] if problem else 1

        # Insert test submissions: accepted and failed
        execute_insert("""
            INSERT INTO problem_submissions (user_id, problem_id, code, language, status, execution_time, memory, coding_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, problem_id, "def solve(): pass", "python", "Accepted", 45, 1024, "{}"))
        execute_insert("""
            INSERT INTO problem_submissions (user_id, problem_id, code, language, status, execution_time, memory, coding_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, problem_id, "def solve(): pass", "python", "Wrong Answer", 50, 1024, "{}"))

        stats = ProblemService.get_dashboard_stats(user_id)
        self.assertIn("heatmap", stats)
        self.assertIn("timeline", stats)
        self.assertIsInstance(stats["heatmap"], dict)
        self.assertIsInstance(stats["timeline"], list)
        self.assertGreaterEqual(len(stats["heatmap"]), 1)
        self.assertGreaterEqual(len(stats["timeline"]), 1)

        first_timeline = stats["timeline"][0]
        self.assertIn("day", first_timeline)
        self.assertIn("accepted", first_timeline)
        self.assertIn("failed", first_timeline)
        self.assertIsInstance(first_timeline["day"], str)

    def test_10_streak_upsert_rules(self):
        """Verify streak insert and conflict-update paths (initial, same-day, consecutive, missed-day)."""
        test_email = f"streak_{uuid.uuid4().hex[:8]}@careerpilot.ai"
        _, _, user_id = AuthService.register(
            username=f"suser_{uuid.uuid4().hex[:8]}",
            email=test_email,
            password="Password123!",
            confirm_password="Password123!",
            full_name="Streak User"
        )

        def run_streak_upsert(uid):
            if is_postgres():
                sql = """
                    INSERT INTO user_problem_analytics (user_id, streak, last_submission_at)
                    VALUES (?, 1, TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'))
                    ON CONFLICT(user_id) DO UPDATE SET 
                        streak = CASE 
                            WHEN user_problem_analytics.last_submission_at = TO_CHAR(CURRENT_DATE - INTERVAL '1 day', 'YYYY-MM-DD') THEN user_problem_analytics.streak + 1
                            WHEN user_problem_analytics.last_submission_at = TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD') THEN user_problem_analytics.streak
                            ELSE 1
                        END,
                        last_submission_at = TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD')
                """
            else:
                sql = """
                    INSERT INTO user_problem_analytics (user_id, streak, last_submission_at)
                    VALUES (?, 1, date('now'))
                    ON CONFLICT(user_id) DO UPDATE SET 
                        streak = CASE 
                            WHEN last_submission_at = date('now', '-1 day') THEN streak + 1
                            WHEN last_submission_at = date('now') THEN streak
                            ELSE 1
                        END,
                        last_submission_at = date('now')
                """
            execute_update(sql, (uid,))

        # 1. Initial submission: should insert streak = 1
        run_streak_upsert(user_id)
        row = execute_one("SELECT streak, last_submission_at FROM user_problem_analytics WHERE user_id = ?", (user_id,))
        self.assertIsNotNone(row)
        self.assertEqual(row["streak"], 1)

        # 2. Same-day submission: should NOT increment streak (stays 1)
        run_streak_upsert(user_id)
        row = execute_one("SELECT streak FROM user_problem_analytics WHERE user_id = ?", (user_id,))
        self.assertEqual(row["streak"], 1)

        # 3. Consecutive-day submission: simulate yesterday's date
        if is_postgres():
            execute_update("UPDATE user_problem_analytics SET last_submission_at = TO_CHAR(CURRENT_DATE - INTERVAL '1 day', 'YYYY-MM-DD') WHERE user_id = ?", (user_id,))
        else:
            execute_update("UPDATE user_problem_analytics SET last_submission_at = date('now', '-1 day') WHERE user_id = ?", (user_id,))

        run_streak_upsert(user_id)
        row = execute_one("SELECT streak FROM user_problem_analytics WHERE user_id = ?", (user_id,))
        self.assertEqual(row["streak"], 2)

        # Another same-day submission: stays 2
        run_streak_upsert(user_id)
        row = execute_one("SELECT streak FROM user_problem_analytics WHERE user_id = ?", (user_id,))
        self.assertEqual(row["streak"], 2)

        # 4. Missed-day submission: simulate 3 days ago (gap > 1 day)
        if is_postgres():
            execute_update("UPDATE user_problem_analytics SET last_submission_at = TO_CHAR(CURRENT_DATE - INTERVAL '3 days', 'YYYY-MM-DD') WHERE user_id = ?", (user_id,))
        else:
            execute_update("UPDATE user_problem_analytics SET last_submission_at = date('now', '-3 days') WHERE user_id = ?", (user_id,))

        run_streak_upsert(user_id)
        row = execute_one("SELECT streak FROM user_problem_analytics WHERE user_id = ?", (user_id,))
        self.assertEqual(row["streak"], 1)

    def test_11_admin_problem_analytics_grouping(self):
        """Verify admin problem analytics queries with multi-column GROUP BY."""
        rows, highlights, total_count, total_pages = AdminAnalyticsService.get_problems_analytics(page=1, per_page=10)
        self.assertIsInstance(rows, list)
        self.assertIsInstance(highlights, dict)
        self.assertIn("most_attempted", highlights)
        self.assertIn("most_solved", highlights)
        self.assertIn("most_failed", highlights)
        self.assertIn("most_difficult", highlights)
        self.assertGreaterEqual(total_count, 0)
        self.assertGreaterEqual(total_pages, 0)

    def test_12_postgresql_query_syntax_validation(self):
        """Verify that PostgreSQL queries are well-formed and parameter adaptation functions properly."""
        pg_streak = """
            INSERT INTO user_problem_analytics (user_id, streak, last_submission_at)
            VALUES (?, 1, TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'))
            ON CONFLICT(user_id) DO UPDATE SET 
                streak = CASE 
                    WHEN user_problem_analytics.last_submission_at = TO_CHAR(CURRENT_DATE - INTERVAL '1 day', 'YYYY-MM-DD') THEN user_problem_analytics.streak + 1
                    WHEN user_problem_analytics.last_submission_at = TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD') THEN user_problem_analytics.streak
                    ELSE 1
                END,
                last_submission_at = TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD')
        """
        adapted_streak = adapt_query_placeholders(pg_streak, target_is_postgres=True)
        self.assertIn("%s", adapted_streak)
        self.assertNotIn("?", adapted_streak)
        self.assertIn("CURRENT_DATE - INTERVAL '1 day'", adapted_streak)

        pg_heatmap = """
            SELECT TO_CHAR(created_at, 'YYYY-MM-DD') as day, COUNT(*) as count
            FROM problem_submissions
            WHERE user_id = ? AND status = 'Accepted' AND created_at >= CURRENT_DATE - INTERVAL '365 days'
            GROUP BY TO_CHAR(created_at, 'YYYY-MM-DD')
        """
        adapted_heatmap = adapt_query_placeholders(pg_heatmap, target_is_postgres=True)
        self.assertIn("%s", adapted_heatmap)
        self.assertIn("CURRENT_DATE - INTERVAL '365 days'", adapted_heatmap)

    def test_13_round_numeric_type_compatibility(self):
        """
        Verify that acceptance rate, average runtime, and difficulty rate queries
        explicitly cast expressions to NUMERIC before ROUND(..., decimal_places),
        preventing PostgreSQL's 'function round(double precision, integer) does not exist' failure.
        """
        import inspect
        from backend.services.admin_service import AdminAnalyticsService

        src = inspect.getsource(AdminAnalyticsService.get_problems_analytics)

        # 1. Acceptance rate query must cast to NUMERIC before ROUND(..., 1)
        self.assertIn("ROUND(CAST(((CAST(COALESCE(sub.accepted_count, 0) AS REAL) / sub.total_attempts) * 100) AS NUMERIC), 1)", src)

        # 2. Avg runtime query must cast to NUMERIC before ROUND(..., 1)
        self.assertIn("ROUND(CAST(AVG(execution_time) AS NUMERIC), 1)", src)

        # 3. Most difficult highlight query must cast to NUMERIC before ROUND(..., 1)
        self.assertIn("ROUND(CAST(SUM(CASE WHEN ps.status='Accepted' THEN 1.0 ELSE 0.0 END) / COUNT(ps.id) * 100 AS NUMERIC), 1)", src)

        # 4. Verify functional execution on database adapter returns valid numeric results
        rows, highlights, total_count, total_pages = AdminAnalyticsService.get_problems_analytics(page=1, per_page=5)
        self.assertIsInstance(rows, list)
        for r in rows:
            self.assertIn("acceptance_rate", r)
            self.assertIsInstance(r["acceptance_rate"], (int, float))
            self.assertIn("avg_runtime", r)
            self.assertIsInstance(r["avg_runtime"], (int, float))


if __name__ == "__main__":
    unittest.main()

