"""
CareerPilot AI — Decorators
Custom decorators for route protection and error handling.
"""

import functools
from flask import session, redirect, url_for, flash, request, jsonify, g


def login_required(f):
    """
    Decorator to require user authentication.
    Redirects to login page if not authenticated.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin privileges.
    Redirects to dashboard if not an admin.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        if session.get('user_role') != 'admin':
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """
    Decorator for API endpoints requiring authentication.
    Returns JSON error instead of redirect.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def handle_errors(f):
    """
    Decorator to catch and handle exceptions gracefully.
    Returns appropriate error responses for both web and API requests.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] {f.__name__}: {error_msg}")
            
            # Check if this is an API request
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    "success": False,
                    "error": "An unexpected error occurred",
                    "details": error_msg
                }), 500
            
            flash(f"An error occurred: {error_msg}", "danger")
            return redirect(request.referrer or url_for('dashboard.index'))
    return decorated_function
