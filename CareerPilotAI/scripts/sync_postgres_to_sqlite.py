#!/usr/bin/env python3
"""
CareerPilot AI — PostgreSQL to SQLite Reverse Delta Sync Tool
Emergency Rollback Utility

Purpose:
In the event that production switches to PostgreSQL and subsequently must roll back
to SQLite, this script reconciles any new rows created in PostgreSQL (e.g., new user
registrations, resumes, chat messages, problem submissions) back into the SQLite
database to prevent data loss.

Features:
- Dry-run mode by default (safe inspection).
- Transfers records in dependency topological order.
- Updates sqlite_sequence to prevent ID collisions on subsequent SQLite inserts.
- Runs PRAGMA foreign_key_check and PRAGMA integrity_check after reconciliation.
"""

import os
import sys
import sqlite3
import argparse
from typing import Dict, List, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.database.db import normalize_postgres_url

# Tables in dependency order (parents before children)
SYNC_TABLE_ORDER = [
    "users",
    "resumes",
    "resume_analysis",
    "resume_versions",
    "career_profiles",
    "chat_sessions",
    "chat_history",
    "problems",
    "problem_submissions",
    "user_problem_analytics",
    "user_topic_scores",
    "user_streaks",
    "job_history",
    "interview_history",
    "learning_roadmaps",
    "notification_preferences",
    "job_notifications",
    "user_activity",
    "system_settings",
    "settings",
    "feedback",
]


def sync_delta(sqlite_path: str, pg_url: str, dry_run: bool = True):
    import psycopg2
    import psycopg2.extras

    print("=== CareerPilot AI Reverse Delta Sync (PostgreSQL -> SQLite) ===")
    print(f"SQLite Target : {sqlite_path}")
    print(f"PostgreSQL DSN: {pg_url.split('@')[-1] if '@' in pg_url else 'configured'}")
    print(f"Mode          : {'DRY RUN' if dry_run else 'LIVE RECONCILIATION'}")
    print("-" * 55)

    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

    dsn = normalize_postgres_url(pg_url)
    pg_conn = psycopg2.connect(dsn)
    pg_conn.autocommit = True
    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    total_new_rows = 0

    try:
        if not dry_run:
            sqlite_cur.execute("PRAGMA foreign_keys = OFF;")
            sqlite_cur.execute("BEGIN TRANSACTION;")

        for table in SYNC_TABLE_ORDER:
            # Check if table has 'id' primary key
            sqlite_cur.execute(f"PRAGMA table_info({table});")
            cols_info = sqlite_cur.fetchall()
            if not cols_info:
                continue

            col_names = [col[1] for col in cols_info]
            has_id = "id" in col_names

            if has_id:
                sqlite_cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table};")
                max_sqlite_id = sqlite_cur.fetchone()[0]

                pg_cur.execute(f"SELECT * FROM {table} WHERE id > %s ORDER BY id;", (max_sqlite_id,))
                new_rows = pg_cur.fetchall()
            else:
                # For composite or non-id tables, identify missing rows by primary keys
                pk_cols = [col[1] for col in cols_info if col[5] > 0]
                if not pk_cols:
                    continue
                pg_cur.execute(f"SELECT * FROM {table};")
                all_pg = pg_cur.fetchall()
                new_rows = []
                for p_row in all_pg:
                    where_clauses = " AND ".join(f"{col} = ?" for col in pk_cols)
                    pk_vals = tuple(p_row[col] for col in pk_cols)
                    sqlite_cur.execute(f"SELECT 1 FROM {table} WHERE {where_clauses};", pk_vals)
                    if not sqlite_cur.fetchone():
                        new_rows.append(p_row)

            if new_rows:
                total_new_rows += len(new_rows)
                print(f"[*] {table}: {len(new_rows)} new records found in PostgreSQL")

                if not dry_run:
                    placeholders = ", ".join(["?"] * len(col_names))
                    insert_sql = f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({placeholders});"
                    for r in new_rows:
                        vals = tuple(r[c] for c in col_names)
                        sqlite_cur.execute(insert_sql, vals)

                    # Update sqlite_sequence if table has an id
                    if has_id:
                        sqlite_cur.execute(f"SELECT MAX(id) FROM {table};")
                        new_max = sqlite_cur.fetchone()[0]
                        sqlite_cur.execute(
                            "INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?);",
                            (table, new_max)
                        )
            else:
                print(f"    {table}: in sync (0 new records)")

        if not dry_run:
            sqlite_cur.execute("COMMIT;")
            sqlite_cur.execute("PRAGMA foreign_keys = ON;")
            # Run foreign key checks
            sqlite_cur.execute("PRAGMA foreign_key_check;")
            fk_violations = sqlite_cur.fetchall()
            if fk_violations:
                print(f"[!] Warning: {len(fk_violations)} foreign key violations detected in SQLite post-sync!")
            else:
                print("[✓] SQLite foreign key integrity check PASSED.")

            sqlite_cur.execute("PRAGMA integrity_check;")
            integrity_result = sqlite_cur.fetchone()[0]
            print(f"[✓] SQLite integrity check: {integrity_result}")

    except Exception as e:
        if not dry_run:
            sqlite_conn.rollback()
        raise e
    finally:
        sqlite_conn.close()
        pg_conn.close()

    print("-" * 55)
    print(f"Total New Records Synchronized: {total_new_rows}")
    print("Reverse Sync Finished Successfully.")


def main():
    parser = argparse.ArgumentParser(description="Reverse Delta Sync Tool (PostgreSQL -> SQLite)")
    parser.add_argument("--sqlite-path", default="database.db", help="Target SQLite database path")
    parser.add_argument("--pg-url", required=True, help="Source PostgreSQL DATABASE_URL")
    parser.add_argument("--execute", action="store_true", help="Execute sync (defaults to dry-run)")

    args = parser.parse_args()
    sync_delta(args.sqlite_path, args.pg_url, dry_run=not args.execute)


if __name__ == "__main__":
    main()
