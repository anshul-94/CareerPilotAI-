"""
CareerPilot AI — Database Connection Manager
Handles SQLite connections, query execution, and transaction management.
"""

import sqlite3
import os
from typing import Any, Optional
from contextlib import contextmanager


# Default database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")


def get_db_path() -> str:
    """Get the absolute path to the database file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, DATABASE_PATH)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create and return a new database connection.
    Returns rows as sqlite3.Row objects for dict-like access.
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_db(db_path: Optional[str] = None):
    """
    Context manager for database connections.
    Automatically commits on success, rolls back on failure.
    
    Usage:
        with get_db() as db:
            db.execute("SELECT * FROM users")
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(query: str, params: tuple = (), db_path: Optional[str] = None) -> list[dict]:
    """
    Execute a SELECT query and return results as list of dicts.
    
    Args:
        query: SQL query string
        params: Query parameters
        db_path: Optional database path override
        
    Returns:
        List of dictionaries representing rows
    """
    from backend.utils.logger import db_logger
    import time
    start = time.time()
    
    with get_db(db_path) as db:
        cursor = db.execute(query, params)
        rows = cursor.fetchall()
        
        duration = int((time.time() - start) * 1000)
        table = query.split('FROM')[1].split('WHERE')[0].strip() if 'FROM' in query else 'unknown'
        log_msg = f"\n[DB]\nSELECT\n{table}\nRows:{len(rows)}\n{duration} ms"
        db_logger.info(log_msg)
        
        return [dict(row) for row in rows]


def execute_one(query: str, params: tuple = (), db_path: Optional[str] = None) -> Optional[dict]:
    """
    Execute a SELECT query and return a single result as dict.
    
    Args:
        query: SQL query string
        params: Query parameters
        db_path: Optional database path override
        
    Returns:
        Dictionary representing the row, or None if not found
    """
    from backend.utils.logger import db_logger
    import time
    start = time.time()
    
    with get_db(db_path) as db:
        cursor = db.execute(query, params)
        row = cursor.fetchone()
        
        duration = int((time.time() - start) * 1000)
        table = query.split('FROM')[1].split('WHERE')[0].strip() if 'FROM' in query else 'unknown'
        log_msg = f"\n[DB]\nSELECT ONE\n{table}\nRows:{1 if row else 0}\n{duration} ms"
        db_logger.info(log_msg)
        
        return dict(row) if row else None


def execute_insert(query: str, params: tuple = (), db_path: Optional[str] = None) -> int:
    """
    Execute an INSERT query and return the last inserted row ID.
    
    Args:
        query: SQL INSERT statement
        params: Query parameters
        db_path: Optional database path override
        
    Returns:
        The ID of the newly inserted row
    """
    from backend.utils.logger import db_logger
    import time
    start = time.time()
    
    with get_db(db_path) as db:
        cursor = db.execute(query, params)
        
        duration = int((time.time() - start) * 1000)
        table = query.split('INTO')[1].split('(')[0].strip() if 'INTO' in query else 'unknown'
        log_msg = f"\n[DB]\nINSERT\n{table}\nRows:1\n{duration} ms"
        db_logger.info(log_msg)
        
        return cursor.lastrowid


def execute_update(query: str, params: tuple = (), db_path: Optional[str] = None) -> int:
    """
    Execute an UPDATE or DELETE query and return affected row count.
    
    Args:
        query: SQL UPDATE/DELETE statement
        params: Query parameters
        db_path: Optional database path override
        
    Returns:
        Number of rows affected
    """
    from backend.utils.logger import db_logger
    import time
    start = time.time()
    
    with get_db(db_path) as db:
        cursor = db.execute(query, params)
        
        duration = int((time.time() - start) * 1000)
        # Determine if UPDATE or DELETE
        op = "UPDATE" if "UPDATE" in query else ("DELETE" if "DELETE" in query else "EXECUTE")
        if op == "UPDATE":
            table = query.split('UPDATE')[1].split('SET')[0].strip() if 'UPDATE' in query else 'unknown'
        elif op == "DELETE":
            table = query.split('FROM')[1].split('WHERE')[0].strip() if 'FROM' in query else 'unknown'
        else:
            table = 'unknown'
            
        log_msg = f"\n[DB]\n{op}\n{table}\nRows:{cursor.rowcount}\n{duration} ms"
        db_logger.info(log_msg)
        
        return cursor.rowcount


def execute_many(query: str, params_list: list[tuple], db_path: Optional[str] = None) -> int:
    """
    Execute a query with multiple parameter sets (batch insert/update).
    
    Args:
        query: SQL statement
        params_list: List of parameter tuples
        db_path: Optional database path override
        
    Returns:
        Number of rows affected
    """
    with get_db(db_path) as db:
        cursor = db.executemany(query, params_list)
        return cursor.rowcount


def table_exists(table_name: str, db_path: Optional[str] = None) -> bool:
    """Check if a table exists in the database."""
    result = execute_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
        db_path
    )
    return result is not None


def get_table_count(table_name: str, db_path: Optional[str] = None) -> int:
    """Get the number of rows in a table."""
    result = execute_one(f"SELECT COUNT(*) as count FROM {table_name}", db_path=db_path)
    return result["count"] if result else 0
