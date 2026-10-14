"""
CareerPilot AI — Resume Service
Handles PDF upload, text extraction, storage, and resume building.
"""

import os
import json
from typing import Tuple, Optional
from backend.models.resume import ResumeModel
from backend.models.project import ResumeAnalysisModel
from backend.services.ai_service import AIService
from backend.ai.response_parser import parse_json_response
from backend.prompts.resume_prompt import (
    get_resume_analysis_prompt,
    get_skills_extraction_prompt
)
from backend.utils.helpers import (
    secure_filename, allowed_file, extract_skills_from_text, safe_json_loads
)
from backend.utils.logger import app_logger, error_logger, security_logger


# Import here to avoid circular imports at module level
def _sync_career_profile(user_id: int, raw_text: str) -> None:
    """Background-safe wrapper: sync resume text into the career profile."""
    try:
        from backend.services.career_profile_service import CareerProfileService
        CareerProfileService.sync_from_resume(user_id, raw_text)
        print(f"[✓] Career profile synced for user {user_id}")
    except Exception as _e:
        print(f"[WARN] Career profile sync failed: {_e}")

def parse_resume_analysis(raw_text: str) -> dict:
    """Helper to parse resume analysis specifically"""
    return parse_json_response(raw_text)


class ResumeService:
    """Business logic for resume operations."""

    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "static", "uploads"
    )

    @staticmethod
    def upload_resume(user_id: int, file) -> Tuple[bool, str, Optional[int]]:
        """
        Upload and process a resume PDF.
        
        Args:
            user_id: ID of the user uploading
            file: FileStorage object from Flask request
            
        Returns:
            Tuple of (success, message, resume_id)
        """
        if not file or not file.filename:
            return False, "No file selected", None
        
        if not allowed_file(file.filename):
            return False, "Only PDF files are allowed", None
        
        # Ensure upload directory exists
        os.makedirs(ResumeService.UPLOAD_FOLDER, exist_ok=True)
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        filepath = os.path.join(ResumeService.UPLOAD_FOLDER, filename)
        
        try:
            # Save file
            file.save(filepath)
            file_size = os.path.getsize(filepath)
            
            # Check file size (10MB max)
            if file_size > 10 * 1024 * 1024:
                os.remove(filepath)
                return False, "File size must be less than 10MB", None
            
            # Extract text from PDF
            raw_text = ResumeService.extract_text_from_pdf(filepath)
            
            if not raw_text or len(raw_text.strip()) < 50:
                # Keep the file but warn about extraction
                raw_text = raw_text or "Text extraction failed. Please try a different PDF format."
            
            # Save to database
            resume_id = ResumeModel.create(
                user_id=user_id,
                filename=filename,
                original_name=file.filename,
                raw_text=raw_text,
                file_size=file_size
            )
            
            # Set as primary if it's the first resume
            if ResumeModel.count_by_user(user_id) == 1:
                ResumeModel.set_primary(resume_id, user_id)

            # ── Smart Profile Sync ─────────────────────────────────
            # Automatically extract and populate Career DNA profile.
            # Runs in the same request (fast due to deterministic fallback).
            _sync_career_profile(user_id, raw_text)
            # ─────────────────────────────────────────────────────

            return True, "Resume uploaded and profile synced!", resume_id
            
        except Exception as e:
            # Cleanup on failure
            if os.path.exists(filepath):
                os.remove(filepath)
            return False, f"Upload failed: {str(e)}", None

    @staticmethod
    def extract_text_from_pdf(filepath: str) -> str:
        """Extract text content from a PDF file."""
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(filepath)
            text_parts = []
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n".join(text_parts)
            
        except Exception as e:
            print(f"[ERROR] PDF extraction failed: {str(e)}")
            return ""

    @staticmethod
    def analyze_resume(resume_id: int, user_id: int,
                       target_role: str = "") -> Tuple[bool, str, Optional[dict]]:
        """
        Run AI analysis on a resume.
        
        Args:
            resume_id: ID of the resume to analyze
            user_id: ID of the requesting user (for ownership verification)
            target_role: Optional target job role for tailored ATS evaluation
            
        Returns:
            Tuple of (success, message, analysis_dict)
        """
        # 1. Target Role Normalization
        # Ensures "AI/ML Engineer", "AI/ML Engineer ", " AI/ML Engineer", "AI/ML   Engineer"
        # are treated identically; whitespace-only or None becomes "".
        target_role = " ".join(str(target_role or "").split()).strip()

        # 2. Resume Lookup
        resume = ResumeModel.get_by_id(resume_id)
        if not resume:
            app_logger.warning(
                f"[ResumeService] [ResumeLookupStage] Resume not found: resume_id={resume_id}, user_id={user_id}"
            )
            return False, "Resume not found", None

        # 3. Ownership Verification
        if resume.get('user_id') != user_id:
            security_logger.warning(
                f"[ResumeService] [OwnershipStage] Unauthorized resume access attempt: "
                f"resume_id={resume_id}, requesting_user_id={user_id}, owner_id={resume.get('user_id')}"
            )
            return False, "You do not have permission to access this resume", None

        # 4. Text Extraction & Validation
        raw_text = (resume.get('raw_text') or "").strip()
        if not raw_text or len(raw_text) < 50 or raw_text.startswith("Text extraction failed"):
            filename = resume.get('filename')
            if filename:
                filepath = os.path.join(ResumeService.UPLOAD_FOLDER, filename)
                if os.path.exists(filepath):
                    app_logger.info(
                        f"[ResumeService] [TextRetrievalStage] Re-attempting PDF text extraction for resume_id={resume_id}"
                    )
                    extracted = ResumeService.extract_text_from_pdf(filepath)
                    if extracted and len(extracted.strip()) >= 50:
                        raw_text = extracted.strip()
                        ResumeModel.update_raw_text(resume_id, raw_text)

        if not raw_text or len(raw_text) < 50 or raw_text.startswith("Text extraction failed"):
            app_logger.warning(
                f"[ResumeService] [ValidationStage] Resume text too short or unextracted: "
                f"resume_id={resume_id}, text_len={len(raw_text)}"
            )
            return False, "Resume text is too short or could not be extracted. Please upload a clear text PDF.", None

        # 5. Prompt Construction
        try:
            messages = get_resume_analysis_prompt(raw_text, target_role)
        except Exception as e:
            error_logger.error(
                f"[ResumeService] [PromptStage] Failed to build prompt: {type(e).__name__} - {str(e)}",
                exc_info=True
            )
            return False, "Failed to build resume analysis prompt", None

        # 6. AI Provider Invocation
        try:
            response = AIService.chat_completion(messages, temperature=0.3, json_mode=True)
        except Exception as e:
            error_logger.error(
                f"[ResumeService] [AIInvocationStage] Exception calling AI service for resume_id={resume_id}: "
                f"{type(e).__name__} - {str(e)}",
                exc_info=True
            )
            return False, "AI service encountered an unexpected error. Please try again later.", None

        if not response or not response.get("success"):
            error_detail = response.get("error", "AI provider failure") if response else "Empty response from AI service"
            error_logger.error(
                f"[ResumeService] [AIProviderStage] AI provider failed for resume_id={resume_id}: {error_detail}"
            )
            
            err_lower = str(error_detail).lower()
            if "rate limit" in err_lower or "429" in err_lower:
                user_msg = "AI service rate limit reached. Please wait a moment and try again."
            elif "timeout" in err_lower or "timed out" in err_lower:
                user_msg = "AI analysis request timed out. Please try again."
            elif "auth" in err_lower or "api key" in err_lower or "401" in err_lower:
                user_msg = "AI service authentication error. Please contact administrator."
            elif "offline" in err_lower or "connection" in err_lower or "unreachable" in err_lower:
                user_msg = "AI service is offline or unreachable. Please try again shortly."
            else:
                user_msg = "AI analysis failed. Please try again."
            return False, user_msg, None

        # 7. Response Parsing & Validation
        content = response.get("content", "")
        if not content or not isinstance(content, str) or not content.strip():
            error_logger.error(
                f"[ResumeService] [ResponseParsingStage] AI provider returned empty content for resume_id={resume_id}"
            )
            return False, "AI returned an empty analysis. Please try again.", None

        analysis = parse_json_response(content, fallback_structure={
            "ats_score": 0, "strong_skills": [], "weak_skills": [], 
            "missing_keywords": [], "grammar_issues": [], 
            "experience_analysis": "", "project_analysis": "", 
            "summary": "Analysis unavailable", "action_plan": []
        })

        if (
            analysis.get("summary") == "Analysis unavailable"
            and analysis.get("ats_score") == 0
            and not analysis.get("strong_skills")
        ):
            error_logger.error(
                f"[ResumeService] [ResponseParsingStage] Response JSON parsing failed for resume_id={resume_id}"
            )
            return False, "Unable to parse AI analysis results. Please try again.", None

        # 8. Database Persistence
        try:
            ResumeAnalysisModel.create(
                resume_id=resume_id,
                user_id=user_id,
                ats_score=analysis.get("ats_score", 0),
                strong_skills=analysis.get("strong_skills", []),
                weak_skills=analysis.get("weak_skills", []),
                missing_keywords=analysis.get("missing_keywords", []),
                grammar_issues=analysis.get("grammar_issues", []),
                experience_analysis=analysis.get("experience_analysis", ""),
                project_analysis=analysis.get("project_analysis", ""),
                summary=analysis.get("summary", ""),
                action_plan=analysis.get("action_plan", []),
                full_analysis=analysis
            )
            app_logger.info(
                f"[ResumeService] [DatabaseStage] Analysis saved to DB for resume_id={resume_id}, user_id={user_id}"
            )
        except Exception as e:
            error_logger.error(
                f"[ResumeService] [DatabaseStage] Failed to persist analysis for resume_id={resume_id}: "
                f"{type(e).__name__} - {str(e)}",
                exc_info=True
            )

        analysis["mock"] = response.get("mock", False)
        analysis["target_role"] = target_role
        return True, "Analysis complete!", analysis

    @staticmethod
    def extract_skills(resume_id: int) -> list[str]:
        """Extract skills from a resume using AI + pattern matching."""
        resume = ResumeModel.get_by_id(resume_id)
        if not resume or not resume.get('raw_text'):
            return []
        
        # Pattern-based extraction (fast, always works)
        pattern_skills = extract_skills_from_text(resume['raw_text'])
        
        # AI-based extraction (more comprehensive)
        try:
            messages = get_skills_extraction_prompt(resume['raw_text'])
            response = AIService.chat_completion(messages, temperature=0.2, json_mode=True)
            if response.get("success"):
                data = parse_json_response(response["content"], fallback_structure={"technical_skills": [], "tools": []})
                ai_skills = data.get("technical_skills", []) + data.get("tools", [])
                # Merge with pattern skills
                all_skills = list(set(pattern_skills + ai_skills))
                return all_skills
        except Exception:
            pass
        
        return pattern_skills

    @staticmethod
    def get_user_resumes(user_id: int) -> list[dict]:
        """Get all resumes for a user with analysis status."""
        resumes = ResumeModel.get_by_user(user_id)
        for resume in resumes:
            analysis = ResumeAnalysisModel.get_by_resume(resume['id'])
            resume['has_analysis'] = analysis is not None
            resume['ats_score'] = analysis.get('ats_score', 0) if analysis else None
        return resumes

    @staticmethod
    def get_latest_analysis(user_id: int) -> Optional[dict]:
        """Get the latest resume analysis for a user."""
        analysis = ResumeAnalysisModel.get_latest(user_id)
        if analysis:
            # Parse JSON strings back to lists/dicts
            for field in ['strong_skills', 'weak_skills', 'missing_keywords',
                         'grammar_issues', 'action_plan', 'full_analysis']:
                if isinstance(analysis.get(field), str):
                    analysis[field] = safe_json_loads(analysis[field], [])
        return analysis
