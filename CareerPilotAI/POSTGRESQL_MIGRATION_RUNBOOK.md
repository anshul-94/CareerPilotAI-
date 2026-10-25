# CareerPilot AI — PostgreSQL Migration & Operational Runbook

**Document:** Production Migration Runbook  
**Applies To:** CareerPilot AI (Flask + Raw SQL Architecture)  
**Target Database:** PostgreSQL 15+ (Render PostgreSQL / AWS RDS / Local Docker / Supabase / Neon)  
**Status:** Ready for User Review (DO NOT run against live production until explicitly approved)  

---

## 1. Safety Protocols & Core Principles

1. **Untouched SQLite Source:** The SQLite file `database.db` and backup files will NEVER be modified, truncated, or removed during migration.
2. **Explicit Target Selection:** The application only connects to PostgreSQL if the `DATABASE_URL` environment variable is explicitly provided.
3. **No Silent Empty Fallback:** The application will fail fast and report connection errors if `DATABASE_URL` is configured but unreachable. It will never silently fall back to an empty database.
4. **No Plaintext Secrets:** Connection strings, passwords, and tokens are NEVER hardcoded into source code or committed to git.
5. **Reversible Rollout:** Reverting back to SQLite requires solely unsetting or clearing `DATABASE_URL`.

---

## 2. Pre-Migration Preparation & Backup

Before performing any migration work, create a verified snapshot of the active SQLite database:

### Step 2.1 — Create SQLite Timestamped Backup
Run the following shell commands in the project root:
```bash
# 1. Create a timestamped backup copy
BACKUP_NAME="database_backup_$(date +%Y%m%d_%H%M%S).db"
cp database.db "${BACKUP_NAME}"

# 2. Verify backup integrity
python3 -c "
import sqlite3
conn = sqlite3.connect('${BACKUP_NAME}')
c = conn.cursor()
c.execute('PRAGMA integrity_check;')
print('Integrity status:', c.fetchone()[0])
c.execute('SELECT COUNT(*) FROM users;')
print('Verified user count:', c.fetchone()[0])
"
```

### Step 2.2 — Backup Local Uploaded Files (Resume PDFs)
```bash
# Archive all uploaded PDFs to a safe backup directory
tar -czvf "resumes_backup_$(date +%Y%m%d_%H%M%S).tar.gz" static/uploads/
```

---

## 3. Provisioning an Isolated Staging Test Environment

> [!IMPORTANT]
> **STAGING SAFETY MANDATE:** Never run migration tests against production or shared user databases. All pre-cutover verification must execute against a dedicated, isolated test database using a verified snapshot copy of `database.db`.

### Option A: Local Testing with Disposable Docker Container
Run an isolated PostgreSQL 16 container on a non-standard port (e.g. 5433) to avoid conflict with any host services:
```bash
# Start disposable local PostgreSQL 16 container
docker run --name careerpilot-staging-pg \
  -e POSTGRES_USER=staging_user \
  -e POSTGRES_PASSWORD=staging_secret_pass \
  -e POSTGRES_DB=careerpilot_staging \
  -p 5433:5432 -d postgres:16-alpine

# Set test environment variable (NOT production DATABASE_URL)
export TEST_DATABASE_URL="postgresql://staging_user:staging_secret_pass@localhost:5433/careerpilot_staging"
```

### Option B: Cloud Staging Database (Isolated Developer/Staging Project)
1. On Render, Neon, or Supabase, create an isolated database named `careerpilot-staging-test-db`.
2. Ensure the URL contains `staging` or `test` and is never the production database.
3. Export as:
   ```bash
   export TEST_DATABASE_URL="postgresql://<user>:<password>@<host>:5432/careerpilot_staging"
   ```

### Step 3.1 — Automated 10-Point Staging Verification Suite
CareerPilot AI provides an end-to-end automated staging verifier (`scripts/verify_staging_postgresql.py`) that runs against the isolated test instance:
```bash
# Run comprehensive 10-step staging verification suite
python3 scripts/verify_staging_postgresql.py --pg-url "$TEST_DATABASE_URL"
```

This automated suite executes:
1. Target safety check (strictly blocks production URLs).
2. Creates a clean snapshot copy (`temp_staging_source.db`), guaranteeing `database.db` remains untouched.
3. Runs the migration utility into PostgreSQL in strict topological order.
4. Validates row counts across all 27 tables.
5. Verifies primary key alignments and representative record values.
6. Asserts 0 foreign-key orphans across all relationships.
7. Validates auto-increment sequences (verifies empty tables generate ID 1; populated tables generate MAX+1).
8. Exercises application database adapter CRUD, commits, and transaction rollbacks.
9. Validates connection pool release under 35 sequential borrows.
10. Executes real application business logic smoke tests (user registration, chat history, admin metrics).

