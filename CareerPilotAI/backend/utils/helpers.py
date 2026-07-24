"""
CareerPilot AI — Helper Utilities
Common utility functions used across the application.
"""

import os
import re
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def generate_short_id() -> str:
    """Generate a short unique identifier (8 chars)."""
    return uuid.uuid4().hex[:8]


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def sanitize_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)].rsplit(' ', 1)[0] + suffix


def format_date(date_str: str, fmt: str = "%b %d, %Y") -> str:
    """Format a datetime string for display."""
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        return dt.strftime(fmt)
    except (ValueError, AttributeError):
        return str(date_str)


def format_relative_time(date_str: str) -> str:
    """Format a datetime string as relative time (e.g., '2 hours ago')."""
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        
        now = datetime.now()
        diff = now - dt
        
        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            mins = int(diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins > 1 else ''} ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.days < 7:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            return format_date(date_str)
    except (ValueError, AttributeError):
        return str(date_str)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safely parse JSON string, returning default on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def safe_json_dumps(obj: Any, pretty: bool = False) -> str:
    """Safely serialize object to JSON string."""
    try:
        if pretty:
            return json.dumps(obj, indent=2, default=str)
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return "{}"


def extract_skills_from_text(text: str) -> list[str]:
    """Extract common tech skills from resume text."""
    skill_patterns = [
        "Python", "Java", "JavaScript", "TypeScript", "C\\+\\+", "C#", "Ruby", "Go",
        "Rust", "Swift", "Kotlin", "PHP", "R", "Scala", "Perl",
        "HTML", "CSS", "SQL", "NoSQL", "GraphQL",
        "React", "Angular", "Vue", "Django", "Flask", "Spring", "Express",
        "Node\\.js", "FastAPI", "Laravel", "Rails",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
        "Git", "Linux", "CI/CD", "Jenkins", "GitHub Actions",
        "MongoDB", "PostgreSQL", "MySQL", "Redis", "Elasticsearch",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "REST API", "Microservices", "Agile", "Scrum",
        "Data Science", "Data Engineering", "Data Analysis",
        "AI", "LLM", "GPT", "Prompt Engineering",
        "Figma", "Adobe", "Photoshop", "Illustrator",
        "Power BI", "Tableau", "Excel",
        "Blockchain", "IoT", "Cybersecurity",
        "JIRA", "Confluence", "Slack",
        "OpenCV", "NLTK", "SpaCy", "Hugging Face",
        "Selenium", "Jest", "Pytest", "JUnit",
        "Firebase", "Supabase", "Heroku", "Vercel", "Netlify",
    ]
    
    found_skills = []
    text_upper = text.upper()
    
    for skill in skill_patterns:
        pattern = re.compile(r'\b' + skill + r'\b', re.IGNORECASE)
        if pattern.search(text):
            # Get the original casing from our list
            clean_skill = skill.replace("\\", "")
            if clean_skill not in found_skills:
                found_skills.append(clean_skill)
    
    return found_skills


def calculate_match_score(resume_skills: list[str], job_skills: list[str]) -> int:
    """Calculate match percentage between resume skills and job requirements."""
    if not job_skills:
        return 0
    
    resume_lower = {s.lower() for s in resume_skills}
    job_lower = {s.lower() for s in job_skills}
    
    matched = resume_lower.intersection(job_lower)
    score = int((len(matched) / len(job_lower)) * 100)
    
    return min(100, score)


def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """Check if a file has an allowed extension."""
    if allowed_extensions is None:
        allowed_extensions = {'pdf'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def secure_filename(filename: str) -> str:
    """Generate a secure filename while preserving the extension."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'pdf'
    return f"{generate_short_id()}_{int(datetime.now().timestamp())}.{ext}"


def get_greeting() -> str:
    """Get a time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"
