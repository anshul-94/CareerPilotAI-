"""
CareerPilot AI — Input Validators
Validation functions for user inputs across the application.
"""

import re
from typing import Optional, Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format."""
    if not email or not email.strip():
        return False, "Email is required"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email.strip()):
        return False, "Invalid email format"
    
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format."""
    if not username or not username.strip():
        return False, "Username is required"
    
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username must be less than 30 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
    if not password:
        return False, "Password is required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 128:
        return False, "Password is too long"
    
    return True, ""


def validate_registration(username: str, email: str, password: str,
                          confirm_password: str) -> Tuple[bool, str]:
    """Validate all registration fields."""
    valid, msg = validate_username(username)
    if not valid:
        return False, msg
    
    valid, msg = validate_email(email)
    if not valid:
        return False, msg
    
    valid, msg = validate_password(password)
    if not valid:
        return False, msg
    
    if password != confirm_password:
        return False, "Passwords do not match"
    
    return True, ""


def validate_resume_file(filename: str, file_size: int = 0) -> Tuple[bool, str]:
    """Validate resume file upload."""
    if not filename:
        return False, "No file selected"
    
    allowed_extensions = {'pdf'}
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext not in allowed_extensions:
        return False, "Only PDF files are allowed"
    
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        return False, "File size must be less than 10MB"
    
    return True, ""


def validate_chat_message(message: str) -> Tuple[bool, str]:
    """Validate chat message."""
    if not message or not message.strip():
        return False, "Message cannot be empty"
    if len(message) > 5000:
        return False, "Message is too long (max 5000 characters)"
    
    return True, ""


def validate_code_input(code: str) -> Tuple[bool, str]:
    """Validate code input for review."""
    if not code or not code.strip():
        return False, "Code input cannot be empty"
    if len(code) > 50000:
        return False, "Code is too long (max 50000 characters)"
    
    return True, ""


def validate_sql_query(query: str) -> Tuple[bool, str]:
    """Validate SQL query input."""
    if not query or not query.strip():
        return False, "SQL query cannot be empty"
    if len(query) > 10000:
        return False, "Query is too long (max 10000 characters)"
    
    return True, ""


def sanitize_input(text: str) -> str:
    """Sanitize user input by removing potentially dangerous characters."""
    if not text:
        return ""
    # Remove null bytes and control characters (keep newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()
