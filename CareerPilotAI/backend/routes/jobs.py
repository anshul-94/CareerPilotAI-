"""
CareerPilot AI — Job Routes
AI-powered job search, matching, and tracking.
Now auto-prefills from Career DNA profile.
"""

from flask import Blueprint, render_template, request, session, jsonify
from backend.utils.decorators import login_required, api_login_required
from backend.services.job_service import JobService
from backend.services.career_profile_service import CareerProfileService

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs_bp.route('/')
@login_required
def index():
    """Job finder page — auto-prefilled from Career DNA profile."""
    user_id      = session['user_id']
    saved_jobs   = JobService.get_user_jobs(user_id, status='saved')
    applied_jobs = JobService.get_user_jobs(user_id, status='applied')
    recent_jobs  = JobService.get_user_jobs(user_id)[:10]

    # Build profile-based prefill (no asking the user again)
    prefill = CareerProfileService.get_prefill_for_module(user_id, 'jobs')

    return render_template('jobs/index.html',
                           saved_jobs=saved_jobs,
                           applied_jobs=applied_jobs,
                           recent_jobs=recent_jobs,
                           prefill=prefill)


@jobs_bp.route('/search', methods=['POST'])
@api_login_required
def search():
    """
    API: Search for jobs.
    If no query/role/location provided, uses profile-based prefill automatically.
    Override flag: pass override=true to use user-provided values without updating profile.
    """
    user_id = session['user_id']
    data    = request.json or {}

    is_override = data.get('override', False)

    query    = data.get('query', '').strip()
    role     = data.get('role', '').strip()
    location = data.get('location', '').strip()

    # If NOT overriding and fields are empty, auto-fill from profile
    if not is_override and not any([query, role, location]):
        prefill  = CareerProfileService.get_prefill_for_module(user_id, 'jobs')
        role     = role     or prefill.get('preferred_role', '')
        location = location or prefill.get('preferred_location', '')

    result = JobService.search_for_user(user_id, query, role, location)
    
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 500

    return jsonify({
        "success":      True,
        "jobs":         result["jobs"],
        "total":        result["total"],
        "queries_used": result.get("queries_used", []),
        "user_skills":  result.get("user_skills", []),
        "is_override":  is_override,
        "search_context": {
            "role":     role,
            "location": location,
        }
    })


@jobs_bp.route('/search/override', methods=['POST'])
@api_login_required
def search_override():
    """
    API: Temporary override search — uses user-provided values.
    Does NOT modify the user's Career DNA profile.
    """
    user_id = session['user_id']
    data    = request.json or {}

    # Use exactly what the user typed — no profile merge
    query    = data.get('query', '').strip()
    role     = data.get('role', '').strip()
    location = data.get('location', '').strip()

    if not any([query, role, location]):
        return jsonify({"success": False,
                        "error": "Please provide a search term for override."}), 400

    result = JobService.search_for_user(user_id, query, role, location)
    
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 500

    return jsonify({
        "success":        True,
        "jobs":           result["jobs"],
        "total":          result["total"],
        "queries_used":   result.get("queries_used", []),
        "is_override":    True,
        "search_context": {"role": role, "location": location},
    })


@jobs_bp.route('/match/<int:job_id>')
@api_login_required
def match(job_id):
    """API: Get detailed match analysis for a job."""
    user_id  = session['user_id']
    analysis = JobService.get_match_analysis(user_id, job_id)
    return jsonify({"success": True, "analysis": analysis})


@jobs_bp.route('/status', methods=['POST'])
@api_login_required
def update_status():
    """API: Update job application status."""
    data   = request.json or {}
    job_id = data.get('job_id')
    status = data.get('status')

    if not job_id or not status:
        return jsonify({"success": False,
                        "error": "Job ID and status required"}), 400

    success = JobService.update_job_status(job_id, status)
    return jsonify({"success": success})
