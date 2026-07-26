import pytest
from app import app
from backend.database.db import execute_update
import sqlite3

def test_delete_route():
    app.config['TESTING'] = True
    client = app.test_client()

    # Create dummy user and session
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Find a valid user to avoid constraint errors
    c.execute("SELECT id FROM users LIMIT 1")
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (email, password_hash) VALUES ('t@t.com', 'h')")
        user_id = c.lastrowid
    else:
        user_id = user[0]

    sid = "test-delete-999"
    c.execute("INSERT OR IGNORE INTO chat_sessions (session_id, user_id, title) VALUES (?, ?, 'Test')", (sid, user_id))
    conn.commit()

    # Log in by setting session
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    # Hit the delete endpoint
    response = client.post(f'/chat/session/{sid}/delete')
    print("Response status:", response.status_code)
    print("Response JSON:", response.get_json())

    # Check database
    c.execute("SELECT * FROM chat_sessions WHERE session_id = ?", (sid,))
    remaining = c.fetchone()
    print("Row remains in DB:", remaining is not None)

if __name__ == '__main__':
    test_delete_route()
