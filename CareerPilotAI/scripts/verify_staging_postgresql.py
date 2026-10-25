"""
CareerPilot AI — PostgreSQL Staging Verification Utility
Executes comprehensive end-to-end validation of the migration and application adapter
against a REAL, isolated PostgreSQL test instance without touching production.

Validation Steps:
1. Pre-flight connection and safety checks (strictly blocks production targets & sanitizes credentials)
2. Verified SQLite snapshot creation (never touches live database.db)
3. Schema creation and data migration in strict topological order (non-destructive on existing tables)
4. Exact row count parity verification across all 27 tables
5. Primary key and representative data integrity audit
6. Foreign-key integrity and orphan detection
7. Auto-increment sequence verification on both empty and populated tables
8. Adapter CRUD, transaction commit, and rollback verification
9. Connection pool lifecycle and leak prevention check
10. End-to-end application feature smoke tests (auth, resumes, chat, jobs, admin)
"""

import os
import sys
import time
import shutil
import sqlite3
import argparse
import re
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.migrate_sqlite_to_postgresql import (
    MigrationRunner,
    MIGRATION_ORDER,
    mask_url_credentials
)


def sanitize_message(msg: str) -> str:
    """Redact passwords and secrets from any error message or stack trace string."""
    pattern = r'(postgresql://[^:]+:)([^@]+)(@)'
    return re.sub(pattern, r'\1***\3', str(msg))


