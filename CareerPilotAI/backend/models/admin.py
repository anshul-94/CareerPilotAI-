"""
CareerPilot AI — Admin Database Models
Defines tables, migrations, and access methods for Admin Authentication and Audit Logging.
"""

import bcrypt
from datetime import datetime
from typing import Optional, List, Dict, Any
from backend.database.db import execute_query, execute_one, execute_insert, execute_update, table_exists


def migrate_admin_tables():
    """Create admin_users and admin_audit_logs tables if they do not exist, and seed default admin."""
    
    # 1. Admin Users Table
    if not table_exists("admin_users"):
        execute_query("""
            CREATE TABLE admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
    # 2. Admin Audit Logs Table
    if not table_exists("admin_audit_logs"):
        execute_query("""
            CREATE TABLE admin_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                admin_username TEXT,
                action TEXT NOT NULL,
                target TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # 3. Seed Default Admin User if missing
    AdminModel.seed_default_admin()


class AdminModel:
    """Data access layer for admin users and audit operations."""

    @staticmethod
    def seed_default_admin():
        """Ensure initial admin account 'adminuser85' exists with secure hashed password."""
        existing = execute_one("SELECT * FROM admin_users WHERE username = ?", ("adminuser85",))
        if not existing:
            hashed_pw = bcrypt.hashpw("adminuser85".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            execute_insert(
                """INSERT INTO admin_users (username, email, password_hash, role, is_active)
                   VALUES (?, ?, ?, 'admin', 1)""",
                ("adminuser85", "admin@careerpilot.ai", hashed_pw)
            )

    @staticmethod
    def get_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Get an admin by username."""
        return execute_one("SELECT * FROM admin_users WHERE username = ?", (username,))

    @staticmethod
    def get_by_id(admin_id: int) -> Optional[Dict[str, Any]]:
        """Get an admin by ID (never returning password hash for general use)."""
        row = execute_one("SELECT id, username, email, role, is_active, created_at, last_login FROM admin_users WHERE id = ?", (admin_id,))
        return row

    @staticmethod
    def update_last_login(admin_id: int):
        """Update last login timestamp for admin."""
        execute_update(
            "UPDATE admin_users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (admin_id,)
        )

    @staticmethod
    def log_audit(admin_id: Optional[int], admin_username: str, action: str, target: str = "", ip_address: str = "") -> int:
        """Record an administrative audit log entry."""
        return execute_insert(
            """INSERT INTO admin_audit_logs (admin_id, admin_username, action, target, ip_address)
               VALUES (?, ?, ?, ?, ?)""",
            (admin_id, admin_username or "System", action, target, ip_address)
        )

    @staticmethod
    def get_audit_logs(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve recent administrative audit logs."""
        return execute_query(
            "SELECT * FROM admin_audit_logs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )

    @staticmethod
    def count_audit_logs() -> int:
        """Count total audit logs."""
        res = execute_one("SELECT COUNT(*) as count FROM admin_audit_logs")
        return res["count"] if res else 0
