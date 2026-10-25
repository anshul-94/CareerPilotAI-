"""
CareerPilot AI — Storage Service Abstraction
Provides pluggable storage providers (Local Filesystem vs. Supabase Storage)
for resume documents, guaranteeing isolated server-side credential handling,
resilient failure modes, and zero client-side secret exposure.
"""

import os
import io
import requests
from abc import ABC, abstractmethod
from typing import Optional, Tuple, BinaryIO, Union
from backend.config import Config
from backend.utils.logger import app_logger, error_logger


class BaseStorageService(ABC):
    """Abstract interface defining required storage operations."""

    @abstractmethod
    def upload_file(self, file_data: Union[BinaryIO, bytes], object_key: str,
                    content_type: str = "application/pdf") -> Tuple[bool, str]:
        """
        Upload binary content or a file-like stream to storage under object_key.
        Returns: (success: bool, message: str)
        """
        pass

    @abstractmethod
    def download_file(self, object_key: str) -> Tuple[bool, Optional[bytes], str]:
        """
        Download binary content for object_key.
        Returns: (success: bool, content: Optional[bytes], error_message: str)
        """
        pass

    @abstractmethod
    def generate_signed_url(self, object_key: str, expires_in_seconds: int = 60) -> Tuple[bool, Optional[str], str]:
        """
        Generate a short-lived authenticated URL for the object.
        Returns: (success: bool, url: Optional[str], error_message: str)
        """
        pass

    @abstractmethod
    def delete_file(self, object_key: str) -> Tuple[bool, str]:
        """
        Delete the object identified by object_key.
        Returns: (success: bool, message: str)
        """
        pass

    @abstractmethod
    def file_exists(self, object_key: str) -> bool:
        """
        Check if the object exists in storage without raising exceptions.
        Returns: bool
        """
        pass


class LocalStorageService(BaseStorageService):
    """Default storage provider using the local or persistent container filesystem."""

    def __init__(self, base_folder: Optional[str] = None):
        if base_folder:
            self.base_folder = os.path.abspath(base_folder)
        else:
            folder = getattr(Config, 'UPLOAD_FOLDER', 'static/uploads')
            if not os.path.isabs(folder):
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                folder = os.path.join(project_root, folder)
            self.base_folder = os.path.abspath(folder)
        os.makedirs(self.base_folder, exist_ok=True)

    def _resolve_path(self, object_key: str) -> str:
        """Resolve and validate that object_key stays within base_folder."""
        # Sanitize leading slashes
        clean_key = object_key.lstrip("/\\")
        target_path = os.path.abspath(os.path.join(self.base_folder, clean_key))
        if not target_path.startswith(self.base_folder):
            raise ValueError(f"Path traversal detected for key: {object_key}")
        return target_path

    def upload_file(self, file_data: Union[BinaryIO, bytes], object_key: str,
                    content_type: str = "application/pdf") -> Tuple[bool, str]:
        try:
            target_path = self._resolve_path(object_key)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            if isinstance(file_data, bytes):
                with open(target_path, "wb") as f:
                    f.write(file_data)
            elif hasattr(file_data, "read"):
                # Rewind if seekable
                if hasattr(file_data, "seek"):
                    file_data.seek(0)
                with open(target_path, "wb") as f:
                    f.write(file_data.read())
            else:
                return False, "Unsupported file_data type"

            return True, "File uploaded successfully to local storage"
        except Exception as e:
            error_logger.error(f"[LocalStorage] Upload failed for {object_key}: {e}", exc_info=True)
            return False, f"Local upload failed: {str(e)}"

    def download_file(self, object_key: str) -> Tuple[bool, Optional[bytes], str]:
        try:
            target_path = self._resolve_path(object_key)
            if not os.path.exists(target_path):
                return False, None, "File not found on local disk"

            with open(target_path, "rb") as f:
                content = f.read()
            return True, content, ""
        except Exception as e:
            error_logger.error(f"[LocalStorage] Download failed for {object_key}: {e}", exc_info=True)
            return False, None, f"Local download error: {str(e)}"

    def generate_signed_url(self, object_key: str, expires_in_seconds: int = 60) -> Tuple[bool, Optional[str], str]:
        # Local filesystem storage does not produce remote signed URLs
        return False, None, "Signed URLs are not supported for local storage backend"

    def delete_file(self, object_key: str) -> Tuple[bool, str]:
        try:
            target_path = self._resolve_path(object_key)
            if os.path.exists(target_path):
                os.remove(target_path)
                return True, "Local file deleted successfully"
            return True, "File already absent from local disk"
        except Exception as e:
            error_logger.error(f"[LocalStorage] Delete failed for {object_key}: {e}", exc_info=True)
            return False, f"Local deletion failed: {str(e)}"

    def file_exists(self, object_key: str) -> bool:
        try:
            target_path = self._resolve_path(object_key)
            return os.path.exists(target_path) and os.path.isfile(target_path)
        except Exception:
            return False


