"""
CareerPilot AI — Job Routes
AI-powered job search, matching, and tracking.
"""

from flask import Blueprint, render_template, request, session, jsonify
from backend.utils.decorators import login_required, api_login_required
from backend.services.job_service import JobService

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs_bp.route('/')
@login_required
def index():
    """Job finder page."""
    user_id = session['user_id']
    saved_jobs = JobService.get_user_jobs(user_id, status='saved')
    applied_jobs = JobService.get_user_jobs(user_id, status='applied')
    recent_jobs = JobService.get_user_jobs(user_id)[:10]
    
    return render_template('jobs/index.html',
                         saved_jobs=saved_jobs,
                         applied_jobs=applied_jobs,
                         recent_jobs=recent_jobs)


@jobs_bp.route('/search', methods=['POST'])
@api_login_required
def search():
    """API: Search for jobs."""
    user_id = session['user_id']
    data = request.json
    
    query = data.get('query', '').strip()
    role = data.get('role', '').strip()
    location = data.get('location', '').strip()
    
    result = JobService.search_for_user(user_id, query, role, location)
    
    return jsonify({
        "success": True,
        "jobs": result["jobs"],
        "total": result["total"],
        "queries_used": result.get("queries_used", []),
        "user_skills": result.get("user_skills", [])
    })


@jobs_bp.route('/match/<int:job_id>')
@api_login_required
def match(job_id):
    """API: Get detailed match analysis for a job."""
    user_id = session['user_id']
    analysis = JobService.get_match_analysis(user_id, job_id)
    return jsonify({"success": True, "analysis": analysis})


@jobs_bp.route('/status', methods=['POST'])
@api_login_required
def update_status():
    """API: Update job application status."""
    data = request.json
    job_id = data.get('job_id')
    status = data.get('status')
    
    if not job_id or not status:
        return jsonify({"success": False, "error": "Job ID and status required"}), 400
    
    success = JobService.update_job_status(job_id, status)
    return jsonify({"success": success})
