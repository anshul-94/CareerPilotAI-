import os
from backend.database.schema import init_db

if __name__ == "__main__":
    db_path = os.path.join("backend", "database", "careerpilot.db")
    print("Initializing CareerPilot AI Database...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    if os.path.exists(db_path):
        print(f"Database already exists at {db_path}. Overwriting/re-initializing schema may clear data depending on schema logic.")
    
    init_db(db_path=db_path)
    
    print(f"Database successfully initialized at: {db_path}")
