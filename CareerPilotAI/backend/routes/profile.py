"""
CareerPilot AI — Profile Routes
Full Career DNA profile management.
Uses CareerProfileService as the single source of truth.
"""

from flask import (Blueprint, render_template, request, session,
                   redirect, url_for, flash, jsonify)
from backend.utils.decorators import login_required, api_login_required
from backend.models.user import UserModel
from backend.models.chat import ChatModel
from backend.models.project import SettingsModel
from backend.services.auth_service import AuthService
from backend.services.career_profile_service import CareerProfileService

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


# ─────────────────────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────────────────────

@profile_bp.route('/')
@login_required
def index():
    """User Career DNA profile page."""
    user_id = session['user_id']
    user     = UserModel.get_by_id(user_id)
    settings = SettingsModel.get_by_user(user_id)
    snapshot = CareerProfileService.get_career_snapshot(user_id)

    return render_template('profile/index.html',
                           user=user,
                           settings=settings,
                           snapshot=snapshot)


@profile_bp.route('/update', methods=['POST'])
@login_required
def update():
    """Update user profile — marks fields as manual so resume won't overwrite."""
    user_id = session['user_id']

    # Collect all form data
    form_data = {
        'full_name':         request.form.get('full_name', '').strip(),
        'phone':             request.form.get('phone', '').strip(),
        'location':          request.form.get('location', '').strip(),
        'linkedin_url':      request.form.get('linkedin_url', '').strip(),
        'github_url':        request.form.get('github_url', '').strip(),
        'portfolio_url':     request.form.get('portfolio_url', '').strip(),
        'preferred_role':    request.form.get('preferred_role', '').strip(),
        'career_goal':       request.form.get('career_goal', '').strip(),
        'expected_salary':   request.form.get('expected_salary', '').strip(),
        'preferred_location':request.form.get('preferred_location', '').strip(),
        'seniority_level':   request.form.get('seniority_level', '').strip(),
        'domain':            request.form.get('domain', '').strip(),
    }

    # Save via service (handles manual flag marking + mirroring)
    CareerProfileService.save_manual(user_id, form_data)

    session['full_name'] = form_data.get('full_name') or session.get('full_name')
    flash("✅ Profile saved! Your Career DNA has been updated.", 'success')
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
        # Also sync these to career profile as manual
        CareerProfileService.save_manual(user_id, {
            'preferred_role':     request.form.get('preferred_role', ''),
            'preferred_location': request.form.get('preferred_location', ''),
            'expected_salary':    request.form.get('expected_salary', ''),
            'seniority_level':    request.form.get('experience_level', ''),
        })
        flash("Settings saved!", 'success')
        return redirect(url_for('profile.settings'))

    user = UserModel.get_by_id(user_id)
    user_settings = SettingsModel.get_by_user(user_id)
    snapshot = CareerProfileService.get_career_snapshot(user_id)

    from backend.config import Config
    return render_template('profile/settings.html',
                           user=user,
                           settings=user_settings,
                           snapshot=snapshot,
                           host=Config.OLLAMA_HOST,
                           model_name=Config.OLLAMA_MODEL)


@profile_bp.route('/history')
@login_required
def history():
    """Activity history page."""
    user_id = session['user_id']

    from backend.models.resume import ResumeModel
    from backend.models.job import JobModel
    from backend.models.interview import InterviewModel

    chats      = ChatModel.get_user_sessions(user_id)
    resumes    = ResumeModel.get_by_user(user_id)
    interviews = InterviewModel.get_by_user(user_id)

    return render_template('profile/history.html',
                           chats=chats, resumes=resumes, interviews=interviews)


@profile_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    user_id = session['user_id']
    current = request.form.get('current_password', '')
    new     = request.form.get('new_password', '')

    success, message = AuthService.change_password(user_id, current, new)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('profile.settings'))


# ─────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────

@profile_bp.route('/api/snapshot')
@api_login_required
def api_snapshot():
    """API: Get Career DNA snapshot for any page to consume."""
    user_id  = session['user_id']
    snapshot = CareerProfileService.get_career_snapshot(user_id)
    return jsonify({"success": True, "snapshot": snapshot})


@profile_bp.route('/api/prefill/<module>')
@api_login_required
def api_prefill(module):
    """
    API: Get prefill data for a specific module.
    Modules: jobs, learning, interview, agent, project, chat
    Call from any page's JS to auto-fill forms.
    """
    user_id = session['user_id']
    prefill = CareerProfileService.get_prefill_for_module(user_id, module)
    return jsonify({"success": True, "prefill": prefill})


@profile_bp.route('/api/save', methods=['POST'])
@api_login_required
def api_save():
    """API: Save profile fields (partial updates supported)."""
    user_id   = session['user_id']
    form_data = request.json or {}
    profile   = CareerProfileService.save_manual(user_id, form_data)
    return jsonify({"success": True, "profile": profile})


@profile_bp.route('/api/resync-resume', methods=['POST'])
@api_login_required
def api_resync_resume():
    """API: Re-run AI extraction on the most recent resume and sync profile."""
    user_id = session['user_id']
    from backend.models.resume import ResumeModel
    resume = ResumeModel.get_primary(user_id)
    if not resume or not resume.get('raw_text'):
        return jsonify({"success": False,
                        "error": "No resume found. Please upload one first."}), 404
    profile = CareerProfileService.sync_from_resume(
        user_id, resume['raw_text']
    )
    return jsonify({"success": True, "profile": profile})


@profile_bp.route('/api/completeness')
@api_login_required
def api_completeness():
    """API: Get profile completeness score and missing fields."""
    user_id = session['user_id']
    profile = CareerProfileService.get_profile(user_id)

    fields_status = {
        "full_name":       bool(profile.get("full_name")),
        "preferred_role":  bool(profile.get("preferred_role")),
        "skills":          bool(profile.get("skills")),
        "location":        bool(profile.get("location") or profile.get("preferred_location")),
        "education":       bool(profile.get("education")),
        "experience":      bool(profile.get("experience_years") is not None),
        "career_goal":     bool(profile.get("career_goal")),
        "linkedin":        bool(profile.get("linkedin_url")),
        "github":          bool(profile.get("github_url")),
        "salary":          bool(profile.get("expected_salary")),
    }
    missing = [f for f, ok in fields_status.items() if not ok]

    return jsonify({
        "success":      True,
        "completeness": profile.get("profile_completeness", 0),
        "fields":       fields_status,
        "missing":      missing,
    })


@profile_bp.route('/api/test-ollama', methods=['GET'])
@login_required
def test_ollama():
    """API: Test Ollama connection and fetch model status."""
    from backend.ai.ollama_service import ollama
    result = ollama.check_connection()
    return jsonify(result)