---

## 4. Executing the Production Data Migration

> [!CAUTION]
> Run this section ONLY after the Staging Verification Suite (Section 3.1) has passed 100% and been approved for production cutover.

The migration utility `scripts/migrate_sqlite_to_postgresql.py` automates the entire migration in strict foreign-key order:

### Step 4.1 — Dry-Run Validation
First, run a dry run to inspect table counts and verify both connections:
```bash
# Test with dry-run flag (strictly 0 writes to destination)
python3 scripts/migrate_sqlite_to_postgresql.py --sqlite-path database.db --pg-url "$DATABASE_URL" --dry-run
```

Expected output:
- Source connection confirmed valid.
- Destination connection confirmed valid.
- Table list with 27 verified tables and matching row counts printed.

### Step 4.2 — Execute Full Migration
Run the live migration command:
```bash
python3 scripts/migrate_sqlite_to_postgresql.py --sqlite-path database.db --pg-url "$DATABASE_URL"
```

What the script performs:
1. Connects to `database.db` in read-only mode (`?mode=ro`).
2. Creates all 27 tables and indexes on PostgreSQL using verified DDL.
3. Transfers all 27 tables in topological dependency order (Root → Parents → Children).
4. Synchronizes all PostgreSQL sequence generators (`pg_get_serial_sequence`) to `MAX(id)`.
5. Compares row counts between SQLite and PostgreSQL for every table.
6. Prints a verification report.

---

## 5. Verification & Validation Checklist

Before switching web service traffic to PostgreSQL, run the automated test suite against the target PostgreSQL database:

```bash
# Run automated database compatibility test suite against PostgreSQL
DATABASE_URL="$DATABASE_URL" python3 -m unittest tests/test_database_compatibility.py
```

### Manual Smoke-Testing Checklist:
- [ ] **Admin Authentication:** Login at `/admin/login` with `adminuser85`.
- [ ] **Admin Dashboard:** Check user growth chart, submissions trend, active users metric at `/admin/dashboard`.
- [ ] **User Authentication:** Login with an existing user (e.g., `anshulp85@gmail.com`).
- [ ] **Resume Intelligence:** View existing resume versions and run an analysis preview.
- [ ] **Chat Coach:** Open an existing conversation session; send a new message and verify it appends correctly.
- [ ] **Coding Platform:** Open problem #1 ("Two Sum"); submit solution code and verify feedback is recorded in `problem_submissions` and `ai_problem_feedback`.
- [ ] **Job Notifications:** Filter notifications by "Saved" / "High Match".

---

## 6. Production Rollout Procedure (Render Deployment)

Once validation succeeds:

1. **Enter Maintenance Window:** (Optional but recommended: 5-minute window).
2. **Set Environment Variable on Render Web Service:**
   - Go to Render Dashboard → CareerPilot Web Service → Environment.
   - Add/Update:
     `DATABASE_URL` = `<Internal PostgreSQL Connection String>`
   - Click **Save Changes**.
3. **Application Re-Deploy:**
   - Render will rebuild and redeploy the container.
   - In Render deployment logs, verify:
     ```
     [✓] career_profiles
     [✓] resume_versions
     [✓] notification_agent
     [✓] chat_sessions
     [✓] problem_solving
     [✓] admin_tables
     Database Ready.
     Server Ready.
     ```
4. **Live Verification:** Run through the smoke-testing checklist on the live domain.

---

## 7. Emergency Rollback Protocol & Data Reconciliation Strategy

> [!WARNING]
> **CRITICAL DATA LOSS WARNING:** Simply unsetting `DATABASE_URL` DOES NOT guarantee zero data loss if the application has already accepted live writes on PostgreSQL! Any user registrations, uploaded resumes, chat sessions, interview recordings, or problem submissions created in PostgreSQL after cutover **will NOT exist in the stale SQLite database**.

### Rollback Decision Matrix

| Scenario | Window | Recommended Strategy | Data Loss Risk |
|---|---|---|---|
| **Scenario 1: Pre-Traffic / Smoke Failure** | 0 – 5 min post-cutover (no live users yet) | **Immediate SQLite Reversion** | **Zero Data Loss** (no live writes occurred) |
| **Scenario 2: Post-Traffic Defect (Recoverable)** | > 5 min post-cutover (live traffic active) | **Fix Forward / PostgreSQL Recovery** | **Zero Data Loss** (PostgreSQL stays source of truth) |
| **Scenario 3: Catastrophic PostgreSQL Failure** | > 5 min post-cutover (live traffic active) | **Maintenance Mode + Reverse Delta Reconciliation** | **Zero Data Loss IF reconciled**; High risk if bypassed |

---

