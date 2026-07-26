import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()
c.execute("SELECT session_id FROM chat_sessions LIMIT 1")
row = c.fetchone()
if row:
    sid = row[0]
    print(f"Testing delete for session {sid}")
    c.execute("DELETE FROM chat_history WHERE session_id = ?", (sid,))
    c.execute("DELETE FROM chat_sessions WHERE session_id = ?", (sid,))
    conn.commit()
    print("Delete executed and committed.")
else:
    print("No chat sessions to delete.")
