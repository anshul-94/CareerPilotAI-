"""
CareerPilot AI — Profile Routes
User profile, settings, and history.
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from backend.utils.decorators import login_required
from backend.models.user import UserModel
from backend.models.chat import ChatModel
from backend.models.project import SettingsModel
from backend.services.auth_service import AuthService

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('/')
@login_required
def index():
    """User profile page."""
    user_id = session['user_id']
    user = UserModel.get_by_id(user_id)
    settings = SettingsModel.get_by_user(user_id)
    return render_template('profile/index.html', user=user, settings=settings)


@profile_bp.route('/update', methods=['POST'])
@login_required
def update():
    """Update user profile."""
    user_id = session['user_id']
    
    UserModel.update_profile(
        user_id,
        full_name=request.form.get('full_name', ''),
        bio=request.form.get('bio', ''),
        phone=request.form.get('phone', ''),
        location=request.form.get('location', ''),
        linkedin_url=request.form.get('linkedin_url', ''),
        github_url=request.form.get('github_url', ''),
        portfolio_url=request.form.get('portfolio_url', '')
    )
    
    session['full_name'] = request.form.get('full_name', session.get('full_name'))
    flash("Profile updated successfully!", 'success')
    return redirect(url_for('profile.index'))


@profile_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page."""
    user_id = session['user_id']
    
    if request.method == 'POST':
        SettingsModel.create_or_update(
            user_id,
            theme=request.form.get('theme', 'dark'),
            notifications=1 if request.form.get('notifications') else 0,
            email_alerts=1 if request.form.get('email_alerts') else 0,
            preferred_role=request.form.get('preferred_role', ''),
            preferred_location=request.form.get('preferred_location', ''),
            expected_salary=int(request.form.get('expected_salary', 0) or 0),
            experience_level=request.form.get('experience_level', 'fresher')
        )
        flash("Settings saved!", 'success')
        return redirect(url_for('profile.settings'))
    
    user = UserModel.get_by_id(user_id)
    user_settings = SettingsModel.get_by_user(user_id)
    
    from backend.config import Config
    
    return render_template('profile/settings.html', user=user, settings=user_settings, 
                           host=Config.OLLAMA_HOST, model_name=Config.OLLAMA_MODEL)

@profile_bp.route('/history')
@login_required
def history():
    """Activity history page."""
    user_id = session['user_id']
    
    from backend.models.resume import ResumeModel
    from backend.models.job import JobModel
    from backend.models.interview import InterviewModel
    
    chats = ChatModel.get_user_sessions(user_id)
    resumes = ResumeModel.get_by_user(user_id)
    interviews = InterviewModel.get_by_user(user_id)
    
    return render_template('profile/history.html',
                         chats=chats, resumes=resumes, interviews=interviews)

@profile_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    user_id = session['user_id']
    current = request.form.get('current_password', '')
    new = request.form.get('new_password', '')
    
    success, message = AuthService.change_password(user_id, current, new)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('profile.settings'))

@profile_bp.route('/api/test-ollama', methods=['GET'])
@login_required
def test_ollama():
    """API: Test Ollama connection and fetch model status."""
    from backend.ai.ollama_service import ollama
    result = ollama.check_connection()
    return jsonify(result)
