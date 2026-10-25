"""
CareerPilot AI — Resume Storage & Supabase Integration Tests
Tests:
1. Upload folder path configuration and dynamic volume resolution
2. Authorized PDF download by owner (server-side stream with attachment headers)
3. Authorized PDF download by admin
4. Unauthorized download attempt blocked (ownership barrier)
5. Unauthenticated download redirect
6. Safe handling of missing physical/cloud objects (graceful flash, no 500 error)
7. Non-existent resume ID handling
8. Full upload, storage persistence, and deletion lifecycle
9. Disallowed file extensions and oversized file safeguards
10. Storage deletion failure safeguards (preserves database record if storage delete fails)
11. Supabase Storage upload, signed URL, and download (mocked API responses)
12. Supabase Storage upload failure creates no database record
13. Database insert failure triggers storage object cleanup
14. Storage backend selection toggle and graceful fallback when credentials missing
15. Backward-compatibility for legacy records without resume_storage_metadata rows
"""

import os
import shutil
import unittest
import uuid
import io
from unittest.mock import patch, MagicMock

os.environ["DATABASE_PATH"] = "test_resume_storage.db"

from app import create_app
from backend.config import Config
from backend.database.schema import init_db
from backend.models.user import UserModel
from backend.models.resume import ResumeModel
from backend.models.resume_storage import ResumeStorageModel, migrate_resume_storage_table
from backend.services.resume_service import ResumeService
from backend.services.storage_service import (
    BaseStorageService, LocalStorageService, SupabaseStorageService, StorageFactory
)


class ResumeStorageIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_PATH"] = "test_resume_storage.db"
        Config.DATABASE_PATH = "test_resume_storage.db"
        if os.path.exists(Config.DATABASE_PATH):
            os.remove(Config.DATABASE_PATH)
        init_db(Config.DATABASE_PATH)
        migrate_resume_storage_table()

        # Isolated test upload directory
        cls.test_upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_uploads_tmp")
        os.makedirs(cls.test_upload_dir, exist_ok=True)
        Config.UPLOAD_FOLDER = cls.test_upload_dir
        Config.RESUME_STORAGE_BACKEND = "local"

        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            # Create user 1 (owner)
            cls.u1_email = f"user1_{uuid.uuid4().hex[:6]}@careerpilot.ai"
            UserModel.create("user1", cls.u1_email, "password123", "User One")
            u1 = UserModel.get_by_email(cls.u1_email)
            cls.user1_id = u1["id"]

            # Create user 2 (attacker / unauthorized user)
            cls.u2_email = f"user2_{uuid.uuid4().hex[:6]}@careerpilot.ai"
            UserModel.create("user2", cls.u2_email, "password123", "User Two")
            u2 = UserModel.get_by_email(cls.u2_email)
            cls.user2_id = u2["id"]

            # Create sample PDF on disk for user 1 (legacy local record without metadata)
            cls.sample_filename = "u1_legacy_resume.pdf"
            cls.sample_filepath = os.path.join(cls.test_upload_dir, cls.sample_filename)
            cls.sample_content = b"%PDF-1.4 Mock PDF resume content for automated testing"
            with open(cls.sample_filepath, "wb") as f:
                f.write(cls.sample_content)

            cls.legacy_resume_id = ResumeModel.create(
                user_id=cls.user1_id,
                filename=cls.sample_filename,
                original_name="UserOne_Legacy.pdf",
                raw_text="Sample text content for user one legacy resume",
                file_size=len(cls.sample_content)
            )

            # Create a resume record where the physical file is MISSING on disk
            cls.missing_filename = "missing_lost_resume.pdf"
            cls.missing_resume_id = ResumeModel.create(
                user_id=cls.user1_id,
                filename=cls.missing_filename,
                original_name="LostResume.pdf",
                raw_text="Extracted text that survived container restart",
                file_size=54321
            )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("test_resume_storage.db"):
            os.remove("test_resume_storage.db")
        if os.path.exists(cls.test_upload_dir):
            shutil.rmtree(cls.test_upload_dir, ignore_errors=True)

    def setUp(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        Config.RESUME_STORAGE_BACKEND = "local"

    # ── 1. Local Storage Basic Tests ─────────────────────────────────

    def test_01_upload_folder_configuration(self):
        """Verify LocalStorageService respects Config.UPLOAD_FOLDER."""
        folder = ResumeService.get_upload_folder()
        self.assertEqual(folder, os.path.abspath(self.test_upload_dir))
        self.assertTrue(os.path.isdir(folder))

    def test_02_download_authorized_owner_legacy(self):
        """Owner can download their legacy resume without metadata table entry."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1_id
            sess['logged_in'] = True

        res = self.client.get(f"/resume/download/{self.legacy_resume_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, self.sample_content)
        disposition = res.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disposition)
        self.assertIn("UserOne_Legacy.pdf", disposition)

    def test_03_download_admin_authorized(self):
        """Admin can download any user's resume."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 999
            sess['is_admin'] = True
            sess['logged_in'] = True

        res = self.client.get(f"/resume/download/{self.legacy_resume_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, self.sample_content)

    def test_04_download_unauthorized_other_user_blocked(self):
        """User 2 must be blocked from downloading User 1's resume."""
        with self.client.session_transaction() as sess:
            sess.clear()
            sess['user_id'] = self.user2_id
            sess['is_admin'] = False
            sess['logged_in'] = True

        res = self.client.get(f"/resume/download/{self.legacy_resume_id}")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/resume/upload", res.headers.get("Location", ""))

    def test_05_download_unauthenticated_redirect(self):
        """Unauthenticated request redirects to login."""
        res = self.client.get(f"/resume/download/{self.legacy_resume_id}")
        self.assertEqual(res.status_code, 302)

    def test_06_download_missing_file_handled_safely(self):
        """Missing physical file redirects safely without 500 error."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1_id
            sess['logged_in'] = True

        res = self.client.get(f"/resume/download/{self.missing_resume_id}")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/resume/upload", res.headers.get("Location", ""))

    def test_07_download_nonexistent_resume_id(self):
        """Requesting non-existent resume ID redirects safely."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1_id
            sess['logged_in'] = True

        res = self.client.get("/resume/download/999999")
        self.assertEqual(res.status_code, 302)

    # ── 2. Local Storage Upload, Delete, and Validation Lifecycle ───

    def test_08_local_upload_and_delete_flow(self):
        """Full upload, metadata persistence, download, and delete flow using storage abstraction."""
        from werkzeug.datastructures import FileStorage

        dummy_pdf_bytes = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000115 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
        )
        file_obj = FileStorage(
            stream=io.BytesIO(dummy_pdf_bytes),
            filename="developer_resume.pdf",
            content_type="application/pdf"
        )

        success, msg, new_id = ResumeService.upload_resume(self.user1_id, file_obj)
        self.assertTrue(success, f"Upload failed: {msg}")
        self.assertIsNotNone(new_id)

        # Verify DB entry
        rec = ResumeModel.get_by_id(new_id)
        self.assertIsNotNone(rec)

        # Verify metadata entry
        meta = ResumeStorageModel.get_by_resume_id(new_id)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["backend"], "local")

        # Verify physical file was written in test upload dir
        storage = StorageFactory.get_storage("local")
        self.assertTrue(storage.file_exists(meta["object_key"]))

        # Delete resume via client
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1_id
            sess['logged_in'] = True

        del_res = self.client.post(f"/resume/delete/{new_id}")
        self.assertEqual(del_res.status_code, 302)

        # Verify DB entry and metadata removed
        self.assertIsNone(ResumeModel.get_by_id(new_id))
        self.assertIsNone(ResumeStorageModel.get_by_resume_id(new_id))

        # Verify file is deleted
        self.assertFalse(storage.file_exists(meta["object_key"]))

    def test_09_upload_disallowed_extension(self):
        """Non-PDF files must be rejected before saving."""
        from werkzeug.datastructures import FileStorage

        file_obj = FileStorage(
            stream=io.BytesIO(b"malicious script content"),
            filename="exploit.sh",
            content_type="text/x-shellscript"
        )
        success, msg, res_id = ResumeService.upload_resume(self.user1_id, file_obj)
        self.assertFalse(success)
        self.assertIn("PDF", msg)
        self.assertIsNone(res_id)

    def test_10_upload_oversized_file_rejected(self):
        """Files exceeding 10MB must be rejected safely."""
        from werkzeug.datastructures import FileStorage

        oversized_bytes = b"%PDF-1.4 " + (b"0" * (10 * 1024 * 1024 + 100))
        file_obj = FileStorage(
            stream=io.BytesIO(oversized_bytes),
            filename="huge_resume.pdf",
            content_type="application/pdf"
        )
        success, msg, res_id = ResumeService.upload_resume(self.user1_id, file_obj)
        self.assertFalse(success)
        self.assertIn("10MB", msg)
        self.assertIsNone(res_id)

    # ── 3. Failure Handling Safeguards ──────────────────────────────

    def test_11_storage_deletion_failure_preserves_database_record(self):
        """If storage deletion fails, do not silently delete database record."""
        # Create a resume entry
        resume_id = ResumeModel.create(
            user_id=self.user1_id,
            filename="undeletable.pdf",
            original_name="undeletable.pdf",
            raw_text="Undeletable test content",
            file_size=100
        )
        ResumeStorageModel.create(
            resume_id=resume_id,
            backend="local",
            bucket_name="",
            object_key="undeletable.pdf",
            file_size=100
        )

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1_id
            sess['logged_in'] = True

        # Mock storage.delete_file to fail
        with patch.object(LocalStorageService, "delete_file", return_value=(False, "Permission denied on disk")):
            res = self.client.post(f"/resume/delete/{resume_id}")
            self.assertEqual(res.status_code, 302)

            # Database record MUST still exist
            self.assertIsNotNone(ResumeModel.get_by_id(resume_id))

        # Clean up manually
        ResumeModel.delete(resume_id)
        ResumeStorageModel.delete_by_resume_id(resume_id)

    def test_12_database_failure_cleans_up_uploaded_storage_object(self):
        """If database insertion fails after storage upload, newly created object is cleaned up."""
        from werkzeug.datastructures import FileStorage

        dummy_bytes = b"%PDF-1.4 Valid dummy PDF for cleanup test"
        file_obj = FileStorage(
            stream=io.BytesIO(dummy_bytes),
            filename="cleanup_test.pdf",
            content_type="application/pdf"
        )

        with patch.object(ResumeModel, "create", side_effect=RuntimeError("Simulated DB connection failure")):
            with patch.object(LocalStorageService, "delete_file", return_value=(True, "Deleted")) as spy_delete:
                success, msg, res_id = ResumeService.upload_resume(self.user1_id, file_obj)
                self.assertFalse(success)
                self.assertIn("rolled back", msg.lower())
                self.assertIsNone(res_id)
                self.assertTrue(spy_delete.called, "storage.delete_file was not called to clean up orphan!")

    # ── 4. Supabase Storage Provider Mocked Tests ───────────────────

    @patch("backend.services.storage_service.requests.post")
    @patch("backend.services.storage_service.requests.get")
    def test_13_supabase_upload_and_download_flow_mocked(self, mock_get, mock_post):
        """Mocked Supabase Storage upload, metadata recording, and authenticated download."""
        from werkzeug.datastructures import FileStorage

        Config.RESUME_STORAGE_BACKEND = "supabase"
        Config.SUPABASE_URL = "https://mockproject.supabase.co"
        Config.SUPABASE_SERVICE_ROLE_KEY = "mock_secret_role_key"
        Config.SUPABASE_RESUME_BUCKET = "careerpilot-resumes"

        # Mock Supabase upload response (200 OK)
        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 200
        mock_upload_resp.json.return_value = {"Key": "careerpilot-resumes/mock_obj.pdf"}
        mock_post.return_value = mock_upload_resp

        # Upload
        dummy_bytes = b"%PDF-1.4 Mock Supabase PDF content"
        file_obj = FileStorage(
            stream=io.BytesIO(dummy_bytes),
            filename="supabase_resume.pdf",
            content_type="application/pdf"
        )

        success, msg, res_id = ResumeService.upload_resume(self.user1_id, file_obj)
        self.assertTrue(success, f"Upload failed: {msg}")
        self.assertIsNotNone(res_id)

        # Verify metadata
        meta = ResumeStorageModel.get_by_resume_id(res_id)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["backend"], "supabase")
        self.assertEqual(meta["bucket_name"], "careerpilot-resumes")
        self.assertTrue(meta["object_key"].startswith(f"{self.user1_id}/"))

        # Mock Supabase download response
        mock_download_resp = MagicMock()
        mock_download_resp.status_code = 200
        mock_download_resp.content = dummy_bytes
        mock_get.return_value = mock_download_resp

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1_id
            sess['logged_in'] = True

        res = self.client.get(f"/resume/download/{res_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, dummy_bytes)

        # Clean up
        ResumeModel.delete(res_id)
        ResumeStorageModel.delete_by_resume_id(res_id)

    @patch("backend.services.storage_service.requests.post")
    def test_14_supabase_upload_failure_creates_no_database_record(self, mock_post):
        """When Supabase returns error (e.g., 500 or 403), no DB record is created."""
        from werkzeug.datastructures import FileStorage

        Config.RESUME_STORAGE_BACKEND = "supabase"
        Config.SUPABASE_URL = "https://mockproject.supabase.co"
        Config.SUPABASE_SERVICE_ROLE_KEY = "mock_secret_role_key"

        mock_fail_resp = MagicMock()
        mock_fail_resp.status_code = 500
        mock_fail_resp.json.return_value = {"message": "Internal storage error"}
        mock_post.return_value = mock_fail_resp

        initial_count = ResumeModel.count_by_user(self.user1_id)

        file_obj = FileStorage(
            stream=io.BytesIO(b"%PDF-1.4 dummy"),
            filename="fail_upload.pdf",
            content_type="application/pdf"
        )
        success, msg, res_id = ResumeService.upload_resume(self.user1_id, file_obj)
        self.assertFalse(success)
        self.assertIsNone(res_id)
        self.assertEqual(ResumeModel.count_by_user(self.user1_id), initial_count)

    def test_15_backend_selection_and_fallback(self):
        """StorageFactory fails safely when credentials are missing, without silent local write."""
        from werkzeug.datastructures import FileStorage

        Config.RESUME_STORAGE_BACKEND = "supabase"
        Config.SUPABASE_URL = ""
        Config.SUPABASE_SERVICE_ROLE_KEY = ""

        # Factory returns SupabaseStorageService
        storage = StorageFactory.get_storage()
        self.assertIsInstance(storage, SupabaseStorageService)

        # Upload attempt must fail safely with explicit error
        file_obj = FileStorage(
            stream=io.BytesIO(b"%PDF-1.4 dummy"),
            filename="unconfigured_test.pdf",
            content_type="application/pdf"
        )
        initial_count = ResumeModel.count_by_user(self.user1_id)
        success, msg, res_id = ResumeService.upload_resume(self.user1_id, file_obj)
        self.assertFalse(success)
        self.assertIn("not configured", msg.lower())
        self.assertIsNone(res_id)
        self.assertEqual(ResumeModel.count_by_user(self.user1_id), initial_count)

        # Local storage returns LocalStorageService
        Config.RESUME_STORAGE_BACKEND = "local"
        self.assertIsInstance(StorageFactory.get_storage(), LocalStorageService)

        # Unknown storage backend raises ValueError
        with self.assertRaises(ValueError):
            StorageFactory.get_storage("unsupported_backend")


if __name__ == "__main__":
    unittest.main()
