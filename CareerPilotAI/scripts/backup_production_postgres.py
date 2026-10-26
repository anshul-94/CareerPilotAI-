#!/usr/bin/env python3
"""
CareerPilot AI — Safe Production PostgreSQL Backup Utility
Executes custom-format backup and verification against Supabase production target.
Guarantees:
- Strictly non-destructive (zero writes, zero schema changes).
- Validates target project identity ('bszcepdezyzfxwhqkejw') before connecting.
- Never prints secrets, connection strings, or passwords.
- Verifies output archive with pg_restore --list.
"""

import os
import sys
import getpass
import urllib.parse
import subprocess
import datetime
import shutil

EXPECTED_PROJECT_REF = "bszcepdezyzfxwhqkejw"
EXPECTED_HOST_SUBSTRING = "aws-0-ap-northeast-2.pooler.supabase.com"
EXPECTED_DB = "postgres"
EXPECTED_USER_SUBSTRING = "postgres.bszcepdezyzfxwhqkejw"

def find_binary(name: str) -> str:
    """Find pg_dump or pg_restore in homebrew or system PATH."""
    paths = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        shutil.which(name)
    ]
    for p in paths:
        if p and os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return ""

def main():
    print("=" * 70)
    print(" CareerPilot AI — Safe Production PostgreSQL Backup Utility")
    print("=" * 70)

    # 1. Check binaries
    pg_dump_bin = find_binary("pg_dump")
    pg_restore_bin = find_binary("pg_restore")

    if not pg_dump_bin or not pg_restore_bin:
        print("[ERROR] Required tools pg_dump and pg_restore were not found.")
        sys.exit(1)

    print(f"[✓] Tools verified:")
    print(f"    - pg_dump:    {pg_dump_bin}")
    print(f"    - pg_restore: {pg_restore_bin}")

    # 2. Get connection URL securely
    raw_url = os.getenv("PRODUCTION_DATABASE_URL", "").strip()
    if not raw_url:
        try:
            raw_url = getpass.getpass("Enter Production Database Connection URI (hidden, no echo): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[ABORTED] Backup cancelled by user.")
            sys.exit(1)

    if not raw_url:
        print("[ERROR] Production database URI is required to perform backup.")
        sys.exit(1)

    # 3. Validate non-secret target metadata
    try:
        parsed = urllib.parse.urlparse(raw_url)
    except Exception as e:
        print(f"[ERROR] Invalid URI format: {e}")
        sys.exit(1)

    username = parsed.username or ""
    hostname = parsed.hostname or ""
    path_db = (parsed.path or "").lstrip("/")

    # Verification checks
    is_ref_valid = EXPECTED_PROJECT_REF in username or EXPECTED_PROJECT_REF in hostname
    is_host_valid = EXPECTED_HOST_SUBSTRING in hostname or "supabase.com" in hostname
    is_db_valid = path_db == EXPECTED_DB

    print("\n[-] Validating Production Target Metadata (Non-Secret):")
    print(f"    - Host:     {hostname}")
    print(f"    - Port:     {parsed.port or 5432}")
    print(f"    - Database: {path_db}")
    print(f"    - Ref Match: {'PASS' if is_ref_valid else 'FAIL'}")

    if not (is_ref_valid and is_host_valid and is_db_valid):
        print("\n[SAFETY STOP] Target metadata does not match production project 'bszcepdezyzfxwhqkejw'!")
        print("Aborting to prevent backing up an incorrect target.")
        sys.exit(1)

    print("[✓] Target project identity verified successfully.")

    # 4. Prepare backup output directory
    backup_dir = os.path.expanduser("~/careerpilot_backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"prod_pg_backup_{timestamp}.dump"
    backup_path = os.path.join(backup_dir, backup_filename)

    if os.path.exists(backup_path):
        print(f"[ERROR] Destination file already exists: {backup_path}")
        sys.exit(1)

    # 5. Execute pg_dump
    print(f"\n[-] Starting custom-format dump to: {backup_path}")
    dump_cmd = [
        pg_dump_bin,
        raw_url,
        "--format=custom",
        "--no-owner",
        "--no-acl",
        f"--file={backup_path}"
    ]

    try:
        res = subprocess.run(dump_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Redact any password that pg_dump might print in stderr
            err_msg = res.stderr
            if parsed.password and parsed.password in err_msg:
                err_msg = err_msg.replace(parsed.password, "***")
            print(f"\n[ERROR] pg_dump failed with exit code {res.returncode}:")
            print(err_msg.strip())
            if os.path.exists(backup_path):
                os.remove(backup_path)
            sys.exit(res.returncode)
    except Exception as e:
        print(f"\n[ERROR] Failed to execute pg_dump: {e}")
        if os.path.exists(backup_path):
            os.remove(backup_path)
        sys.exit(1)

    # 6. Verify with pg_restore --list
    file_size_bytes = os.path.getsize(backup_path)
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    print(f"[✓] Dump completed successfully: {file_size_mb} MB ({file_size_bytes} bytes)")

    print("[-] Verifying backup archive integrity with pg_restore --list...")
    restore_cmd = [pg_restore_bin, "--list", backup_path]
    res_restore = subprocess.run(restore_cmd, capture_output=True, text=True)

    if res_restore.returncode != 0:
        print("[!] Warning: pg_restore --list returned non-zero code:")
        print(res_restore.stderr.strip())
        sys.exit(1)

    table_data_count = sum(1 for line in res_restore.stdout.splitlines() if "TABLE DATA" in line)
    print(f"[✓] Backup verification PASSED:")
    print(f"    - Archive Path:      {backup_path}")
    print(f"    - Archive Size:      {file_size_mb} MB")
    print(f"    - Table Data Items:  {table_data_count} tables verified")
    print("=" * 70)
    print(" BACKUP COMPLETE AND VERIFIED SAFE")
    print("=" * 70)

if __name__ == "__main__":
    main()
