"""
CareerPilot AI — Auth Service
Handles user registration, login, and session management.
"""

import bcrypt
from typing import Tuple, Optional
from backend.models.user import UserModel
from backend.models.project import SettingsModel
from backend.utils.validators import validate_registration


class AuthService:
    """Business logic for authentication operations."""

    @staticmethod
    def register(username: str, email: str, password: str,
                 confirm_password: str, full_name: str = "") -> Tuple[bool, str, Optional[int]]:
        """
        Register a new user.
        
        Returns:
            Tuple of (success, message, user_id)
        """
        # Validate inputs
        valid, error = validate_registration(username, email, password, confirm_password)
        if not valid:
            return False, error, None
        
        # Check for existing username
        if UserModel.get_by_username(username):
            return False, "Username already exists", None
        
        # Check for existing email
        if UserModel.get_by_email(email):
            return False, "Email already registered", None
        
        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Create user
        try:
            user_id = UserModel.create(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name or username
            )
            
            # Create default settings
            SettingsModel.create_or_update(user_id)
            
            return True, "Registration successful!", user_id
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}", None

    @staticmethod
    def login(username: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Authenticate a user.
        
        Returns:
            Tuple of (success, message, user_dict)
        """
        if not username or not password:
            return False, "Username and password are required", None
        
        # Find user (support both username and email login)
        user = UserModel.get_by_username(username)
        if not user:
            user = UserModel.get_by_email(username)
        
        if not user:
            return False, "Invalid username or password", None
        
        if not user.get('is_active'):
            return False, "Account is deactivated", None
        
        # Verify password
        try:
            if bcrypt.checkpw(password.encode('utf-8'),
                            user['password_hash'].encode('utf-8')):
                # Update last login
                UserModel.update_last_login(user['id'])
                return True, "Login successful!", user
            else:
                return False, "Invalid username or password", None
        except Exception:
            return False, "Authentication error", None

    @staticmethod
    def get_session_data(user: dict) -> dict:
        """Prepare session data from user dict."""
        return {
            'user_id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user.get('full_name', user['username']),
            'avatar_url': user.get('avatar_url', '/static/images/default-avatar.png'),
            'user_role': user.get('role', 'user'),
        }

    @staticmethod
    def change_password(user_id: int, current_password: str,
                        new_password: str) -> Tuple[bool, str]:
        """Change user's password."""
        user = UserModel.get_by_id(user_id)
        if not user:
            return False, "User not found"
        
        if not bcrypt.checkpw(current_password.encode('utf-8'),
                            user['password_hash'].encode('utf-8')):
            return False, "Current password is incorrect"
        
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters"
        
        new_hash = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        from backend.database.db import execute_update
        execute_update(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id)
        )
        
        return True, "Password changed successfully"