class SupabaseStorageService(BaseStorageService):
    """
    Supabase Storage provider communicating with Supabase Storage REST API v1.
    All operations use the private service_role key strictly on the backend.
    """

    def __init__(self,
                 supabase_url: Optional[str] = None,
                 service_role_key: Optional[str] = None,
                 bucket: Optional[str] = None,
                 timeout: Optional[int] = None):
        self.supabase_url = (supabase_url or Config.SUPABASE_URL).rstrip("/")
        self.service_role_key = (service_role_key or Config.SUPABASE_SERVICE_ROLE_KEY).strip()
        self.bucket = (bucket or Config.SUPABASE_RESUME_BUCKET).strip()
        self.timeout = timeout or Config.SUPABASE_TIMEOUT

    def _get_headers(self, content_type: Optional[str] = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def upload_file(self, file_data: Union[BinaryIO, bytes], object_key: str,
                    content_type: str = "application/pdf") -> Tuple[bool, str]:
        if not self.supabase_url or not self.service_role_key:
            return False, "Supabase storage is not configured (missing URL or SERVICE_ROLE_KEY)"

        clean_key = object_key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{clean_key}"
        headers = self._get_headers(content_type)
        headers["x-upsert"] = "true"

        try:
            if isinstance(file_data, bytes):
                body = file_data
            elif hasattr(file_data, "read"):
                if hasattr(file_data, "seek"):
                    file_data.seek(0)
                body = file_data.read()
            else:
                return False, "Unsupported file_data type"

            res = requests.post(url, headers=headers, data=body, timeout=self.timeout)
            if res.status_code in (200, 201):
                return True, "File uploaded successfully to Supabase Storage"
            
            error_msg = f"Supabase upload rejected with status {res.status_code}"
            try:
                err_json = res.json()
                if "message" in err_json:
                    error_msg = f"Supabase error: {err_json['message']}"
            except Exception:
                pass
            error_logger.error(f"[SupabaseStorage] Upload error: {error_msg}")
            return False, error_msg

        except requests.RequestException as e:
            error_logger.error(f"[SupabaseStorage] Network exception during upload: {type(e).__name__}")
            return False, "Storage network failure during upload"

    def download_file(self, object_key: str) -> Tuple[bool, Optional[bytes], str]:
        if not self.supabase_url or not self.service_role_key:
            return False, None, "Supabase storage is not configured"

        clean_key = object_key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket}/{clean_key}"
        headers = self._get_headers()

        try:
            res = requests.get(url, headers=headers, timeout=self.timeout)
            if res.status_code == 200:
                return True, res.content, ""
            elif res.status_code == 404:
                return False, None, "Object not found in Supabase Storage"
            else:
                return False, None, f"Supabase download failed with status {res.status_code}"
        except requests.RequestException as e:
            error_logger.error(f"[SupabaseStorage] Network exception during download: {type(e).__name__}")
            return False, None, "Storage network failure during download"

    def generate_signed_url(self, object_key: str, expires_in_seconds: int = 60) -> Tuple[bool, Optional[str], str]:
        if not self.supabase_url or not self.service_role_key:
            return False, None, "Supabase storage is not configured"

        clean_key = object_key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{clean_key}"
        headers = self._get_headers("application/json")
        payload = {"expiresIn": expires_in_seconds}

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                signed_path = data.get("signedURL")
                if signed_path:
                    # Supabase returns relative or absolute path
                    if signed_path.startswith("http"):
                        full_url = signed_path
                    else:
                        full_url = f"{self.supabase_url}/storage/v1{signed_path}"
                    return True, full_url, ""
                return False, None, "Signed URL missing in Supabase response"
            return False, None, f"Supabase sign failed with status {res.status_code}"
        except requests.RequestException as e:
            error_logger.error(f"[SupabaseStorage] Network exception during signing: {type(e).__name__}")
            return False, None, "Storage network failure during signing"

    def delete_file(self, object_key: str) -> Tuple[bool, str]:
        if not self.supabase_url or not self.service_role_key:
            return False, "Supabase storage is not configured"

        clean_key = object_key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}"
        headers = self._get_headers("application/json")
        payload = {"prefixes": [clean_key]}

        try:
            res = requests.delete(url, headers=headers, json=payload, timeout=self.timeout)
            if res.status_code in (200, 204):
                return True, "Object deleted successfully from Supabase Storage"
            
            error_msg = f"Supabase delete failed with status {res.status_code}"
            error_logger.error(f"[SupabaseStorage] Delete error: {error_msg}")
            return False, error_msg
        except requests.RequestException as e:
            error_logger.error(f"[SupabaseStorage] Network exception during delete: {type(e).__name__}")
            return False, "Storage network failure during delete"

    def file_exists(self, object_key: str) -> bool:
        if not self.supabase_url or not self.service_role_key:
            return False

        clean_key = object_key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/info/authenticated/{self.bucket}/{clean_key}"
        headers = self._get_headers()

        try:
            res = requests.get(url, headers=headers, timeout=self.timeout)
            return res.status_code == 200
        except Exception:
            return False


class StorageFactory:
    """Factory to retrieve the appropriate storage provider based on environment configuration."""

    @staticmethod
    def get_storage(backend: Optional[str] = None) -> BaseStorageService:
        target_backend = (backend or Config.RESUME_STORAGE_BACKEND).lower().strip()

        if target_backend == "supabase":
            # Strictly return SupabaseStorageService. If credentials are missing,
            # it fails operations with an explicit error rather than silently writing to ephemeral local disk.
            return SupabaseStorageService()

        if target_backend == "local":
            return LocalStorageService()

        raise ValueError(f"Unsupported storage backend: '{target_backend}'. Expected 'local' or 'supabase'.")
