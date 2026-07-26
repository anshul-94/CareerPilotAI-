"""
CareerPilot AI — Interview Routes
Mock interview sessions with AI evaluation.
Auto-prefills role and experience from Career DNA profile.
"""

from flask import Blueprint, render_template, request, session, jsonify
from backend.utils.decorators import login_required, api_login_required
from backend.services.interview_service import InterviewService
from backend.services.career_profile_service import CareerProfileService

interview_bp = Blueprint('interview', __name__, url_prefix='/interview')


@interview_bp.route('/')
@login_required
def index():
    """Mock interview setup page — auto-prefilled from Career DNA profile."""
    user_id = session['user_id']
    history = InterviewService.get_user_history(user_id)
    stats   = InterviewService.get_stats(user_id)
    prefill = CareerProfileService.get_prefill_for_module(user_id, 'interview')

    return render_template('interview/index.html',
                           history=history,
                           stats=stats,
                           prefill=prefill)


@interview_bp.route('/start', methods=['POST'])
@api_login_required
def start():
    """API: Start a new interview session."""
    data = request.json
    user_id = session['user_id']
    
    role = data.get('role', 'Software Developer').strip()
    difficulty = data.get('difficulty', 'medium')
    experience_years = int(data.get('experience_years', 0))
    interview_type = data.get('interview_type', 'technical')
    
    result = InterviewService.start_session(
        user_id, role, difficulty, experience_years, interview_type
    )
    
    return jsonify({"success": True, **result})


@interview_bp.route('/evaluate', methods=['POST'])
@api_login_required
def evaluate():
    """API: Submit answers and get evaluation."""
    data = request.json
    interview_id = data.get('interview_id')
    answers = data.get('answers', [])
    
    if not interview_id:
        return jsonify({"success": False, "error": "Interview ID required"}), 400
    
    result = InterviewService.evaluate_session(interview_id, answers)
    
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400
    
    return jsonify({"success": True, **result})
