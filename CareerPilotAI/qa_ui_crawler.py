import os
import sys
import time
import json
import uuid
import threading
import subprocess
from urllib.parse import urlparse, urljoin

# Playwright imports
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not found. Run: pip install playwright")
    sys.exit(1)

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Pre-load config to avoid Database path issues
base_dir = os.path.dirname(os.path.abspath(__file__))
TEST_DB = "test_ui.db"
abs_db_path = os.path.join(base_dir, TEST_DB)
os.environ['DATABASE_PATH'] = abs_db_path

from app import create_app
from backend.database.schema import reset_db
from backend.services.auth_service import AuthService
from backend.database.db import get_connection

# Settings
BASE_URL = "http://127.0.0.1:5001"

# Results tracking
results = {
    "scanned_urls": [],
    "network_errors": [],
    "console_errors": [],
    "broken_buttons": []
}

visited_urls = set()
urls_to_visit = set(["/dashboard"])

def setup_test_env():
    """Setup test database and user."""
    reset_db(abs_db_path)
    
    # Create test user
    rand_suffix = str(uuid.uuid4())[:8]
    test_email = f"ui_test_{rand_suffix}@example.com"
    test_password = "password123"
    test_username = f"uitest_{rand_suffix}"
    
    success, msg, user_id = AuthService.register(
        test_username, test_email, test_password, test_password
    )
    
    if not success:
        print(f"Failed to create test user: {msg}")
        sys.exit(1)
        
    return test_username, test_password

def run_flask():
    """Run Flask server in testing mode."""
    env = os.environ.copy()
    env["FLASK_APP"] = "run.py"
    env["DATABASE_PATH"] = abs_db_path
    
    runner_code = f"""
import os
os.environ['DATABASE_PATH'] = r'{abs_db_path}'
from app import create_app
app = create_app()
app.run(port=5001, debug=False, use_reloader=False)
    """
    with open("temp_runner.py", "w") as f:
        f.write(runner_code)
        
    process = subprocess.Popen([sys.executable, "temp_runner.py"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2) # Give it time to start
    return process

def crawl_app(username, password):
    """Crawl the application using Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(base_url=BASE_URL)
        page = context.new_page()

        # Listen for console errors
        page.on("console", lambda msg: results["console_errors"].append({
            "url": page.url,
            "text": msg.text,
            "type": msg.type
        }) if msg.type == "error" else None)
        
        # Listen for failed requests (e.g. 404 assets)
        page.on("response", lambda response: results["network_errors"].append({
            "url": page.url,
            "resource": response.url,
            "status": response.status
        }) if response.status >= 400 else None)

        print(f"[*] Logging in as {username}...")
        page.goto("/login")
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")
        
        page.wait_for_load_state("networkidle")
        
        if "login" in page.url:
            print("[-] Login failed!")
            return

        # Start crawling
        print("[*] Starting crawl...")
        while urls_to_visit:
            path = urls_to_visit.pop()
            if path in visited_urls:
                continue
                
            visited_urls.add(path)
            full_url = urljoin(BASE_URL, path)
            print(f"  -> Visiting {path}")
            
            try:
                page.goto(full_url)
                page.wait_for_load_state("networkidle")
                results["scanned_urls"].append(path)
                
                # Check for Flash alerts containing "danger" or "error" classes
                alerts = page.locator(".alert-danger, .alert-error").all_inner_texts()
                for alert in alerts:
                    results["console_errors"].append({
                        "url": path,
                        "text": f"Flash Error: {alert.strip()}",
                        "type": "flash"
                    })
                
                # Test clicking all buttons (shallow testing of UI components)
                buttons = page.locator("button").all()
                for i, btn in enumerate(buttons):
                    try:
                        # Skip if button is disabled
                        if btn.is_disabled():
                            continue
                            
                        # Get button text or id for logging
                        btn_name = btn.text_content() or btn.get_attribute("id") or f"button_{i}"
                        btn_name = btn_name.strip()
                        
                        # Only click if it doesn't look like a logout or delete button
                        if not btn_name or any(x in btn_name.lower() for x in ['logout', 'delete', 'remove', 'clear']):
                            continue
                            
                        print(f"    -> Clicking button: '{btn_name}'")
                        # Click and wait a short moment for any async JS or network request
                        btn.click(timeout=3000)
                        page.wait_for_timeout(500) 
                        
                    except Exception as e:
                        print(f"    [-] Button click failed: {str(e)}")
                        # Playwright might throw if button is intercepted or not clickable

                # Find all internal links to add to crawl queue
                links = page.locator("a").all()
                for link in links:
                    href = link.get_attribute("href")
                    if href and href.startswith("/") and not href.startswith("//"):
                        # Exclude some destructive or file routes
                        if any(x in href for x in ['logout', 'delete', 'download', 'static']):
                            continue
                        if href not in visited_urls:
                            urls_to_visit.add(href)
                            
            except Exception as e:
                print(f"[-] Error visiting {path}: {str(e)}")
                results["console_errors"].append({
                    "url": path,
                    "text": str(e),
                    "type": "exception"
                })

        browser.close()

if __name__ == "__main__":
    print("=== CareerPilot AI UI QA Crawler ===")
    
    print("[1] Setting up Test Database...")
    user, pwd = setup_test_env()
    
    print("[2] Starting Flask server...")
    flask_proc = run_flask()
    
    try:
        print("[3] Initiating Playwright UI Crawler...")
        crawl_app(user, pwd)
    finally:
        print("[4] Cleaning up...")
        flask_proc.terminate()
        if os.path.exists("temp_runner.py"):
            os.remove("temp_runner.py")
            
    # Save Report
    report_file = "ui_bug_report.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\n[✓] Crawl complete. Visited {len(results['scanned_urls'])} pages.")
    print(f"    - Network Errors: {len(results['network_errors'])}")
    print(f"    - Console Errors: {len(results['console_errors'])}")
    print(f"[✓] Report saved to {report_file}")
