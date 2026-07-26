import requests

s = requests.Session()
# First login
login_data = {
    "email": "test@test.com", # Assumed dummy email or we find real user email
    "password": "password"
}
# Wait, let's just bypass by using Flask app context
from app import app
from backend.models.chat import ChatSessionModel

with app.app_context():
    with app.test_request_context():
        # Let's see what happens if we call delete
        try:
            print("Deleting 5d1c30fb-9df5-490b-a532-8224e973c676...")
            ChatSessionModel.delete('5d1c30fb-9df5-490b-a532-8224e973c676')
            print("Success")
        except Exception as e:
            print(f"Failed: {str(e)}")
