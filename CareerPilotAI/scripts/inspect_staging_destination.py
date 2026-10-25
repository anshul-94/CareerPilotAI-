"""
CareerPilot AI — Read-Only Staging Destination State Inspector
Inspects the PostgreSQL staging destination to verify:
1. Public schema table count
2. Row counts across all migrated tables
3. Whether data transaction rolled back completely

Safety:
- Strictly READ-ONLY (set_session(readonly=True))
- Redacts all passwords and credentials
- Performs zero DDL or DML mutations
"""

import os
import sys
import argparse
import re

# Redact credentials
def mask_credentials(url: str) -> str:
    if not url:
        return "<unset>"
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1***\3', url)

def main():
    parser = argparse.ArgumentParser(description="Read-only staging destination inspector")
    parser.add_argument("--pg-url", default=None, help="PostgreSQL connection string (defaults to TEST_DATABASE_URL)")
    args = parser.parse_args()

    raw_url = args.pg_url or os.getenv("TEST_DATABASE_URL", "").strip()
    if not raw_url:
        print("[INSPECTION ERROR] Neither --pg-url nor TEST_DATABASE_URL was provided.")
        print("Please export TEST_DATABASE_URL='...' or pass --pg-url '...'")
        sys.exit(1)

    normalized_url = raw_url
    if normalized_url.startswith("postgres://"):
        normalized_url = "postgresql://" + normalized_url[len("postgres://"):]

    print("=" * 70)
    print(" CareerPilot AI — PostgreSQL Staging Destination Inspection (Read-Only)")
    print("=" * 70)
    print(f"Target: {mask_credentials(normalized_url)}")

    try:
        import psycopg2
    except ImportError:
        print("[ERROR] psycopg2-binary is required.")
        sys.exit(1)

    try:
        conn = psycopg2.connect(normalized_url)
        conn.set_session(readonly=True)
        cur = conn.cursor()

        # 1. Fetch public tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"\n[✓] Connected. Found {len(tables)} public table(s):")

        total_rows = 0
        table_counts = {}
        for tbl in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{tbl}";')
            count = cur.fetchone()[0]
            table_counts[tbl] = count
            total_rows += count
            status = "EMPTY (0 rows)" if count == 0 else f"{count} rows"
            print(f"    - {tbl:<30}: {status}")

        print("-" * 70)
        print(f"Total rows across all {len(tables)} tables: {total_rows}")
        if len(tables) > 0 and total_rows == 0:
            print("[VERIFICATION RESULT] Data transaction rolled back completely.")
            print("                      Schema tables exist (committed prior to data transaction),")
            print("                      but ZERO rows exist in any table.")
        elif total_rows > 0:
            print("[VERIFICATION RESULT] Non-zero rows detected. Transaction did not rollback or prior data exists.")
        else:
            print("[VERIFICATION RESULT] Database has 0 tables.")

        cur.close()
        conn.close()

    except Exception as e:
        safe_msg = re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1***\3', str(e))
        print(f"\n[ERROR] Failed to inspect destination: {safe_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
