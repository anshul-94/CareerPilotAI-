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
    if session.get('admin_id') and session.get('admin_role') == 'admin':
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # 1. Server-side Admin authentication check
        from backend.services.admin_service import AdminAuthService
        admin_success, admin_msg, admin_user = AdminAuthService.login(
            username, password, request.remote_addr or ""
        )
        if admin_success and admin_user:
            session['admin_id'] = admin_user['id']
            session['admin_username'] = admin_user['username']
            session['admin_email'] = admin_user['email']
            session['admin_role'] = admin_user['role']
            flash("Welcome to CareerPilot AI Admin Panel.", "success")
            return redirect(url_for('admin.dashboard'))
        
        # 2. Normal user authentication flow
        success, message, user = AuthService.login(username, password)
        
        if success and user:
            # If user has admin role in users table
            if user.get('role') == 'admin':
                session['admin_id'] = user['id']
                session['admin_username'] = user['username']
                session['admin_email'] = user['email']
                session['admin_role'] = 'admin'
                flash("Welcome to CareerPilot AI Admin Panel.", "success")
                return redirect(url_for('admin.dashboard'))
            
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
            flash(message or admin_msg or "Invalid username or password", 'danger')
    
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
        
        if success and user_id:
            from backend.models.user import UserModel
            user = UserModel.get_by_id(user_id)
            if user:
                session_data = AuthService.get_session_data(user)
                session.update(session_data)
                flash(message, 'success')
                
                # Fire autonomous background tasks
                from backend.services.autonomous_agent import AutonomousAgent
                AutonomousAgent.on_login(user_id)
                
                return redirect(url_for('dashboard.index'))
            
            flash(message, 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash(message, 'danger')
    
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('auth.login'))
