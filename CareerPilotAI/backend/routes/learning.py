"""
CareerPilot AI — Learning Routes
AI-powered learning roadmap generation.
Auto-prefills target role and skills from Career DNA profile.
"""

from flask import Blueprint, render_template, request, session, jsonify
from backend.utils.decorators import login_required, api_login_required
from backend.services.learning_service import LearningService
from backend.services.career_profile_service import CareerProfileService

learning_bp = Blueprint('learning', __name__, url_prefix='/learning')


@learning_bp.route('/')
@login_required
def index():
    """Learning roadmap page — auto-prefilled from Career DNA profile."""
    user_id  = session['user_id']
    roadmaps = LearningService.get_user_roadmaps(user_id)
    active   = LearningService.get_active_roadmap(user_id)
    prefill  = CareerProfileService.get_prefill_for_module(user_id, 'learning')

    return render_template('learning/index.html',
                           roadmaps=roadmaps,
                           active_roadmap=active,
                           prefill=prefill)


@learning_bp.route('/generate', methods=['POST'])
@api_login_required
def generate():
    """API: Generate a new learning roadmap."""
    user_id = session['user_id']
    data = request.json
    
    target_role = data.get('target_role', '').strip()
    current_skills = data.get('current_skills', [])
    experience_level = data.get('experience_level', 'beginner')
    
    if not target_role:
        return jsonify({"success": False, "error": "Target role is required"}), 400
    
    if isinstance(current_skills, str):
        current_skills = [s.strip() for s in current_skills.split(',') if s.strip()]
    
    roadmap = LearningService.generate_roadmap(
        user_id, target_role, current_skills, experience_level
    )
    
    if "error" in roadmap:
        return jsonify({"success": False, "error": roadmap["error"]}), 500
    
    return jsonify({"success": True, "roadmap": roadmap})


@learning_bp.route('/progress', methods=['POST'])
@api_login_required
def update_progress():
    """API: Update learning progress."""
    data = request.json
    roadmap_id = data.get('roadmap_id')
    progress = data.get('progress', 0)
    
    if not roadmap_id:
        return jsonify({"success": False, "error": "Roadmap ID required"}), 400
    
    success = LearningService.update_progress(roadmap_id, int(progress))
    return jsonify({"success": success})
