"""
CareerPilot AI — Auth Routes
Handles login, registration, and logout.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from backend.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        success, message, user = AuthService.login(username, password)
        
        if success and user:
            session_data = AuthService.get_session_data(user)
            session.update(session_data)
            flash(message, 'success')
            
            # Fire autonomous background tasks
            from backend.services.autonomous_agent import AutonomousAgent
            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
            if user_id:
                AutonomousAgent.on_login(user_id)
            
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard.index'))
        else:
            flash(message, 'danger')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and account creation."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        
        success, message, user_id = AuthService.register(
            username, email, password, confirm_password, full_name
        )
        
        if success:
            flash(message + " Please log in.", 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
    
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('auth.login'))
