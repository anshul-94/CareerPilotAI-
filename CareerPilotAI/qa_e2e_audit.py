import os
import sys
import unittest
import json
import uuid
from typing import Dict, Any

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set test database path BEFORE importing any app modules!
base_dir = os.path.dirname(os.path.abspath(__file__))
abs_db_path = os.path.join(base_dir, 'test_e2e.db')
os.environ['DATABASE_PATH'] = abs_db_path

from app import create_app
from backend.database.db import get_connection
from backend.database.schema import reset_db
from backend.models.user import UserModel
from werkzeug.security import generate_password_hash
from backend.ai.ollama_service import ollama

class CareerPilotE2EAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment and database."""
        cls.db_path = abs_db_path
        
        # Reset and initialize DB
        reset_db(cls.db_path)
        
        # Create Flask app
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
        
        from backend.services.auth_service import AuthService
        
        # Create a test user with a random UUID to avoid IntegrityError if run multiple times
        rand_suffix = str(uuid.uuid4())[:8]
        cls.test_email = f"test_e2e_{rand_suffix}@example.com"
        cls.test_password = "password123"
        cls.test_username = f"e2e_{rand_suffix}"
        
        # Use auth service to correctly hash with bcrypt
        success, msg, user_id = AuthService.register(
            cls.test_username, cls.test_email, cls.test_password, cls.test_password
        )
        cls.user_id = user_id
        
        # Insert Resume
        with get_connection(cls.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO resumes (user_id, filename, original_name, raw_text, parsed_data, is_primary)
                VALUES (?, 'test.pdf', 'test.pdf', 'Python Developer with 5 years of experience in SQL and ML.', '{}', 1)
            """, (cls.user_id,))
            cls.resume_id = cursor.lastrowid
            conn.commit()

        # Login to get session
        login_res = cls.client.post('/login', data={
            'username': cls.test_username,
            'password': cls.test_password
        }, follow_redirects=True)

        # Global registry to track AI metrics
        cls.test_metrics: Dict[str, Any] = {}

    def setUp(self):
        """Mock the ollama call to extract metrics and save them."""
        self.original_chat = ollama.chat
        self.original_generate = ollama.generate

        def chat_spy(messages, temperature=0.7, json_mode=False):
            res = self.original_chat(messages, temperature, json_mode)
            if 'metrics' in res:
                self.__class__.test_metrics[self._testMethodName] = res['metrics']
            return res

        def generate_spy(prompt, temperature=0.7, json_mode=False):
            res = self.original_generate(prompt, temperature, json_mode)
            if 'metrics' in res:
                self.__class__.test_metrics[self._testMethodName] = res['metrics']
            return res

        ollama.chat = chat_spy
        ollama.generate = generate_spy

    def tearDown(self):
        """Restore ollama original methods."""
        ollama.chat = self.original_chat
        ollama.generate = self.original_generate

    def _verify_metrics(self, test_name: str) -> None:
        """Helper to ensure metrics were captured and model responded."""
        self.assertIn(test_name, self.test_metrics, f"No AI metrics captured for {test_name}. Did it use mocked AI?")
        metrics = self.test_metrics[test_name]
        self.assertGreater(metrics.get("eval_count", 0), 0, "Response had 0 completion tokens. Check Ollama model.")

    # =========================================================================
    # E2E TESTS
    # =========================================================================

    def test_01_career_coach(self):
        """Test Career Coach API + DB Save"""
        res = self.client.post('/chat/send', json={
            'session_id': 'test_chat_1',
            'message': 'How do I become a backend developer?'
        })
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get('success'), "Chat API returned success=False")
        self.assertIsNotNone(data.get('response'))
        
        # Verify DB save
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT count(*) as cnt FROM chat_history WHERE session_id = 'test_chat_1'")
            self.assertGreater(cursor.fetchone()['cnt'], 0, "Chat history not saved to DB.")
            
        self._verify_metrics(self._testMethodName)

    def test_02_learning_roadmap(self):
        """Test Learning Roadmap API + DB Save"""
        res = self.client.post('/learning/generate', json={
            'target_role': 'Backend Developer',
            'skills': ['Python', 'SQL']
        })
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get('success'), "Roadmap API returned success=False")
        
        roadmap_id = data.get('roadmap', {}).get('id')
        self.assertIsNotNone(roadmap_id, "No roadmap ID returned.")
        
        # Verify DB save
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM learning_roadmaps WHERE id = ?", (roadmap_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Roadmap not saved to DB.")
            
        self._verify_metrics(self._testMethodName)

    def test_03_mock_interview(self):
        """Test Mock Interview API + DB Save"""
        res = self.client.post('/interview/start', json={
            'role': 'Backend Developer'
        })
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get('success'), "Interview Start API returned success=False")
        self.assertGreater(len(data.get('questions', [])), 0, "Empty questions array.")
        
        # Verify DB save
        interview_id = data.get('interview_id')
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM interview_history WHERE id = ?", (interview_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Interview not saved to DB.")
            
        self._verify_metrics(self._testMethodName)

    def test_04_sql_coach(self):
        """Test SQL Coach API + DB Save"""
        res = self.client.post('/sql-coach/analyze', json={
            'query': 'SELECT * FROM users WHERE age > 25'
        })
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get('success'), "SQL Coach API returned success=False")
        self.assertIn('explanation', data.get('analysis', {}), "Explanation not in analysis.")
        
        # Verify DB save
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM sql_queries WHERE user_id = ?", (self.user_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "SQL Query analysis not saved to DB.")
            
        self._verify_metrics(self._testMethodName)

    def test_05_project_generator(self):
        """Test Project Generator API + DB Save"""
        res = self.client.post('/projects/generate', json={
            'domain': 'Fintech',
            'skills': ['Python', 'Django']
        })
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get('success'), "Project Generator API returned success=False")
        
        # DB check
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM projects WHERE user_id = ?", (self.user_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Project idea not saved to DB.")
            
        self._verify_metrics(self._testMethodName)

    def test_06_code_reviewer(self):
        """Test Code Reviewer API + DB Save"""
        res = self.client.post('/code-review/analyze', json={
            'code': 'def add(a, b): return a + b',
            'language': 'python'
        })
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get('success'), "Code Review API returned success=False")
        self.assertIn('overall_quality', data.get('review', {}), "Missing review data.")
        
        # DB check
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM code_reviews WHERE user_id = ?", (self.user_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Code review not saved to DB.")
            
        self._verify_metrics(self._testMethodName)

    def test_07_job_match(self):
        """Test Job Match Analysis (AI endpoint)"""
        # First we need to manually insert a job into DB to match against
        with get_connection(self.db_path) as conn:
            conn.execute("""
                INSERT INTO job_history (user_id, title, company, description, match_score)
                VALUES (?, 'Backend Dev', 'TechCorp', 'Python, SQL, APIs required.', 0)
            """, (self.user_id,))
            job_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']
            conn.commit()

        res = self.client.get(f'/jobs/match/{job_id}')
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        analysis = data.get('analysis', {})
        self.assertIn('match_score', analysis, "Job match API returned bad format")
        
        self._verify_metrics(self._testMethodName)

    def test_08_resume_analysis(self):
        """Test Resume Analysis API"""
        res = self.client.post('/resume/analyze/run', json={
            'resume_id': self.resume_id
        })
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertTrue(data.get('success'), "Resume analyze returned success=False")
        
        # DB check
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM resume_analysis WHERE resume_id = ?", (self.resume_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Resume analysis not saved to DB.")
            
        self._verify_metrics(self._testMethodName)

    @classmethod
    def tearDownClass(cls):
        """Generate Report"""
        report_lines = [
            "# 🧪 E2E AI Integration & Performance Report\n",
            "| Module | Status | Latency (ms) | Prompt Tokens | Completion Tokens | Errors |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]
        
        # Mapping test names to pretty names
        names = {
            'test_01_career_coach': 'Career Coach',
            'test_02_learning_roadmap': 'Learning Roadmap',
            'test_03_mock_interview': 'Mock Interview',
            'test_04_sql_coach': 'SQL Coach',
            'test_05_project_generator': 'Project Generator',
            'test_06_code_reviewer': 'Code Reviewer',
            'test_07_job_match': 'Job Match Analysis',
            'test_08_resume_analysis': 'Resume Analysis'
        }
        
        for method, pretty_name in names.items():
            metrics = cls.test_metrics.get(method, {})
            if metrics:
                latency = round(metrics.get("latency_ms", 0), 2)
                p_tokens = metrics.get("prompt_eval_count", 0)
                c_tokens = metrics.get("eval_count", 0)
                status = "🟢 PASS" if c_tokens > 0 else "🔴 FAIL"
                errs = "None"
            else:
                latency, p_tokens, c_tokens = 0, 0, 0
                status = "🔴 FAIL"
                errs = "Missing Metrics/Mocked"
                
            report_lines.append(f"| {pretty_name} | {status} | {latency}ms | {p_tokens} | {c_tokens} | {errs} |")
            
        report_path = os.path.join(os.path.dirname(__file__), 'ai_test_report_gen.md')
        with open(report_path, 'w') as f:
            f.write("\n".join(report_lines) + "\n")
        
        print(f"\n[✓] Generated AI Test Report at {report_path}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
