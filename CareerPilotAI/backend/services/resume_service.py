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
        
        Returns:
            Tuple of (success, message, analysis_dict)
        """
        resume = ResumeModel.get_by_id(resume_id)
        if not resume:
            return False, "Resume not found", None
        
        if not resume.get('raw_text') or len(resume['raw_text'].strip()) < 50:
            return False, "Resume text is too short for analysis", None
        
        # Build prompt and call AI
        messages = get_resume_analysis_prompt(resume['raw_text'], target_role)
        response = AIService.chat_completion(messages, temperature=0.3, json_mode=True)
        
        if not response.get("success"):
            return False, "AI analysis failed. Please try again.", None
        
        # Parse the response
        analysis = parse_json_response(response["content"], fallback_structure={
            "ats_score": 0, "strong_skills": [], "weak_skills": [], 
            "missing_keywords": [], "grammar_issues": [], 
            "experience_analysis": "", "project_analysis": "", 
            "summary": "Analysis unavailable", "action_plan": []
        })
        
        # Save analysis to database
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
        except Exception as e:
            print(f"[WARN] Failed to save analysis: {str(e)}")
        
        analysis["mock"] = response.get("mock", False)
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
