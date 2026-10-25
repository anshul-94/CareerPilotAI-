"""
CareerPilot AI — Database Connection Manager
Handles both SQLite and PostgreSQL connections, query execution, parameter adaptation,
and transaction management with zero application-level breaking changes.
"""

import os
import time
import re
from typing import Any, Optional, Union
from contextlib import contextmanager

# Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Lazy-loaded connection pool for PostgreSQL
_pg_pool = None


def is_postgres() -> bool:
    """Return True if PostgreSQL is configured via DATABASE_URL."""
    return bool(os.getenv("DATABASE_URL", "").strip())


def normalize_postgres_url(url: str) -> str:
    """Ensure PostgreSQL URL uses postgresql:// scheme (required by psycopg2)."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _get_pg_pool():
    """Lazily initialize and return the PostgreSQL thread-safe connection pool."""
    global _pg_pool
    if _pg_pool is None:
        import psycopg2
        from psycopg2.pool import ThreadedConnectionPool
        
        raw_url = os.getenv("DATABASE_URL", "").strip()
        if not raw_url:
            raise ValueError("DATABASE_URL is not set but PostgreSQL connection was requested.")
        
        dsn = normalize_postgres_url(raw_url)
        minconn = int(os.getenv("DB_MIN_CONNECTIONS", "1"))
        maxconn = int(os.getenv("DB_MAX_CONNECTIONS", "20"))
        _pg_pool = ThreadedConnectionPool(minconn, maxconn, dsn=dsn)
    return _pg_pool


def adapt_query_placeholders(query: str, target_is_postgres: bool) -> str:
    """
    Translate positional placeholders from SQLite '?' style to PostgreSQL '%s' style.
    Safely ignores '?' occurrences located inside string literals, escaped quotes,
    double-quoted identifiers, and SQL comments (-- or /* */).
    """
    if not target_is_postgres or "?" not in query:
        return query

    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    out = []
    i = 0
    n = len(query)

    while i < n:
        ch = query[i]
        next_ch = query[i + 1] if i + 1 < n else ""

        # Handle line comments (-- ...)
        if in_line_comment:
            out.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        # Handle block comments (/* ... */)
        if in_block_comment:
            out.append(ch)
            if ch == "*" and next_ch == "/":
                out.append("/")
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        # Detect comment starts outside quotes
        if not in_single_quote and not in_double_quote:
            if ch == "-" and next_ch == "-":
                out.append("--")
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and next_ch == "*":
                out.append("/*")
                in_block_comment = True
                i += 2
                continue

        # Handle single-quoted literals and escaped quotes
        if ch == "'" and not in_double_quote:
            if in_single_quote:
                if next_ch == "'":  # SQL standard escaped quote ''
                    out.append("''")
                    i += 2
                    continue
                in_single_quote = False
                out.append(ch)
                i += 1
                continue
            else:
                in_single_quote = True
                out.append(ch)
                i += 1
                continue

        # Handle backslash escape inside single quotes (e.g. \')
        if ch == "\\" and in_single_quote:
            out.append(ch)
            if next_ch:
                out.append(next_ch)
                i += 2
                continue
            i += 1
            continue

        # Handle double quotes (identifiers)
        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            out.append(ch)
            i += 1
            continue

        # Translate placeholder outside quotes and comments
        if ch == "?" and not in_single_quote and not in_double_quote:
            out.append("%s")
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def get_db_path() -> str:
    """Get the absolute path to the SQLite database file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    current_path = os.getenv("DATABASE_PATH", "database.db")
    return os.path.join(base_dir, current_path)


class PostgresConnectionWrapper:
    """
    Wrapper around a psycopg2 connection to provide a unified .execute() and
    .executemany() interface matching sqlite3.Connection behavior.
    Safely returns pooled connections upon .close() or context manager exit.
    """
    def __init__(self, raw_conn, pool=None):
        self._raw_conn = raw_conn
        self._pool = pool
        self._closed = False

    def execute(self, query: str, params: tuple = ()):
        from psycopg2.extras import RealDictCursor
        cursor = self._raw_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        return cursor

    def executemany(self, query: str, params_list: list):
        from psycopg2.extras import RealDictCursor
        cursor = self._raw_conn.cursor(cursor_factory=RealDictCursor)
        cursor.executemany(query, params_list)
        return cursor

    def commit(self):
        if not self._raw_conn.closed:
            self._raw_conn.commit()

    def rollback(self):
        if not self._raw_conn.closed:
            self._raw_conn.rollback()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._pool is not None:
            # Ensure any dangling uncommitted transaction is rolled back before returning to pool
            try:
                if not self._raw_conn.closed:
                    self._raw_conn.rollback()
            except Exception:
                pass
            self._pool.putconn(self._raw_conn, close=self._raw_conn.closed)
        else:
            try:
                self._raw_conn.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            self.close()


