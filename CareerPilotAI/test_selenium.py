import time
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import sys

# Connect to database and insert a test user and session to test with
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute("INSERT OR IGNORE INTO users (id, email, password_hash) VALUES (999, 'ui_test@test.com', 'scrypt:32768:8:1$x$x')")
c.execute("INSERT OR REPLACE INTO chat_sessions (session_id, user_id, title) VALUES ('test-ui-123', 999, 'UI Test Chat')")
conn.commit()

print("Database seeded for UI test.")

# Configure headless Chrome
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

try:
    driver = webdriver.Chrome(options=options)
    driver.get("http://localhost:5002/auth/login")
    
    # We don't have the exact hash for ui_test@test.com since we mocked it.
    # We can just set a session cookie directly or login if we know a real credential.
    # Alternatively, we can use the test client again since Selenium might be flaky.
    pass
except Exception as e:
    print(f"Selenium setup failed: {e}")
    sys.exit(1)
finally:
    try:
        driver.quit()
    except:
        pass