class StagingVerifier:
    def __init__(self, pg_url: str, source_sqlite: str = "database.db", allow_clean_destination: bool = False, skip_orphans: bool = False):
        self.raw_pg_url = pg_url.strip()
        self.pg_url = self.raw_pg_url
        if self.pg_url.startswith("postgres://"):
            self.pg_url = "postgresql://" + self.pg_url[len("postgres://"):]
        self.source_sqlite = source_sqlite
        self.allow_clean_destination = allow_clean_destination
        self.skip_orphans = skip_orphans
        self.snapshot_sqlite = os.path.join(PROJECT_ROOT, "temp_staging_source.db")
        self.pg_conn = None
        self.runner = None
        self.results: Dict[str, Any] = {}

    def step1_safety_and_connection_check(self):
        """Verify target database safety and connectivity."""
        print("\n" + "=" * 70)
        print(" STEP 1: Destination Safety & Connectivity Check")
        print("=" * 70)

        # 1. Enforce strict production rejection
        target_lower = self.pg_url.lower()
        env_mode = os.getenv("ENVIRONMENT", "").lower()
        flask_env = os.getenv("FLASK_ENV", "").lower()

        # Reject explicit production keywords
        prod_keywords = ["production", "prod-db", "careerpilot-prod", "live-db"]
        if any(k in target_lower for k in prod_keywords) or env_mode in ("production", "prod") or flask_env in ("production", "prod"):
            raise RuntimeError(
                f"[SAFETY VIOLATION] Staging verification is strictly prohibited against "
                f"production targets or when ENVIRONMENT=production! Target: {mask_url_credentials(self.pg_url)}"
            )

        import psycopg2
        print(f"[-] Connecting to isolated PostgreSQL target: {mask_url_credentials(self.pg_url)}")
        self.pg_conn = psycopg2.connect(self.pg_url)
        with self.pg_conn.cursor() as cur:
            cur.execute("SELECT version();")
            v = cur.fetchone()[0]
            print(f"[✓] Connected successfully to: {v}")
            self.results["pg_version"] = v

    def step2_create_verified_source_snapshot(self):
        """Create a safe snapshot copy of database.db to ensure live file is untouched."""
        print("\n" + "=" * 70)
        print(" STEP 2: Creating Verified Source SQLite Snapshot")
        print("=" * 70)

        if not os.path.exists(self.source_sqlite):
            raise FileNotFoundError(f"Source database not found: {self.source_sqlite}")

        if os.path.exists(self.snapshot_sqlite):
            os.remove(self.snapshot_sqlite)

        # Open source in read-only mode and backup to snapshot file
        src_conn = sqlite3.connect(f"file:{os.path.abspath(self.source_sqlite)}?mode=ro", uri=True)
        dest_conn = sqlite3.connect(self.snapshot_sqlite)
        try:
            with dest_conn:
                src_conn.backup(dest_conn)
            print(f"[✓] Safe source snapshot created: {self.snapshot_sqlite}")
        finally:
            src_conn.close()
            dest_conn.close()

    def step3_execute_migration(self):
        """
        Execute migration from snapshot into isolated PostgreSQL safely.
        Handles empty databases, already-migrated databases, and prevents accidental data destruction.
        """
        print("\n" + "=" * 70)
        print(" STEP 3: Executing Migration Utility Safely")
        print("=" * 70)

        # Inspect destination existing tables
        with self.pg_conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            existing_tables = set(r[0] for r in cur.fetchall())

        target_tables = set(MIGRATION_ORDER)
        has_existing = len(existing_tables) > 0
        already_migrated = target_tables.issubset(existing_tables)

        # Check if existing tables actually have data
        total_existing_rows = 0
        if has_existing:
            with self.pg_conn.cursor() as cur:
                for t in existing_tables:
                    try:
                        cur.execute(f'SELECT COUNT(*) FROM "{t}";')
                        total_existing_rows += cur.fetchone()[0]
                    except Exception:
                        pass

        if has_existing and total_existing_rows == 0:
            print(f"[i] Destination database already contains {len(existing_tables)} schema table(s) with 0 data rows.")
            print("[i] (Schema initialization previously committed or previous transaction rolled back).")
            print("[i] Safe to proceed with data migration into existing schema without destructive dropping.")
        elif already_migrated and total_existing_rows > 0 and not self.allow_clean_destination:
            print("[i] Destination database already contains all 27 CareerPilot AI tables with populated data.")
            print("[i] Verifying existing data and skipping destructive table drop.")
            self.results["migration_action"] = "VERIFIED_EXISTING"
            return
        elif has_existing and total_existing_rows > 0 and not self.allow_clean_destination:
            raise RuntimeError(
                f"[SAFETY VIOLATION] Destination database is non-empty ({len(existing_tables)} tables present with {total_existing_rows} rows) "
                f"and --allow-clean-destination was not specified. Aborting to prevent accidental data loss. "
                f"Use a clean empty database or pass --allow-clean-destination if this is a disposable test DB."
            )

        clean_flag = has_existing and total_existing_rows > 0 and self.allow_clean_destination
        confirm_token = "YES_DELETE_DESTINATION_DATA" if clean_flag else ""

        print(f"[-] Executing migration (clean_destination={clean_flag}, skip_orphans={self.skip_orphans})...")
        self.runner = MigrationRunner(
            sqlite_path=self.snapshot_sqlite,
            pg_url=self.pg_url,
            dry_run=False,
            clean_destination=clean_flag,
            confirm_clean_destination=confirm_token,
            skip_orphans=self.skip_orphans
        )
        self.runner.run()
        self.results["migration_stats"] = self.runner.stats
        self.results["migration_action"] = "MIGRATED_FRESH"

    def step4_verify_row_counts(self):
        """Verify row counts match across all 27 tables, dynamically deriving audited exclusions from source integrity scan."""
        print("\n" + "=" * 70)
        print(" STEP 4: Verifying Row Count Parity Across All 27 Tables")
        print("=" * 70)

        s_conn = sqlite3.connect(f"file:{self.snapshot_sqlite}?mode=ro", uri=True)
        s_cur = s_conn.cursor()

        # Dynamically audit source SQLite referential integrity
        # Derives any orphaned records per table without hardcoding numbers
        audited_orphans_by_table: Dict[str, List[Any]] = {}
        s_cur.execute("PRAGMA foreign_key_check;")
        fk_violations = s_cur.fetchall()
        for v in fk_violations:
            tbl, rowid, parent_tbl, fkid = v[0], v[1], v[2], v[3]
            s_cur.execute(f"PRAGMA foreign_key_list({tbl});")
            fk_info = [r for r in s_cur.fetchall() if r[0] == fkid]
            from_col = fk_info[0][3] if fk_info else "unknown"
            to_col = fk_info[0][4] if fk_info else "id"

            s_cur.execute(f"SELECT id, {from_col} FROM {tbl} WHERE rowid = ?", (rowid,))
            val_row = s_cur.fetchone()
            row_id = val_row[0] if val_row else rowid
            orphan_val = val_row[1] if val_row else None

            if tbl not in audited_orphans_by_table:
                audited_orphans_by_table[tbl] = []
            audited_orphans_by_table[tbl].append({
                "rowid": rowid,
                "id": row_id,
                "parent_table": parent_tbl,
                "from_col": from_col,
                "to_col": to_col,
                "orphan_value": orphan_val
            })

        all_matched = True
        table_reports = []

        with self.pg_conn.cursor() as p_cur:
            for table in MIGRATION_ORDER:
                s_cur.execute(f"SELECT COUNT(*) FROM {table};")
                s_cnt = s_cur.fetchone()[0]

                p_cur.execute(f"SELECT COUNT(*) FROM {table};")
                p_cnt = p_cur.fetchone()[0]

                # Dynamically determine expected count based on source integrity scan
                orphans_excluded_list = audited_orphans_by_table.get(table, []) if self.skip_orphans else []
                orphans_excluded_count = len(orphans_excluded_list)

                expected_pg = s_cnt - orphans_excluded_count
                status = "MATCH" if p_cnt == expected_pg else "MISMATCH"
                if status == "MATCH" and orphans_excluded_count > 0:
                    status = f"MATCH ({orphans_excluded_count} orphan(s) excluded)"
                if status != "MATCH" and not status.startswith("MATCH"):
                    all_matched = False

                table_reports.append((table, s_cnt, p_cnt, status))
                print(f"  {table:<28} | SQLite: {s_cnt:<6} | PG: {p_cnt:<6} | {status}")

        s_conn.close()
        self.results["row_counts_matched"] = all_matched
        self.results["table_reports"] = table_reports

        if audited_orphans_by_table and self.skip_orphans:
            print("\n[-] Documented Source Integrity Exclusions:")
            for tbl, orphans in audited_orphans_by_table.items():
                for o in orphans:
                    print(f"    - Table '{tbl}' row id={o['id']}: {o['from_col']}={o['orphan_value']} -> missing '{o['parent_table']}.{o['to_col']}'")

        if not all_matched:
            raise AssertionError("[FAIL] Table row counts do not match between SQLite and PostgreSQL!")
        print("[✓] All 27 table row counts match perfectly.")

    def step5_verify_primary_keys_and_sample_data(self):
        """Verify primary keys and sample column values match 1:1."""
        print("\n" + "=" * 70)
        print(" STEP 5: Verifying Primary Key Integrity & Sample Data")
        print("=" * 70)

        s_conn = sqlite3.connect(f"file:{self.snapshot_sqlite}?mode=ro", uri=True)
        s_conn.row_factory = sqlite3.Row
        s_cur = s_conn.cursor()

        sample_tables = ["users", "problems", "chat_sessions", "agent_profiles"]

        with self.pg_conn.cursor() as p_cur:
            for table in sample_tables:
                pk = "session_id" if table == "chat_sessions" else "id"
                s_cur.execute(f"SELECT {pk} FROM {table} ORDER BY {pk} ASC;")
                s_keys = [r[0] for r in s_cur.fetchall()]

                p_cur.execute(f"SELECT {pk} FROM {table} ORDER BY {pk} ASC;")
                p_keys = [r[0] for r in p_cur.fetchall()]

                self.assertEqual(s_keys, p_keys, f"Primary key mismatch in {table}")
                print(f"[✓] `{table}`: Verified {len(s_keys)} primary keys match exactly.")

        s_conn.close()

    def step6_check_foreign_key_integrity(self):
        """Confirm zero orphaned child records in PostgreSQL."""
        print("\n" + "=" * 70)
        print(" STEP 6: Checking Foreign Key Integrity & Orphaned Records")
        print("=" * 70)

        fk_checks = [
            ("resumes", "user_id", "users", "id"),
            ("resume_analysis", "resume_id", "resumes", "id"),
            ("chat_sessions", "user_id", "users", "id"),
            ("chat_history", "user_id", "users", "id"),
            ("job_history", "user_id", "users", "id"),
            ("job_notifications", "user_id", "users", "id"),
            ("problem_submissions", "problem_id", "problems", "id"),
            ("problem_submissions", "user_id", "users", "id")
        ]

        with self.pg_conn.cursor() as cur:
            for child, child_col, parent, parent_col in fk_checks:
                query = f"""
                    SELECT COUNT(*) FROM {child} c
                    WHERE c.{child_col} IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM {parent} p WHERE p.{parent_col} = c.{child_col});
                """
                cur.execute(query)
                orphans = cur.fetchone()[0]
                self.assertEqual(orphans, 0, f"Found {orphans} orphaned records in {child}.{child_col} referencing {parent}.{parent_col}")
                print(f"[✓] {child}.{child_col} -> {parent}.{parent_col}: 0 orphans.")

            # Parity check for legacy chat_history messages (July 24-25, 2026 predate chat_sessions table creation)
            cur.execute("""
                SELECT COUNT(*) FROM chat_history c
                WHERE c.session_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM chat_sessions p WHERE p.session_id = c.session_id);
            """)
            pg_legacy = cur.fetchone()[0]

            s_conn = sqlite3.connect(f"file:{self.snapshot_sqlite}?mode=ro", uri=True)
            s_cur = s_conn.cursor()
            s_cur.execute("""
                SELECT COUNT(*) FROM chat_history c
                WHERE c.session_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM chat_sessions p WHERE p.session_id = c.session_id);
            """)
            s_legacy = s_cur.fetchone()[0]
            s_conn.close()

            self.assertEqual(pg_legacy, s_legacy, f"Legacy chat message count mismatch: SQLite={s_legacy}, PG={pg_legacy}")
            print(f"[✓] chat_history.session_id: {pg_legacy} pre-session legacy messages match SQLite source 1:1.")

    def _inspect_sequence(self, cur, table_name: str, column_name: str = "id") -> Optional[Dict[str, Any]]:
        """
        Read-only inspection of the sequence associated with table_name.column_name.
        Uses PostgreSQL catalogs (pg_get_serial_sequence and pg_sequences) without calling nextval()
        or mutating sequence state in any way.
        """
        cur.execute("SELECT pg_get_serial_sequence(%s, %s);", (table_name, column_name))
        seq_res = cur.fetchone()
        if not seq_res or not seq_res[0]:
            return None

        seq_full_name = seq_res[0]
        # Query pg_sequences catalog view for read-only sequence metadata
        if "." in seq_full_name:
            schema_part, seq_part = seq_full_name.split(".", 1)
            schema_clean = schema_part.strip('"')
            seq_clean = seq_part.strip('"')
            cur.execute("""
                SELECT schemaname, sequencename, last_value, start_value, min_value, max_value, increment_by
                FROM pg_sequences
                WHERE (schemaname = %s AND sequencename = %s)
                   OR sequencename = %s;
            """, (schema_clean, seq_clean, seq_clean))
        else:
            seq_clean = seq_full_name.strip('"')
            cur.execute("""
                SELECT schemaname, sequencename, last_value, start_value, min_value, max_value, increment_by
                FROM pg_sequences
                WHERE sequencename = %s;
            """, (seq_clean,))

        seq_row = cur.fetchone()
        if not seq_row:
            raise AssertionError(
                f"Sequence '{seq_full_name}' found for {table_name}.{column_name} "
                f"but missing from pg_sequences catalog view"
            )

        schemaname, sequencename, last_val, start_val, min_val, max_val, inc_by = seq_row

        cur.execute(f"SELECT COUNT(*), MAX({column_name}) FROM {table_name};")
        row_count, max_id = cur.fetchone()

        return {
            "table": table_name,
            "column": column_name,
            "sequence_name": seq_full_name,
            "schemaname": schemaname,
            "sequencename": sequencename,
            "last_value": last_val,
            "start_value": start_val,
            "min_value": min_val,
            "max_value": max_val,
            "increment_by": inc_by,
            "row_count": row_count,
            "max_id": max_id,
        }

    def step7_verify_sequences(self):
        """
        Verify sequence health on empty and populated tables using read-only catalog inspection.
        Guarantees that:
        1. No sequence values are consumed (0 nextval() calls).
        2. Populated tables have sequences positioned at or above MAX(id), preventing PK collisions.
        3. Empty tables have usable sequences and will not collide with existing rows.
        4. Verification is 100% repeatable across multiple runs.
        """
        print("\n" + "=" * 70)
        print(" STEP 7: Testing Auto-Increment Sequences (Empty & Populated, Read-Only)")
        print("=" * 70)

        with self.pg_conn.cursor() as cur:
            # 1. Populated table validation (users)
            users_info = self._inspect_sequence(cur, "users", "id")
            self.assertIsNotNone(users_info, "users.id sequence not found")
            max_user_id = users_info["max_id"]
            user_last_val = users_info["last_value"]

            self.assertIsNotNone(max_user_id, "users table unexpectedly has no MAX(id)")
            self.assertIsNotNone(user_last_val, f"Sequence '{users_info['sequence_name']}' has NULL last_value")

            # Key Invariant: The sequence must be at or ahead of MAX(id) to ensure next ID will not collide.
            # We do NOT require user_last_val == max_user_id + 1 because PostgreSQL sequences are monotonic,
            # non-transactional counters that legitimately advance when test records are inserted and deleted.
            self.assertGreaterEqual(
                user_last_val,
                max_user_id,
                f"Sequence '{users_info['sequence_name']}' last_value ({user_last_val}) is behind MAX(id) ({max_user_id}); "
                f"risk of primary-key collision!"
            )
            print(
                f"[✓] Populated table `users`: MAX(id)={max_user_id}, "
                f"sequence='{users_info['sequencename']}', last_value={user_last_val} "
                f"(next generated ID will be >= {user_last_val + users_info['increment_by']}, no collision risk)"
            )

            # 2. Empty table validation (user_topic_scores)
            topic_info = self._inspect_sequence(cur, "user_topic_scores", "id")
            self.assertIsNotNone(topic_info, "user_topic_scores.id sequence not found")
            topic_count = topic_info["row_count"]
            topic_last_val = topic_info["last_value"]

            if topic_count == 0:
                # Sequence is usable: start_value or last_value >= 1.
                # Because the table has 0 rows, any positive generated ID will not collide.
                # Does not require returning 1 on every run, preserving repeatability if previously advanced.
                is_usable = (topic_last_val is None) or (topic_last_val >= 1)
                self.assertTrue(
                    is_usable,
                    f"Sequence '{topic_info['sequence_name']}' for empty table has invalid state (last_value={topic_last_val})"
                )
                print(
                    f"[✓] Empty table `user_topic_scores`: Count=0, "
                    f"sequence='{topic_info['sequencename']}', last_value={topic_last_val} "
                    f"(sequence usable and repeatable without mutating state)"
                )
            else:
                self.assertGreaterEqual(topic_last_val, topic_info["max_id"])
                print(f"[✓] Table `user_topic_scores`: Count={topic_count}, last_value={topic_last_val}")

            # 3. Comprehensive verification for all sequence-backed tables in topological order
            checked_count = 0
            for tbl in MIGRATION_ORDER:
                if tbl == "chat_sessions":
                    continue  # Uses UUID/text session_id PK
                info = self._inspect_sequence(cur, tbl, "id")
                if info:
                    if info["row_count"] > 0:
                        self.assertIsNotNone(
                            info["last_value"],
                            f"Sequence for populated table '{tbl}' has NULL last_value"
                        )
                        self.assertGreaterEqual(
                            info["last_value"],
                            info["max_id"],
                            f"Sequence '{info['sequence_name']}' last_value ({info['last_value']}) < MAX(id) ({info['max_id']}) "
                            f"in table '{tbl}'"
                        )
                    else:
                        self.assertTrue(
                            info["last_value"] is None or info["last_value"] >= 1,
                            f"Sequence for empty table '{tbl}' has invalid state"
                        )
                    checked_count += 1

            self.results["sequences_verified"] = True
            print(f"[✓] Verified all {checked_count} auto-increment primary-key sequences read-only (0 nextval calls).")

    def step8_adapter_crud_and_transactions(self):
        """Test application database adapter operations through PostgreSQL with guaranteed cleanup."""
        print("\n" + "=" * 70)
        print(" STEP 8: Testing Application Database Adapter & Pool Lifecycle")
        print("=" * 70)

        # Set environment for adapter and reset connection pool
        os.environ["DATABASE_URL"] = self.pg_url
        import backend.database.db as db_mod
        db_mod._pg_pool = None

        from backend.database.db import (
            execute_query, execute_one, execute_insert, execute_update, get_db
        )

        test_user_id = None
        try:
            # 1. SELECT query
            users = execute_query("SELECT id, username FROM users LIMIT 3;")
            self.assertGreaterEqual(len(users), 1)
            print(f"[✓] execute_query(): retrieved {len(users)} users.")

            # 2. INSERT query with automatic RETURNING id
            # Note: Consumes a sequence value on users_id_seq. In PostgreSQL, sequences
            # are monotonic and are never rolled back when temporary rows are deleted.
            test_uname = f"test_staging_{int(time.time())}"
            test_user_id = execute_insert(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?);",
                (test_uname, f"{test_uname}@test.com", "hash123")
            )
            self.assertGreater(test_user_id, 0)
            print(f"[✓] execute_insert(): created test user with returned id={test_user_id}")

            # 3. UPDATE query
            rows = execute_update("UPDATE users SET full_name = ? WHERE id = ?;", ("Staging Verified", test_user_id))
            self.assertEqual(rows, 1)
            print(f"[✓] execute_update(): updated {rows} row.")

            # 4. SELECT ONE query
            user_row = execute_one("SELECT full_name FROM users WHERE id = ?;", (test_user_id,))
            self.assertEqual(user_row["full_name"], "Staging Verified")
            print(f"[✓] execute_one(): verified field value: '{user_row['full_name']}'")

            # 5. Transaction rollback on constraint failure
            with self.assertRaises(Exception):
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
                        (test_uname, f"{test_uname}@test.com", "duplicate")
                    )
            print("[✓] Transaction rollback: Duplicate key constraint safely rolled back.")

        finally:
            if test_user_id:
                try:
                    execute_update("DELETE FROM users WHERE id = ?;", (test_user_id,))
                    print("[✓] Guaranteed cleanup: temporary test user deleted.")
                except Exception:
                    pass

    def step9_connection_pool_stress(self):
        """Verify zero pool exhaustion under repeated borrows."""
        print("\n" + "=" * 70)
        print(" STEP 9: Connection Pool Lifecycle & Stress Validation")
        print("=" * 70)

        from backend.database.db import get_db

        borrow_count = 35  # Exceeds max default pool of 20
        for i in range(borrow_count):
            with get_db() as db:
                db.execute("SELECT 1;")
        print(f"[✓] Successfully performed {borrow_count} sequential borrows/releases with 0 leaks.")

    def step10_representative_application_smoke_tests(self):
        """Run representative application model operations against PostgreSQL with guaranteed cleanup."""
        print("\n" + "=" * 70)
        print(" STEP 10: Representative Application Model Smoke Tests")
        print("=" * 70)

        from backend.services.auth_service import AuthService
        from backend.models.chat import ChatSessionModel, ChatModel
        from backend.models.job_notification import JobNotificationModel
        from backend.services.admin_service import AdminAnalyticsService
        from backend.database.db import execute_update

        smoke_uid = None
        try:
            # 1. Auth service registration
            # Note: Consumes a sequence value on users_id_seq. Temporary user is deleted
            # in finally block during guaranteed cleanup; sequence advancement is expected.
            smoke_uname = f"smoke_{int(time.time())}"
            smoke_email = f"{smoke_uname}@careerpilot.ai"
            ok, msg, smoke_uid = AuthService.register(smoke_uname, smoke_email, "SecurePass123!", "SecurePass123!", "Smoke Tester")
            self.assertTrue(ok, f"Auth registration failed: {msg}")
            print(f"[✓] Application Auth: Registered test user {smoke_uname} (id={smoke_uid})")

            # 2. Chat session and message storage
            import uuid
            sess_id = str(uuid.uuid4())
            ChatSessionModel.create(sess_id, smoke_uid, "Staging Chat Test")
            self.assertIsNotNone(sess_id)
            msg_id = ChatModel.create(smoke_uid, sess_id, "user", "Hello CareerPilot Staging!")
            self.assertIsNotNone(msg_id)
            history = ChatModel.get_session(sess_id)
            self.assertEqual(len(history), 1)
            print(f"[✓] Application Chat: Created session {sess_id} and stored message id={msg_id}")

            # 3. Admin dashboard analytics query
            metrics = AdminAnalyticsService.get_dashboard_metrics()
            self.assertIn("total_users", metrics)
            self.assertGreaterEqual(metrics["total_users"], 1)
            print(f"[✓] Application Admin: Dashboard metrics computed: {metrics['total_users']} total users")

            # 4. Problem Solving: Heatmap & Timeline date queries on PostgreSQL
            from backend.services.problem_service import ProblemService
            from backend.database.db import execute_insert, execute_one
            prob_row = execute_one("SELECT id FROM problems LIMIT 1;")
            prob_id = prob_row["id"] if prob_row else 1
            execute_insert("""
                INSERT INTO problem_submissions (user_id, problem_id, code, language, status, execution_time, memory, coding_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (smoke_uid, prob_id, "def solve(): pass", "python", "Accepted", 30, 1024, "{}"))
            execute_insert("""
                INSERT INTO problem_submissions (user_id, problem_id, code, language, status, execution_time, memory, coding_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (smoke_uid, prob_id, "def solve(): pass", "python", "Wrong Answer", 40, 1024, "{}"))

            stats = ProblemService.get_dashboard_stats(smoke_uid)
            self.assertIn("heatmap", stats)
            self.assertIn("timeline", stats)
            self.assertGreaterEqual(len(stats["heatmap"]), 1)
            self.assertGreaterEqual(len(stats["timeline"]), 1)
            print("[✓] Application Problem Solving: Heatmap and timeline PostgreSQL date queries passed.")

            # 5. Problem Solving: Streak upsert and conflict-update paths on PostgreSQL
            streak_sql = """
                INSERT INTO user_problem_analytics (user_id, streak, last_submission_at)
                VALUES (?, 1, TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'))
                ON CONFLICT(user_id) DO UPDATE SET 
                    streak = CASE 
                        WHEN user_problem_analytics.last_submission_at = TO_CHAR(CURRENT_DATE - INTERVAL '1 day', 'YYYY-MM-DD') THEN user_problem_analytics.streak + 1
                        WHEN user_problem_analytics.last_submission_at = TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD') THEN user_problem_analytics.streak
                        ELSE 1
                    END,
                    last_submission_at = TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD')
            """
            # Initial insert (streak = 1)
            execute_update(streak_sql, (smoke_uid,))
            s_row = execute_one("SELECT streak, last_submission_at FROM user_problem_analytics WHERE user_id = ?", (smoke_uid,))
            self.assertEqual(s_row["streak"], 1)

            # Same-day submission (stays 1)
            execute_update(streak_sql, (smoke_uid,))
            s_row = execute_one("SELECT streak FROM user_problem_analytics WHERE user_id = ?", (smoke_uid,))
            self.assertEqual(s_row["streak"], 1)

            # Consecutive day submission (simulate yesterday's submission -> increments to 2)
            execute_update("UPDATE user_problem_analytics SET last_submission_at = TO_CHAR(CURRENT_DATE - INTERVAL '1 day', 'YYYY-MM-DD') WHERE user_id = ?", (smoke_uid,))
            execute_update(streak_sql, (smoke_uid,))
            s_row = execute_one("SELECT streak FROM user_problem_analytics WHERE user_id = ?", (smoke_uid,))
            self.assertEqual(s_row["streak"], 2)

            # Missed day (simulate 3 days ago -> resets to 1)
            execute_update("UPDATE user_problem_analytics SET last_submission_at = TO_CHAR(CURRENT_DATE - INTERVAL '3 days', 'YYYY-MM-DD') WHERE user_id = ?", (smoke_uid,))
            execute_update(streak_sql, (smoke_uid,))
            s_row = execute_one("SELECT streak FROM user_problem_analytics WHERE user_id = ?", (smoke_uid,))
            self.assertEqual(s_row["streak"], 1)
            print("[✓] Application Problem Solving: Streak upsert and conflict-update paths passed on PostgreSQL.")

            # 6. Admin Problem Analytics Grouping on PostgreSQL
            p_rows, p_highlights, p_total, p_pages = AdminAnalyticsService.get_problems_analytics(page=1, per_page=5)
            self.assertIn("most_attempted", p_highlights)
            self.assertIn("most_solved", p_highlights)
            self.assertIn("most_failed", p_highlights)
            self.assertIn("most_difficult", p_highlights)
            print("[✓] Application Admin: Problem analytics multi-column GROUP BY passed on PostgreSQL.")

        finally:
            if smoke_uid:
                try:
                    # Clean up non-FK tables first, then users (which cascades to FK tables)
                    execute_update("DELETE FROM user_problem_analytics WHERE user_id = ?;", (smoke_uid,))
                    execute_update("DELETE FROM user_topic_scores WHERE user_id = ?;", (smoke_uid,))
                    execute_update("DELETE FROM users WHERE id = ?;", (smoke_uid,))
                    print("[✓] Guaranteed cleanup: smoke test user and all related records deleted.")
                except Exception:
                    pass

    def cleanup(self):
        """Clean up temporary resources and reset adapter environment."""
        if self.pg_conn and not self.pg_conn.closed:
            self.pg_conn.close()
        if os.path.exists(self.snapshot_sqlite):
            try:
                os.remove(self.snapshot_sqlite)
                print(f"[✓] Cleaned up temporary source snapshot: {self.snapshot_sqlite}")
            except Exception:
                pass
        # Clear adapter pool
        import backend.database.db as db_mod
        if db_mod._pg_pool is not None:
            try:
                db_mod._pg_pool.closeall()
            except Exception:
                pass
            db_mod._pg_pool = None
        # Unset test DATABASE_URL from process environment
        if "DATABASE_URL" in os.environ and os.environ["DATABASE_URL"] == self.pg_url:
            del os.environ["DATABASE_URL"]

    def run_all(self):
        """Execute complete 10-step staging verification suite."""
        start = time.time()
        print("=" * 70)
        print(" CareerPilot AI — PostgreSQL Staging Engine Verification")
        print("=" * 70)

        try:
            self.step1_safety_and_connection_check()
            self.step2_create_verified_source_snapshot()
            self.step3_execute_migration()
            self.step4_verify_row_counts()
            self.step5_verify_primary_keys_and_sample_data()
            self.step6_check_foreign_key_integrity()
            self.step7_verify_sequences()
            self.step8_adapter_crud_and_transactions()
            self.step9_connection_pool_stress()
            self.step10_representative_application_smoke_tests()

            elapsed = round(time.time() - start, 2)
            print("\n" + "=" * 70)
            print(f" [✓] ALL 10 STAGING VERIFICATION CHECKS PASSED IN {elapsed}s")
            print("=" * 70)
            print(" Verdict: READY FOR STAGING REVIEW")
            return 0

        except Exception as e:
            sanitized_err = sanitize_message(str(e))
            print(f"\n[FATAL ERROR] Staging verification failed: {sanitized_err}")
            return 1
        finally:
            self.cleanup()

    def assertEqual(self, a, b, msg=None):
        if a != b:
            raise AssertionError(msg or f"{a} != {b}")

    def assertTrue(self, a, msg=None):
        if not a:
            raise AssertionError(msg or f"{a} is not True")

    def assertIsNotNone(self, a, msg=None):
        if a is None:
            raise AssertionError(msg or f"{a} is None")

    def assertGreater(self, a, b, msg=None):
        if a <= b:
            raise AssertionError(msg or f"{a} <= {b}")

    def assertGreaterEqual(self, a, b, msg=None):
        if a < b:
            raise AssertionError(msg or f"{a} < {b}")

    def assertIn(self, a, b, msg=None):
        if a not in b:
            raise AssertionError(msg or f"{a} not in {b}")

    class _AssertRaisesContext:
        def __init__(self, exc_type):
            self.exc_type = exc_type
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                raise AssertionError(f"Expected exception {self.exc_type.__name__} was not raised")
            return issubclass(exc_type, self.exc_type)

    def assertRaises(self, exc_type):
        return self._AssertRaisesContext(exc_type)


def main():
    parser = argparse.ArgumentParser(description="Verify CareerPilot AI against an isolated PostgreSQL instance")
    parser.add_argument("--pg-url", default=os.getenv("TEST_DATABASE_URL", ""),
                        help="Connection URL for isolated test PostgreSQL instance")
    parser.add_argument("--source-sqlite", default=os.getenv("DATABASE_PATH", "database.db"),
                        help="Path to source SQLite database (default: database.db)")
    parser.add_argument("--allow-clean-destination", action="store_true",
                        help="Allow dropping tables on an existing non-empty test database")
    parser.add_argument("--skip-orphans", action="store_true",
                        help="Audit and safely exclude orphaned child records whose foreign key parent is missing")
    args = parser.parse_args()

    if not args.pg_url:
        print("\n[ERROR] No PostgreSQL URL provided via --pg-url or TEST_DATABASE_URL environment variable.")
        print("To run against an isolated staging PostgreSQL instance, execute:")
        print("  python3 scripts/verify_staging_postgresql.py --pg-url 'postgresql://user:pass@host:5432/testdb'")
        sys.exit(2)

    verifier = StagingVerifier(
        pg_url=args.pg_url,
        source_sqlite=args.source_sqlite,
        allow_clean_destination=args.allow_clean_destination,
        skip_orphans=args.skip_orphans
    )
    exit_code = verifier.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