def get_connection(db_path: Optional[str] = None):
    """
    Create and return a new database connection.
    For SQLite: Returns sqlite3.Connection with Row factory and PRAGMAs.
    For PostgreSQL: Returns a pooled connection wrapped in PostgresConnectionWrapper.
    """
    if is_postgres():
        pool = _get_pg_pool()
        raw_conn = pool.getconn()
        return PostgresConnectionWrapper(raw_conn, pool=pool)
    else:
        import sqlite3
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
    Automatically commits on success, rolls back on failure, and cleans up connection.
    
    Usage:
        with get_db() as db:
            cursor = db.execute("SELECT * FROM users")
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
    """
    from backend.utils.logger import db_logger
    start = time.time()
    pg_active = is_postgres()
    adapted_query = adapt_query_placeholders(query, pg_active)
    
    with get_db(db_path) as db:
        cursor = db.execute(adapted_query, params)
        rows = cursor.fetchall()
        
        duration = int((time.time() - start) * 1000)
        table = query.split('FROM')[1].split('WHERE')[0].strip() if 'FROM' in query else 'unknown'
        log_msg = f"\n[DB ({'PG' if pg_active else 'SQLite'})]\nSELECT\n{table}\nRows:{len(rows)}\n{duration} ms"
        db_logger.info(log_msg)
        
        return [dict(row) for row in rows]


def execute_one(query: str, params: tuple = (), db_path: Optional[str] = None) -> Optional[dict]:
    """
    Execute a SELECT query and return a single result as dict.
    """
    from backend.utils.logger import db_logger
    start = time.time()
    pg_active = is_postgres()
    adapted_query = adapt_query_placeholders(query, pg_active)
    
    with get_db(db_path) as db:
        cursor = db.execute(adapted_query, params)
        row = cursor.fetchone()
        
        duration = int((time.time() - start) * 1000)
        table = query.split('FROM')[1].split('WHERE')[0].strip() if 'FROM' in query else 'unknown'
        log_msg = f"\n[DB ({'PG' if pg_active else 'SQLite'})]\nSELECT ONE\n{table}\nRows:{1 if row else 0}\n{duration} ms"
        db_logger.info(log_msg)
        
        return dict(row) if row else None


def execute_insert(query: str, params: tuple = (), db_path: Optional[str] = None) -> Any:
    """
    Execute an INSERT query and return the last inserted row ID or primary key.
    On PostgreSQL, automatically appends RETURNING clause if not present.
    """
    from backend.utils.logger import db_logger
    start = time.time()
    pg_active = is_postgres()
    adapted_query = adapt_query_placeholders(query, pg_active)
    
    if pg_active and not re.search(r'\bRETURNING\b', adapted_query, re.IGNORECASE):
        upper_query = adapted_query.upper()
        if re.search(r'\bINTO\s+CHAT_SESSIONS\b', upper_query):
            adapted_query = adapted_query.rstrip("; \t\n") + " RETURNING session_id;"
        else:
            adapted_query = adapted_query.rstrip("; \t\n") + " RETURNING id;"

    with get_db(db_path) as db:
        cursor = db.execute(adapted_query, params)
        
        duration = int((time.time() - start) * 1000)
        table = query.split('INTO')[1].split('(')[0].strip() if 'INTO' in query else 'unknown'
        log_msg = f"\n[DB ({'PG' if pg_active else 'SQLite'})]\nINSERT\n{table}\nRows:1\n{duration} ms"
        db_logger.info(log_msg)
        
        if pg_active:
            row = cursor.fetchone()
            if row:
                values = list(dict(row).values())
                return values[0] if values else 0
            return 0
        else:
            return cursor.lastrowid


def execute_update(query: str, params: tuple = (), db_path: Optional[str] = None) -> int:
    """
    Execute an UPDATE or DELETE query and return affected row count.
    """
    from backend.utils.logger import db_logger
    start = time.time()
    pg_active = is_postgres()
    adapted_query = adapt_query_placeholders(query, pg_active)
    
    with get_db(db_path) as db:
        cursor = db.execute(adapted_query, params)
        
        duration = int((time.time() - start) * 1000)
        op = "UPDATE" if "UPDATE" in query else ("DELETE" if "DELETE" in query else "EXECUTE")
        if op == "UPDATE":
            table = query.split('UPDATE')[1].split('SET')[0].strip() if 'UPDATE' in query else 'unknown'
        elif op == "DELETE":
            table = query.split('FROM')[1].split('WHERE')[0].strip() if 'FROM' in query else 'unknown'
        else:
            table = 'unknown'
            
        log_msg = f"\n[DB ({'PG' if pg_active else 'SQLite'})]\n{op}\n{table}\nRows:{cursor.rowcount}\n{duration} ms"
        db_logger.info(log_msg)
        
        return cursor.rowcount


def execute_many(query: str, params_list: list[tuple], db_path: Optional[str] = None) -> int:
    """
    Execute a query with multiple parameter sets (batch insert/update).
    """
    pg_active = is_postgres()
    adapted_query = adapt_query_placeholders(query, pg_active)
    with get_db(db_path) as db:
        cursor = db.executemany(adapted_query, params_list)
        return cursor.rowcount if cursor.rowcount is not None else len(params_list)


def table_exists(table_name: str, db_path: Optional[str] = None) -> bool:
    """Check if a table exists in the active database."""
    if is_postgres():
        result = execute_one(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
            (table_name,),
            db_path
        )
        return result is not None
    else:
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
