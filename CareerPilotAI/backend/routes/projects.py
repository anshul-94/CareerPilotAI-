"""
CareerPilot AI — Project Routes
AI project idea generation.
"""

from flask import Blueprint, render_template, request, session, jsonify
from backend.utils.decorators import login_required, api_login_required
from backend.services.project_service import ProjectService

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


@projects_bp.route('/')
@login_required
def index():
    """Project generator page."""
    user_id = session['user_id']
    projects = ProjectService.get_user_projects(user_id)
    return render_template('jobs/project_generator.html', projects=projects)


@projects_bp.route('/generate', methods=['POST'])
@api_login_required
def generate():
    """API: Generate project ideas."""
    user_id = session['user_id']
    data = request.json
    
    domain = data.get('domain', '').strip()
    skills = data.get('skills', [])
    experience_level = data.get('experience_level', 'beginner')
    
    if not domain:
        return jsonify({"success": False, "error": "Domain is required"}), 400
    
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(',') if s.strip()]
    
    result = ProjectService.generate(user_id, domain, skills, experience_level)
    return jsonify({"success": True, **result})
