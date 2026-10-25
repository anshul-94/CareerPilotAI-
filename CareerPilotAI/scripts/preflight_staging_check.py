"""
CareerPilot AI — Staging Connection Preflight Script
Performs a strictly READ-ONLY connectivity and identity check against
the Supabase staging database supplied via TEST_DATABASE_URL.

Guarantees:
- Strictly read-only (zero DDL, zero DML, zero table creations, zero writes).
- Never prints passwords, secrets, or raw connection strings.
- Only uses TEST_DATABASE_URL (never DATABASE_URL).
- Validates isolated database identity and reports existing tables.
"""

import os
import sys
import re
from typing import Optional

def mask_connection_string(url: str) -> str:
    """Mask password credentials in any database URL."""
    if not url:
        return "<EMPTY>"
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1***\3', url)

def mask_error(err: Exception) -> str:
    """Sanitize error message to ensure no connection secrets leak."""
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1***\3', str(err))

def run_preflight():
    print("=" * 70)
    print(" CareerPilot AI — Staging Database Preflight Verification")
    print("=" * 70)

    # 1. Read exclusively from TEST_DATABASE_URL
    test_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not test_url:
        print("\n[PREFLIGHT STATUS] STOPPED — TEST_DATABASE_URL is not set.")
        print("\nAction required:")
        print("  Export your Supabase staging connection URL in your terminal:")
        print("    export TEST_DATABASE_URL='postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres'")
        print("  Then re-run this preflight command.")
        sys.exit(1)

    # Normalize protocol scheme for psycopg2 if needed
    normalized_url = test_url
    if normalized_url.startswith("postgres://"):
        normalized_url = "postgresql://" + normalized_url[len("postgres://"):]

    masked_target = mask_connection_string(test_url)
    print(f"\n[-] Validating staging target: {masked_target}")

    # 2. Safety checks against production markers
    target_lower = test_url.lower()
    prod_markers = ["careerpilot-prod", "production-db", "live-db"]
    env_mode = os.getenv("ENVIRONMENT", "").lower()
    if any(m in target_lower for m in prod_markers) or env_mode in ("production", "prod"):
        print(f"\n[PREFLIGHT STATUS] BLOCKED — Target appears to be a production database: {masked_target}")
        sys.exit(1)

    # 3. Execute strictly read-only inspection
    try:
        import psycopg2
        conn = psycopg2.connect(normalized_url, connect_timeout=10)
        conn.autocommit = True
    except Exception as e:
        print("\n[PREFLIGHT STATUS] CONNECTION FAILED")
        print(f"Error: {mask_error(e)}")
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            # Server version
            cur.execute("SELECT version();")
            pg_version = cur.fetchone()[0]

            # Database identity & user
            cur.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();")
            row = cur.fetchone()
            current_db = row[0]
            current_user = row[1]
            server_ip = row[2] or "managed-cloud"
            server_port = row[3] or "pooler"

            # Check public schema tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [r[0] for r in cur.fetchall()]

        print("\n" + "-" * 70)
        print(" PREFLIGHT INSPECTION REPORT")
        print("-" * 70)
        print(f"  Connection Status  : [✓] SUCCESS (Authenticated)")
        print(f"  PostgreSQL Server  : {pg_version.split(',')[0]}")
        print(f"  Target Host        : {masked_target.split('@')[-1]}")
        print(f"  Current Database   : {current_db}")
        print(f"  Current User       : {current_user}")
        print(f"  Public Tables Count: {len(tables)}")
        
        if tables:
            print(f"  Existing Tables    : {', '.join(tables[:10])}" + (" ..." if len(tables) > 10 else ""))
            from scripts.migrate_sqlite_to_postgresql import MIGRATION_ORDER
            overlap = set(tables).intersection(set(MIGRATION_ORDER))
            print(f"  CareerPilot Overlap: {len(overlap)} of 27 tables present")
        else:
            print(f"  Existing Tables    : None (Clean empty database ready for migration)")

        print("-" * 70)
        print("[✓] Preflight completed safely with ZERO writes or schema mutations.")
        print("=" * 70)

    except Exception as e:
        print("\n[PREFLIGHT STATUS] QUERY FAILED")
        print(f"Error: {mask_error(e)}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_preflight()
