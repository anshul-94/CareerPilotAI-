import os
import sys
import time
import uuid
import subprocess
from reportlab.pdfgen import canvas

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    print("Playwright not found. Run: pip install playwright")
    sys.exit(1)

# Ensure project root is in path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)
TEST_DB = "test_journey.db"
abs_db_path = os.path.join(base_dir, TEST_DB)
os.environ['DATABASE_PATH'] = abs_db_path

from backend.database.schema import reset_db

BASE_URL = "http://127.0.0.1:5002"

def generate_dummy_pdf(filename="dummy_resume.pdf"):
    path = os.path.join(base_dir, filename)
    c = canvas.Canvas(path)
    c.drawString(100, 750, "John Doe Resume")
    c.drawString(100, 730, "Skills: Python, SQL, Backend Development")
    c.drawString(100, 710, "Experience: 3 years building web applications")
    c.save()
    return path

def run_flask():
    env = os.environ.copy()
    env["FLASK_APP"] = "run.py"
    env["DATABASE_PATH"] = abs_db_path
    
    runner_code = f"""
import os
os.environ['DATABASE_PATH'] = r'{abs_db_path}'
from app import create_app
app = create_app()
app.run(port=5002, debug=False, use_reloader=False)
    """
    with open("temp_runner_journey.py", "w") as f:
        f.write(runner_code)
        
    process = subprocess.Popen([sys.executable, "temp_runner_journey.py"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    return process

def run_journey():
    reset_db(abs_db_path)
    pdf_path = generate_dummy_pdf()
    
    rand_suffix = str(uuid.uuid4())[:8]
    username = f"user_{rand_suffix}"
    email = f"{username}@example.com"
    password = "Password123!"

    print("=== STARTING QA USER JOURNEY ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(base_url=BASE_URL)
        page = context.new_page()

        # Monitor errors
        def handle_response(response):
            if response.status >= 400 and response.url.startswith(BASE_URL):
                print(f"[HTTP Error] {response.status} at {response.url}")
                if response.status == 500:
                    raise Exception(f"HTTP 500 Internal Server Error at {response.url}")

        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("response", handle_response)

        try:
            print("[Step 1] Start Application (Hit homepage)")
            page.goto("/")
            page.wait_for_load_state("networkidle")

            print("[Step 2] Register")
            page.goto("/register")
            page.fill("input[name='full_name']", "John Doe")
            page.fill("input[name='username']", username)
            page.fill("input[name='email']", email)
            page.fill("input[name='password']", password)
            page.fill("input[name='confirm_password']", password)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            assert "login" in page.url or "dashboard" in page.url, f"Registration failed, URL is {page.url}"

            if "login" in page.url:
                print("[Step 3] Login")
                page.fill("input[name='username']", username)
                page.fill("input[name='password']", password)
                page.click("button[type='submit']")
                page.wait_for_load_state("networkidle")
                
            assert "dashboard" in page.url, "Login failed, not on dashboard"

            print("[Step 4] Upload Resume")
            page.goto("/resume/upload")
            page.set_input_files("input[type='file']", pdf_path)
            
            # The UI auto-submits on file change using js. Let's wait.
            # Usually we need to wait for a success notification or redirect
            page.wait_for_timeout(3000)
            
            print("[Step 5] Analyze Resume")
            # If the dashboard has a resume, we can analyze it, or visit /resume/builder 
            # In the UI, the resume analysis is at /resume/analyze/<id>. We might just go to /dashboard
            page.goto("/dashboard")
            page.wait_for_load_state("networkidle")

            print("[Step 6] Chat with AI")
            page.goto("/chat/")
            page.fill("#chatInput", "Hello, I want to become a Senior Dev.")
            with page.expect_response("**/chat/send", timeout=60000) as response_info:
                page.click("#sendBtn")
            assert response_info.value.ok, "Chat response failed"
            
            print("[Step 7] Generate Learning Roadmap")
            page.goto("/learning/")
            page.fill("#targetRole", "Senior Backend Developer")
            page.fill("#currentSkills", "Python, SQL, Flask")
            with page.expect_response("**/learning/generate", timeout=120000) as response_info:
                page.click("#generateRoadmap")
            assert response_info.value.ok, "Roadmap generation failed"

            print("[Step 8] Generate Mock Interview")
            page.goto("/interview/")
            page.fill("#interviewRole", "Backend Developer")
            with page.expect_response("**/interview/start", timeout=120000) as response_info:
                page.click("#startInterview")
            assert response_info.value.ok, "Interview start failed"

            print("[Step 9] Generate Project")
            page.goto("/projects/")
            page.fill("#projectDomain", "E-commerce")
            with page.expect_response("**/projects/generate", timeout=120000) as response_info:
                page.click("#generateProjectBtn")
            assert response_info.value.ok, "Project generation failed"

            print("[Step 10] Search Jobs")
            page.goto("/jobs/")
            page.fill("#jobRole", "Backend Engineer")
            with page.expect_response("**/jobs/search", timeout=60000) as response_info:
                page.click("#searchJobsBtn")
            assert response_info.value.ok, "Job search failed"

            print("[Step 11] Open History")
            page.goto("/profile/history")
            page.wait_for_load_state("networkidle")

            print("[Step 12] Open Profile")
            page.goto("/profile/")
            page.wait_for_load_state("networkidle")

            print("[Step 13] Logout")
            page.goto("/logout")
            page.wait_for_load_state("networkidle")

            print("\n[✓] ALL STEPS PASSED SUCCESSFULLY.")
        except Exception as e:
            print(f"\n[!] JOURNEY FAILED: {str(e)}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    flask_proc = run_flask()
    try:
        run_journey()
    finally:
        flask_proc.terminate()
        if os.path.exists("temp_runner_journey.py"):
            os.remove("temp_runner_journey.py")
        if os.path.exists("dummy_resume.pdf"):
            os.remove("dummy_resume.pdf")
