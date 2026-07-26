"""
CareerPilot AI — Autonomous Agent
Runs background tasks (like job searching and resume rebuilding) in a non-blocking ThreadPoolExecutor.
Uses file locks to prevent duplicate heavy tasks.
"""

import os
import time
import logging
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from flask import current_app

from backend.services.job_service import JobService
from backend.services.resume_intelligence_service import ResumeIntelligenceService
from backend.models.job import JobModel
from backend.models.resume_version import ResumeVersionModel

logger = logging.getLogger("careerpilot.autonomous")

# Global thread pool for background tasks
_executor = ThreadPoolExecutor(max_workers=3)

# Directory to store simple file locks
LOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "locks")
os.makedirs(LOCK_DIR, exist_ok=True)


class AutonomousAgent:
    """Manages autonomous AI background operations."""

    @staticmethod
    def _acquire_lock(lock_name: str, timeout: int = 300) -> bool:
        """Attempt to acquire a file lock. Returns True if successful."""
        lock_path = os.path.join(LOCK_DIR, f"{lock_name}.lock")
        if os.path.exists(lock_path):
            # Check if lock is stale
            if time.time() - os.path.getmtime(lock_path) > timeout:
                try:
                    os.remove(lock_path)
                except OSError:
                    pass
            else:
                return False  # Still locked
        
        try:
            with open(lock_path, 'w') as f:
                f.write(str(time.time()))
            return True
        except IOError:
            return False

    @staticmethod
    def _release_lock(lock_name: str):
        """Release a file lock."""
        lock_path = os.path.join(LOCK_DIR, f"{lock_name}.lock")
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass

    @staticmethod
    def _run_in_background(app, func, *args, **kwargs):
        """Wrapper to push the Flask app context into the background thread."""
        def task():
            with app.app_context():
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[AutonomousAgent] Background task failed: {e}")
        
        _executor.submit(task)

    @classmethod
    def trigger_job_search(cls, user_id: int, force: bool = False):
        """Trigger an autonomous job search in the background."""
        app = current_app._get_current_object()
        cls._run_in_background(app, cls._do_job_search, user_id, force)

    @classmethod
    def _do_job_search(cls, user_id: int, force: bool):
        lock_name = f"job_search_{user_id}"
        
        # Check if we recently did a job search (within 30 mins)
        if not force:
            latest_jobs = JobModel.get_by_user(user_id, limit=1)
            if latest_jobs:
                last_found = latest_jobs[0].get("created_at")
                if last_found:
                    try:
                        last_time = datetime.fromisoformat(last_found)
                        if datetime.now() - last_time < timedelta(minutes=30):
                            logger.info(f"[AutonomousAgent] Job search skipped (cache fresh) for User {user_id}")
                            return
                    except ValueError:
                        pass
        
        if not cls._acquire_lock(lock_name):
            return
            
        import time
        from backend.utils.logger import scheduler_logger
        start_time = time.time()
        status = "Started"
        
        try:
            # Empty role & location forces JobService to read from DNA
            JobService.search_for_user(user_id, "", "", "")
            status = "Success"
        except Exception as e:
            status = f"Failed ({e})"
        finally:
            cls._release_lock(lock_name)
            duration = int((time.time() - start_time) * 1000)
            log_msg = f"\n========== BACKGROUND JOB ==========\nTask        : AI Job Refresh\nUser ID     : {user_id}\nStarted     : Yes\nDuration    : {duration} ms\nResult      : {status}\n====================================="
            scheduler_logger.info(log_msg)

    @classmethod
    def trigger_resume_generation(cls, user_id: int, target_role: str = "", force: bool = False, is_daily: bool = False):
        """Trigger an autonomous ATS resume generation in the background."""
        app = current_app._get_current_object()
        cls._run_in_background(app, cls._do_resume_generation, user_id, target_role, force, is_daily)

    @classmethod
    def _do_resume_generation(cls, user_id: int, target_role: str, force: bool, is_daily: bool):
        lock_name = f"resume_gen_{user_id}"
        
        # Avoid redundant generation
        if not force:
            latest = ResumeIntelligenceService.get_latest_version(user_id)
            if latest:
                last_created = latest.get("created_at")
                if last_created:
                    try:
                        last_time = datetime.fromisoformat(last_created)
                        if datetime.now() - last_time < timedelta(hours=24):
                            logger.info(f"[AutonomousAgent] Resume generation skipped (fresh) for User {user_id}")
                            return
                    except ValueError:
                        pass
                        
        if not cls._acquire_lock(lock_name, timeout=600):
            return
            
        import time
        from backend.utils.logger import scheduler_logger
        start_time = time.time()
        status = "Started"
        
        try:
            ResumeIntelligenceService.generate_optimized_resume(user_id, target_role, is_daily=is_daily)
            status = "Success"
        except Exception as e:
            status = f"Failed ({e})"
        finally:
            cls._release_lock(lock_name)
            duration = int((time.time() - start_time) * 1000)
            task_name = "Daily Resume Optimization" if is_daily else "AI Resume Build"
            log_msg = f"\n========== BACKGROUND JOB ==========\nTask        : {task_name}\nUser ID     : {user_id}\nStarted     : Yes\nDuration    : {duration} ms\nResult      : {status}\n====================================="
            scheduler_logger.info(log_msg)

    @classmethod
    def on_login(cls, user_id: int):
        """Called immediately after successful login."""
        cls.trigger_job_search(user_id)
        # Check daily resume improvement
        cls.trigger_resume_generation(user_id, is_daily=True)

    @classmethod
    def invalidate_and_regenerate(cls, user_id: int):
        """Called when Profile/DNA or Base Resume is updated."""
        # Force a refresh
        cls.trigger_job_search(user_id, force=True)
        cls.trigger_resume_generation(user_id, force=True)
