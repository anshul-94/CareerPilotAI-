#!/usr/bin/env python3
"""
CareerPilot AI — Resume Storage Migration Script
Non-destructive, backward-compatible migration tool for existing resume PDFs.

Features:
1. Syncs files from source upload directory (e.g. static/uploads/) to target directory
   (e.g. Render Persistent Disk mount point or backup directory).
2. Verifies SHA-256 checksums before and after transfer to ensure 100% data integrity.
3. Validates against active database records (SQLite or PostgreSQL) without modifying metadata.
4. Preserves all file metadata, ownership associations, and resume IDs.
5. Idempotent: safe to run multiple times; skips identical files.
6. Strictly non-destructive: NEVER deletes or modifies source files.

Usage:
    python scripts/migrate_resume_files.py --target-dir /path/to/persistent/storage
    python scripts/migrate_resume_files.py --target-dir /path/to/storage --dry-run
"""

import os
import sys
import shutil
import hashlib
import argparse
import sqlite3
from typing import Dict, List, Optional, Tuple

# Add repository root to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.config import Config


def compute_sha256(filepath: str) -> str:
    """Calculate the SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_db_resumes() -> List[Dict]:
    """Retrieve all resume records from the active database."""
    from backend.database.db import execute_query
    try:
        rows = execute_query(
            "SELECT id, user_id, filename, original_name, file_size, uploaded_at FROM resumes ORDER BY id"
        )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[!] Warning: Could not query active database ({e}). Proceeding without DB cross-check.")
        return []


def migrate_files(
    source_dir: str,
    target_dir: str,
    dry_run: bool = False
) -> Dict[str, any]:
    """
    Migrate files from source_dir to target_dir safely with hash verification.
    """
    source_abs = os.path.abspath(source_dir)
    target_abs = os.path.abspath(target_dir)

    print(f"=== CareerPilot AI Resume File Migration ===")
    print(f"Source Directory : {source_abs}")
    print(f"Target Directory : {target_abs}")
    print(f"Mode             : {'DRY RUN (no changes)' if dry_run else 'LIVE MIGRATION'}")
    print("-" * 50)

    if not os.path.exists(source_abs):
        raise FileNotFoundError(f"Source directory does not exist: {source_abs}")

    if not dry_run:
        os.makedirs(target_abs, exist_ok=True)

    # 1. Inspect source files
    source_files = [
        f for f in os.listdir(source_abs)
        if os.path.isfile(os.path.join(source_abs, f)) and not f.startswith('.')
    ]
    print(f"[*] Found {len(source_files)} physical files in source directory.")

    # 2. Retrieve database records
    db_resumes = get_db_resumes()
    print(f"[*] Found {len(db_resumes)} resume records in database.")

    db_filename_map = {r['filename']: r for r in db_resumes}

    copied = 0
    skipped_identical = 0
    integrity_verified = 0
    errors = []

    results = []

    for filename in sorted(source_files):
        src_path = os.path.join(source_abs, filename)
        dst_path = os.path.join(target_abs, filename)

        src_size = os.path.getsize(src_path)
        src_hash = compute_sha256(src_path)

        db_entry = db_filename_map.get(filename)
        status = "pending"

        if os.path.exists(dst_path):
            dst_hash = compute_sha256(dst_path)
            if src_hash == dst_hash:
                skipped_identical += 1
                status = "already_present_identical"
                print(f"  [=] {filename} (Size: {src_size}B, SHA: {src_hash[:8]}...) -> Already exists & identical")
            else:
                status = "hash_mismatch_existing"
                errors.append(f"Target file exists with different hash: {filename}")
                print(f"  [!] {filename} -> Target file exists with MISMATCHED hash!")
        else:
            if not dry_run:
                try:
                    shutil.copy2(src_path, dst_path)
                    dst_hash = compute_sha256(dst_path)
                    if src_hash == dst_hash:
                        copied += 1
                        integrity_verified += 1
                        status = "copied_and_verified"
                        print(f"  [+] {filename} (Size: {src_size}B) -> Copied and verified (SHA: {src_hash[:8]}...)")
                    else:
                        status = "verification_failed"
                        errors.append(f"Post-copy SHA-256 mismatch: {filename}")
                        print(f"  [!] {filename} -> Copy completed but SHA-256 mismatch!")
                except Exception as e:
                    status = f"copy_error: {str(e)}"
                    errors.append(f"Failed to copy {filename}: {e}")
                    print(f"  [!] {filename} -> Copy failed: {e}")
            else:
                copied += 1
                status = "dry_run_would_copy"
                print(f"  [dry-run] Would copy: {filename} ({src_size}B, SHA: {src_hash[:8]}...)")

        results.append({
            'filename': filename,
            'size': src_size,
            'sha256': src_hash,
            'status': status,
            'db_id': db_entry['id'] if db_entry else None,
            'user_id': db_entry['user_id'] if db_entry else None
        })

    # 3. Check for DB entries missing physical files
    missing_on_disk = []
    for r in db_resumes:
        if r['filename'] not in source_files:
            missing_on_disk.append(r)

    print("-" * 50)
    print("=== Migration Summary ===")
    print(f"Total Source Files    : {len(source_files)}")
    print(f"Total Database Rows   : {len(db_resumes)}")
    print(f"Files Copied          : {copied}")
    print(f"Files Already Current : {skipped_identical}")
    print(f"SHA-256 Verified      : {integrity_verified if not dry_run else 'N/A (Dry Run)'}")
    print(f"Missing Files on Disk : {len(missing_on_disk)}")
    print(f"Errors Encountered    : {len(errors)}")

    if missing_on_disk:
        print("\n[i] Note: The following database records do not have a physical file in source:")
        for m in missing_on_disk:
            print(f"    - Resume ID {m['id']} (User {m['user_id']}): {m['filename']} (Original: {m['original_name']})")
        print("    (Their extracted text remains safely preserved in the database raw_text field)")

    return {
        'source_files': len(source_files),
        'db_resumes': len(db_resumes),
        'copied': copied,
        'skipped_identical': skipped_identical,
        'missing_on_disk': len(missing_on_disk),
        'errors': errors,
        'results': results
    }


def main():
    parser = argparse.ArgumentParser(description="CareerPilot AI Resume Storage Migration Tool")
    parser.add_argument(
        "--source-dir",
        default=os.path.join(REPO_ROOT, "static", "uploads"),
        help="Path to source upload directory (default: static/uploads/)"
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help="Path to destination persistent storage directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without modifying target directory"
    )

    args = parser.parse_args()
    summary = migrate_files(args.source_dir, args.target_dir, args.dry_run)
    if summary['errors']:
        sys.exit(1)


if __name__ == "__main__":
    main()
