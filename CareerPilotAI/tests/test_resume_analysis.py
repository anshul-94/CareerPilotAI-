"""
CareerPilot AI — Resume Analysis Regression Tests
Validates target role normalization, error handling, ownership checks,
provider failure paths, and database persistence without making real external API calls.
"""

import os
import unittest
from unittest.mock import patch
import json
import uuid

# Set test database before app imports
os.environ["DATABASE_PATH"] = "test_regression.db"

from app import create_app
from backend.models.user import UserModel
from backend.models.resume import ResumeModel
from backend.models.project import ResumeAnalysisModel
from backend.database.schema import init_db
from backend.config import Config
from backend.services.resume_service import ResumeService


class ResumeAnalysisRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Config.DATABASE_PATH = "test_regression.db"
        if os.path.exists(Config.DATABASE_PATH):
            os.remove(Config.DATABASE_PATH)
        init_db(Config.DATABASE_PATH)

        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            # Create primary test user
            cls.test_email = f"tester_{uuid.uuid4().hex[:6]}@careerpilot.ai"
            cls.test_password = "password123"
            UserModel.create("tester", cls.test_email, cls.test_password, "Regression Tester")
            user1 = UserModel.get_by_email(cls.test_email)
            cls.user1_id = user1["id"]

            # Create secondary user (for ownership check tests)
            cls.user2_email = f"other_{uuid.uuid4().hex[:6]}@careerpilot.ai"
            UserModel.create("other_user", cls.user2_email, cls.test_password, "Other User")
            user2 = UserModel.get_by_email(cls.user2_email)
            cls.user2_id = user2["id"]

            # Create test resume with valid text for user 1
            sample_resume_text = (
                "John Doe\nAI/ML Engineer\n"
                "Experienced machine learning engineer proficient in Python, PyTorch, Scikit-Learn, "
                "NLP, and Computer Vision. Designed and deployed end-to-end recommendation engines, "
                "data pipelines, and transformer models serving 100k daily active users."
            )
            cls.resume1_id = ResumeModel.create(
                user_id=cls.user1_id,
                filename="john_doe_resume.pdf",
                original_name="john_doe_resume.pdf",
                raw_text=sample_resume_text,
                file_size=12345
            )

            # Create test resume with short/empty text for user 1
            cls.short_resume_id = ResumeModel.create(
                user_id=cls.user1_id,
                filename="short_resume.pdf",
                original_name="short_resume.pdf",
                raw_text="Too short",
                file_size=100
            )

            # Create resume owned by user 2
            cls.user2_resume_id = ResumeModel.create(
                user_id=cls.user2_id,
                filename="user2_resume.pdf",
                original_name="user2_resume.pdf",
                raw_text=sample_resume_text,
                file_size=12345
            )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("test_regression.db"):
            os.remove("test_regression.db")

    def setUp(self):
        # Log in as user 1
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1_id
            sess['logged_in'] = True

    @staticmethod
    def _mock_successful_ai_response(target_role: str = ""):
        return {
            "success": True,
            "content": json.dumps({
                "ats_score": 85,
                "strong_skills": ["Python", "PyTorch", "NLP"],
                "weak_skills": ["Docker", "Kubernetes"],
                "missing_keywords": ["MLOps", "CI/CD"],
                "grammar_issues": [],
                "experience_analysis": "Strong production ML experience.",
                "project_analysis": "Good recommendation system projects.",
                "summary": f"Strong candidate for {target_role or 'general'} position.",
                "action_plan": ["Add cloud certification", "Learn Kubernetes"]
            }),
            "metrics": {"total_tokens": 500, "latency_ms": 120},
            "mock": True
        }

    # ── 1. Target Role Normalization & Equivalence Tests ───────────

    @patch("backend.services.ai_service.AIService.chat_completion")
    def test_target_role_whitespace_variations(self, mock_chat):
        """Verify 'AI/ML Engineer' and all its whitespace variations normalize identically."""
        mock_chat.return_value = self._mock_successful_ai_response("AI/ML Engineer")

        variations = [
            "AI/ML Engineer",
            "AI/ML Engineer ",
            " AI/ML Engineer",
            "AI/ML   Engineer",
            "  AI/ML \t  Engineer \n ",
        ]

        observed_prompts = []

        for role in variations:
            res = self.client.post("/resume/analyze/run", json={
                "resume_id": self.resume1_id,
                "target_role": role
            })
            self.assertEqual(res.status_code, 200, f"Failed for variation: {repr(role)}")
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["analysis"]["target_role"], "AI/ML Engineer")

            # Check prompt captured by mock
            args, kwargs = mock_chat.call_args
            system_msg = args[0][0]["content"]
            self.assertIn("targeting the role of AI/ML Engineer and", system_msg)
            self.assertNotIn("targeting the role of AI/ML Engineer  and", system_msg)
            self.assertNotIn("targeting the role of  AI/ML", system_msg)
            observed_prompts.append(system_msg)

        # All variations must produce the exact same system prompt
        self.assertTrue(all(p == observed_prompts[0] for p in observed_prompts))

    @patch("backend.services.ai_service.AIService.chat_completion")
    def test_target_role_empty_and_whitespace_only(self, mock_chat):
        """Verify empty and whitespace-only target roles are normalized to empty."""
        mock_chat.return_value = self._mock_successful_ai_response()

        for empty_val in ["", "   ", "\t\n  ", None]:
            payload = {"resume_id": self.resume1_id}
            if empty_val is not None:
                payload["target_role"] = empty_val

            res = self.client.post("/resume/analyze/run", json=payload)
            self.assertEqual(res.status_code, 200, f"Failed for empty value: {repr(empty_val)}")
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["analysis"]["target_role"], "")

            args, _ = mock_chat.call_args
            system_msg = args[0][0]["content"]
            # When role is empty, 'targeting the role of' should NOT be present
            self.assertNotIn("targeting the role of", system_msg)

    @patch("backend.services.ai_service.AIService.chat_completion")
    def test_different_valid_target_role(self, mock_chat):
        """Verify a different valid role like 'Data Scientist' works correctly."""
        mock_chat.return_value = self._mock_successful_ai_response("Data Scientist")

        res = self.client.post("/resume/analyze/run", json={
            "resume_id": self.resume1_id,
            "target_role": "  Data    Scientist  "
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["analysis"]["target_role"], "Data Scientist")

        args, _ = mock_chat.call_args
        system_msg = args[0][0]["content"]
        self.assertIn("targeting the role of Data Scientist", system_msg)

    # ── 2. Error Handling & Validation Tests ───────────────────────

    def test_invalid_resume_id_types(self):
        """Verify missing, non-integer, or non-positive resume IDs return 400."""
        # Missing resume_id
        res = self.client.post("/resume/analyze/run", json={"target_role": "AI/ML Engineer"})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Non-integer resume_id
        res = self.client.post("/resume/analyze/run", json={"resume_id": "abc"})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Non-positive resume_id
        res = self.client.post("/resume/analyze/run", json={"resume_id": -5})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

    def test_nonexistent_resume_id(self):
        """Verify non-existent resume returns 404."""
        res = self.client.post("/resume/analyze/run", json={"resume_id": 99999})
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.get_json()["error"].lower())

    def test_ownership_enforcement(self):
        """Verify a user cannot analyze another user's resume (returns 403)."""
        res = self.client.post("/resume/analyze/run", json={
            "resume_id": self.user2_resume_id,
            "target_role": "AI/ML Engineer"
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("permission", res.get_json()["error"].lower())

    def test_missing_or_short_resume_text(self):
        """Verify resumes with insufficient text return 400 with a clear error."""
        res = self.client.post("/resume/analyze/run", json={
            "resume_id": self.short_resume_id,
            "target_role": "AI/ML Engineer"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("too short", res.get_json()["error"].lower())

    # ── 3. AI Provider Failure Paths (Controlled Mocks) ────────────

    @patch("backend.services.ai_service.AIService.chat_completion")
    def test_provider_rate_limit_failure(self, mock_chat):
        """Verify rate limit errors return 502 with helpful user message."""
        mock_chat.return_value = {
            "success": False,
            "error": "Groq API error 429: rate_limit_exceeded"
        }
        res = self.client.post("/resume/analyze/run", json={
            "resume_id": self.resume1_id,
            "target_role": "AI/ML Engineer"
        })
        self.assertEqual(res.status_code, 502)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("rate limit", data["error"].lower())

    @patch("backend.services.ai_service.AIService.chat_completion")
    def test_provider_timeout_failure(self, mock_chat):
        """Verify request timeout returns 502 with friendly message."""
        mock_chat.return_value = {
            "success": False,
            "error": "Request timed out after 60s"
        }
        res = self.client.post("/resume/analyze/run", json={
            "resume_id": self.resume1_id,
            "target_role": "AI/ML Engineer"
        })
        self.assertEqual(res.status_code, 502)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("timed out", data["error"].lower())

    @patch("backend.services.ai_service.AIService.chat_completion")
    def test_provider_invalid_json_response(self, mock_chat):
        """Verify unparseable AI output is handled safely without fake success."""
        mock_chat.return_value = {
            "success": True,
            "content": "Sorry, I cannot analyze this as requested."
        }
        res = self.client.post("/resume/analyze/run", json={
            "resume_id": self.resume1_id,
            "target_role": "AI/ML Engineer"
        })
        self.assertEqual(res.status_code, 500)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("parse", data["error"].lower())

    # ── 4. Database Persistence ───────────────────────────────────

    @patch("backend.services.ai_service.AIService.chat_completion")
    def test_database_persistence_on_success(self, mock_chat):
        """Verify successful analysis is correctly stored in the resume_analysis table."""
        mock_chat.return_value = self._mock_successful_ai_response("AI/ML Engineer")

        res = self.client.post("/resume/analyze/run", json={
            "resume_id": self.resume1_id,
            "target_role": "AI/ML Engineer"
        })
        self.assertEqual(res.status_code, 200)

        latest_analysis = ResumeAnalysisModel.get_by_resume(self.resume1_id)
        self.assertIsNotNone(latest_analysis)
        self.assertEqual(latest_analysis["ats_score"], 85)
        self.assertEqual(latest_analysis["user_id"], self.user1_id)


if __name__ == "__main__":
    unittest.main()
