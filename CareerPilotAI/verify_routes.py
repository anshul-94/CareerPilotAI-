import requests
import time
import sys

BASE_URL = "http://localhost:5002"
session = requests.Session()

def check_route(url, expected_status=200):
    try:
        response = session.get(BASE_URL + url, allow_redirects=True)
        if response.status_code == expected_status:
            print(f"[PASS] {url}")
            return True
        else:
            print(f"[FAIL] {url} - Status Code: {response.status_code}")
            if response.status_code == 500:
                print(response.text[:1000])
            return False
    except Exception as e:
        print(f"[ERROR] {url} - {str(e)}")
        return False

def run_tests():
    print("Testing routes...")
    routes_to_test = [
        "/",
        "/register",
        "/login"
    ]
    
    all_passed = True
    for route in routes_to_test:
        if not check_route(route):
            all_passed = False
            
    # Register and Login
    try:
        # Register a test user
        register_payload = {
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "full_name": "Test User 2"
        }
        res = session.post(BASE_URL + "/register", data=register_payload)
        
        # Login
        login_payload = {
            "username": "testuser2",
            "password": "password123"
        }
        session.post(BASE_URL + "/login", data=login_payload)
    except Exception as e:
        print("Failed to register/login test user:", e)
        sys.exit(1)

    # Test authenticated routes
    auth_routes = [
        "/dashboard",
        "/resume/upload",
        "/resume/builder", # Maps to Intelligence dashboard
        "/jobs/",
        "/chat/",
        "/learning/",
        "/interview/",
        "/code-review",
        "/profile/",
        "/notifications/"
    ]
    
    for route in auth_routes:
        if not check_route(route):
            all_passed = False
            
    if all_passed:
        print("\n[SUCCESS] All routes returned HTTP 200.")
        sys.exit(0)
    else:
        print("\n[FAILURE] Some routes failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
