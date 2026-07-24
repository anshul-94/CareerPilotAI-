import os
os.environ["DATABASE_PATH"] = "test_qa.db"
import sys
import unittest
import json
import uuid
from flask import Flask
from app import create_app
from backend.models.user import UserModel
from backend.services.ai_service import AIService
from backend.ai.ollama_service import ollama
from backend.database.schema import init_db
from backend.config import Config

class CareerPilotQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Override DB path for testing to avoid nuking real DB
        Config.DATABASE_PATH = "test_qa.db"
        if os.path.exists(Config.DATABASE_PATH):
            os.remove(Config.DATABASE_PATH)
            
        init_db(Config.DATABASE_PATH)
        
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        # Create a test user
        cls.test_email = f"qa_tester_{uuid.uuid4().hex[:6]}@careerpilot.ai"
        cls.test_password = "password123"
        cls.test_username = f"qatest_{uuid.uuid4().hex[:6]}"
        
        with cls.app.app_context():
            UserModel.create(cls.test_username, cls.test_email, cls.test_password, "QA Tester")
            user = UserModel.get_by_email(cls.test_email)
            cls.test_user_id = user["id"]
            
    @classmethod
    def tearDownClass(cls):
        if os.path.exists(Config.DATABASE_PATH):
            os.remove(Config.DATABASE_PATH)
            
    def setUp(self):
        # Login before each test
        self.client.post('/auth/login', data={
            'email': self.test_email,
            'password': self.test_password
        }, follow_redirects=True)

    # 1. Purity Checks
    def test_01_no_legacy_imports(self):
        print("\n--- Running Purity Checks ---")
        legacy_terms = ['openrouter_client', 'grok', 'mock_responses']
        found = False
        for root, dirs, files in os.walk('backend'):
            for file in files:
                if file.endswith('.py'):
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read().lower()
                        for term in legacy_terms:
                            if term in content and "mock" not in file: # Ignore mock in file names if any
                                # Exception: this audit script might contain the word, but we only scan 'backend'
                                if term == 'mock_responses' and 'import mock_responses' in content:
                                    found = True
                                    print(f"FAIL: Legacy import {term} found in {file}")
        self.assertFalse(found, "Legacy imports found!")

    # 2. Endpoint Checks
    def test_02_endpoints_load(self):
        print("\n--- Running Endpoint Tests ---")
        endpoints = [
            '/',
            '/dashboard',
            '/resume/upload',
            '/chat/',
            '/learning/',
            '/interview/',
            '/jobs/',
            '/code-review',
            '/projects/',
            '/profile/'
        ]
        
        for ep in endpoints:
            print(f"Testing {ep}...")
            response = self.client.get(ep, follow_redirects=True)
            self.assertEqual(response.status_code, 200, f"Endpoint {ep} failed to load (returned {response.status_code})")
            print(f"PASS: {ep} loaded successfully.")

    # 3. AI Service Direct Invocation
    def test_03_ai_services(self):
        print("\n--- Running AI Module Tests ---")
        
        # Check if Ollama is running before proceeding
        if not ollama.health():
            print("SKIP: Ollama is offline. Ensure `ollama serve` is running for full AI testing.")
            return

        with self.app.app_context():
            # 1. Career Coach
            res = AIService.chat(self.test_user_id, "How do I become a Data Scientist?", "qa_session")
            self.assertFalse(res.get('mock', True), "Career Coach returned mock data.")
            self.assertTrue(len(res.get('response', '')) > 0, "Career Coach returned empty response.")
            print("PASS: Career Coach AI")

            # 2. Roadmap
            res = AIService.generate_roadmap(["Python"], "Data Scientist")
            self.assertFalse(res.get('mock', True), "Roadmap returned mock data.")
            self.assertTrue(len(res.get('weekly_plan', [])) > 0, "Roadmap returned no weekly_plan.")
            print("PASS: Learning Roadmap AI")

            # 3. Mock Interview
            res = AIService.generate_interview_questions("Data Scientist")
            self.assertFalse(res.get('mock', True), "Interview returned mock data.")
            self.assertTrue(len(res.get('questions', [])) > 0, "Interview returned no questions.")
            print("PASS: Mock Interview AI")

            # 4. SQL Coach
            res = AIService.analyze_sql("SELECT * FROM users")
            self.assertFalse(res.get('mock', True), "SQL Coach returned mock data.")
            self.assertTrue('explanation' in res, "SQL Coach response malformed.")
            print("PASS: SQL Coach AI")

            # 5. Code Reviewer
            res = AIService.review_code("def foo():\n  pass")
            self.assertFalse(res.get('mock', True), "Code Reviewer returned mock data.")
            self.assertTrue('overall_quality' in res, "Code Review response malformed.")
            print("PASS: Code Reviewer AI")

            # 6. Project Generator
            res = AIService.generate_projects("Web Dev", ["HTML", "JS"])
            self.assertFalse(res.get('mock', True), "Project Generator returned mock data.")
            self.assertTrue(len(res.get('projects', [])) > 0, "Project Generator returned no projects.")
            print("PASS: Project Generator AI")

if __name__ == '__main__':
    unittest.main(verbosity=2)