### Procedure 1: Pre-Traffic Revert (Smoke Test Failure)
*Use this ONLY if smoke tests fail immediately after cutover and before DNS or user traffic is routed.*

1. **Revert Environment Variable:**
   - In Render Dashboard → CareerPilot Web Service → Environment:
   - Clear or remove `DATABASE_URL`.
   - Click **Save Changes** (triggers automatic restart).
2. **Verify Restart:**
   - Confirm server logs show: `[DB (SQLite)]` queries executing against `database.db`.
3. **Verify SQLite Integrity:**
   - Confirm all original pre-cutover records remain intact.

---

### Procedure 2: Post-Traffic Incident (Fix Forward — Strongly Preferred)
*When live users have written data to PostgreSQL, PostgreSQL is now the authoritative system of record.*

1. **Keep PostgreSQL as Source of Truth:** Do NOT revert `DATABASE_URL` to SQLite.
2. **Mitigate Live Risk:** If needed, set temporary maintenance mode (`MAINTENANCE_MODE=true`) or disable background agent workers (`JOB_AGENT_ENABLED=false`).
3. **Hotfix Application Code:** Patch and deploy the application fix to Render.
4. **Preserve User Data:** All user accounts, chat sessions, and submissions created post-cutover remain intact in PostgreSQL.

---

### Procedure 3: Post-Traffic Catastrophic Rollback with Reverse Reconciliation
*If PostgreSQL is completely unusable and the service MUST fall back to SQLite after live user writes have occurred:*

1. **Activate Maintenance Window Immediately:**
   ```bash
   # Halt incoming writes to avoid split-brain data Divergence
   # Set MAINTENANCE_MODE=true on Render Web Service
   ```
2. **Extract Post-Cutover Delta from PostgreSQL:**
   ```bash
   # Identify exact cutover timestamp (e.g. CUTOVER_TIMESTAMP='2026-10-24 10:00:00')
   # Export all records inserted or updated after cutover across mutable tables:
   # - users
   # - resumes & resume_analysis
   # - chat_sessions & chat_history
   # - problem_submissions & user_problem_analytics
   # - job_history, interview_history, learning_roadmaps
   ```
3. **Reconcile Delta into SQLite:**
   - Use an audited, dry-run tested delta reconciliation script to replay records into SQLite:
     - Check for ID collisions.
     - Remap or preserve auto-increment primary keys.
     - Insert missing user records and dependent foreign keys.
   - Run `PRAGMA integrity_check;` on SQLite.
4. **Switch Render Service Back to SQLite:**
   - Remove `DATABASE_URL` in Render Dashboard.
   - Save and redeploy.
5. **Post-Rollback Audit:**
   - Verify that all users registered during the PostgreSQL window can log in.
   - Verify all chat sessions and problem submissions are present.

> [!CAUTION]
> Do NOT perform reverse synchronization without executing a complete dry-run on staging first. Reverse delta synchronization carries inherent foreign-key collision risks if sequence offsets differ between engines.

---

## 8. Phase 5 — Resume PDF Storage Migration Plan

### Current Architecture & Identified Risk
- Currently, uploaded PDFs are saved to `static/uploads/<filename>` on the local container filesystem.
- On Render and similar PaaS containers, local files are ephemeral and deleted on container restart or redeploy.
- Although the database stores `filename`, `raw_text`, and parsed JSON, physical PDF files can be lost.

### Decoupled Cloud Storage Architecture
To ensure permanent file persistence:

```
[User Browser]
      │ (Upload PDF)
      ▼
[CareerPilot AI (Flask)]
      │
      ├──> Saves metadata & extracted text to PostgreSQL (resumes table)
      │
      └──> Streams binary PDF to S3-compatible Object Storage
             (AWS S3 / Cloudflare R2 / Google Cloud Storage)
```

### Proposed Cloud Storage Implementation Steps:
1. **Choose S3-Compatible Provider:** Cloudflare R2 (zero egress fees) or AWS S3.
2. **Environment Variables:**
   - `S3_BUCKET_NAME`
   - `S3_ACCESS_KEY_ID`
   - `S3_SECRET_ACCESS_KEY`
   - `S3_ENDPOINT_URL` (for Cloudflare R2 or MinIO)
3. **Storage Utility (`backend/utils/storage.py`):**
   - Provide `upload_file(file_obj, filename)` and `download_file(filename)` and `get_presigned_url(filename)`.
   - Maintain a local fallback for offline development.
4. **Data Migration for Existing PDFs:**
   - A dedicated script `scripts/migrate_files_to_s3.py` will read existing files from `static/uploads/` and upload them to the S3 bucket.
5. **No Immediate Breaking Change:**
   - Keep current `static/uploads/` storage intact until PostgreSQL database migration is complete and stable.
