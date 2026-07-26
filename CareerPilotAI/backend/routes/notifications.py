"""
CareerPilot AI — Notification Agent Routes
Flask Blueprint for the AI Job Notification Agent.
Provides all API endpoints for the proactive job notification feature.
"""

from flask import Blueprint, render_template, request, session, jsonify
from backend.utils.decorators import login_required, api_login_required
from backend.services.job_agent_service import JobNotificationAgent
from backend.models.job_notification import (
    AgentProfileModel,
    JobNotificationModel,
    AgentRunModel,
    migrate_notification_tables,
)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


# ── Run migration on first import ────────────────────────────
try:
    migrate_notification_tables()
except Exception as _e:
    print(f"[WARN] Notification table migration: {_e}")


# ─────────────────────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────────────────────

@notifications_bp.route('/')
@login_required
def index():
    """AI Job Notification Agent main page."""
    user_id = session['user_id']

    # Get existing data to pre-populate the page
    notifications = JobNotificationModel.get_by_user(user_id, limit=50)
    stats         = JobNotificationModel.get_stats(user_id)
    profile_row   = AgentProfileModel.get_by_user(user_id)
    last_run      = AgentRunModel.get_last(user_id)

    profile = AgentProfileModel.parse(profile_row) if profile_row else {}

    # Categorize notifications for tab counts
    high_match  = [n for n in notifications if n.get('resume_match', 0) >= 80]
    medium_match = [n for n in notifications if 60 <= n.get('resume_match', 0) < 80]
    low_match   = [n for n in notifications if n.get('resume_match', 0) < 60]
    urgent      = [n for n in notifications if n.get('urgency') == 'urgent']
    remote      = [n for n in notifications if n.get('is_remote')]

    return render_template(
        'jobs/notifications.html',
        notifications=notifications,
        stats=stats,
        profile=profile,
        last_run=last_run,
        high_match=high_match,
        medium_match=medium_match,
        low_match=low_match,
        urgent=urgent,
        remote_jobs=remote,
        has_profile=bool(profile_row),
        has_data=len(notifications) > 0,
    )


# ─────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────

@notifications_bp.route('/api/run-agent', methods=['POST'])
@api_login_required
def run_agent():
    """
    API: Trigger the AI Job Notification Agent.
    Searches jobs, scores them, stores notifications.
    """
    user_id = session['user_id']
    data    = request.json or {}
    fresh   = data.get('fresh', True)

    result = JobNotificationAgent.run_agent(user_id, fresh_search=fresh)

    if result.get("success"):
        return jsonify({
            "success": True,
            "run_id":        result.get("run_id"),
            "jobs_searched": result.get("jobs_searched", 0),
            "jobs_matched":  result.get("jobs_matched", 0),
            "daily_summary": result.get("daily_summary", {}),
            "stats":         result.get("stats", {}),
        })

    return jsonify({
        "success": False,
        "error": result.get("error", "Agent run failed")
    }), 500


@notifications_bp.route('/api/extract-profile', methods=['POST'])
@api_login_required
def extract_profile():
    """
    API: Extract AI career profile from uploaded resume.
    Returns structured profile data.
    """
    user_id = session['user_id']
    result  = JobNotificationAgent.extract_profile(user_id)

    if result.get("success"):
        return jsonify({
            "success": True,
            "profile": result["profile"]
        })
    return jsonify({
        "success": False,
        "error": result.get("error", "Profile extraction failed")
    }), 400


@notifications_bp.route('/api/notifications')
@api_login_required
def get_notifications():
    """
    API: Fetch job notifications with optional filters.
    Query params: category, status, limit
    """
    user_id  = session['user_id']
    category = request.args.get('category', None)
    status   = request.args.get('status', None)
    limit    = int(request.args.get('limit', 50))

    # Map category filter
    if category == 'high_match':
        jobs = JobNotificationModel.get_by_user(user_id, limit=limit)
        jobs = [j for j in jobs if j.get('resume_match', 0) >= 80]
    elif category == 'medium_match':
        jobs = JobNotificationModel.get_by_user(user_id, limit=limit)
        jobs = [j for j in jobs if 60 <= j.get('resume_match', 0) < 80]
    elif category == 'low_match':
        jobs = JobNotificationModel.get_by_user(user_id, limit=limit)
        jobs = [j for j in jobs if j.get('resume_match', 0) < 60]
    elif category == 'urgent':
        jobs = JobNotificationModel.get_by_user(user_id, limit=limit)
        jobs = [j for j in jobs if j.get('urgency') == 'urgent']
    elif category == 'remote':
        jobs = JobNotificationModel.get_by_user(user_id, limit=limit)
        jobs = [j for j in jobs if j.get('is_remote')]
    elif category == 'saved':
        jobs = JobNotificationModel.get_by_user(user_id, status='saved', limit=limit)
    else:
        jobs = JobNotificationModel.get_by_user(user_id, status=status, limit=limit)

    return jsonify({
        "success": True,
        "jobs":    jobs,
        "total":   len(jobs)
    })


@notifications_bp.route('/api/stats')
@api_login_required
def get_stats():
    """API: Get notification dashboard statistics."""
    user_id = session['user_id']
    stats   = JobNotificationModel.get_stats(user_id)
    profile = AgentProfileModel.get_by_user(user_id)
    last_run = AgentRunModel.get_last(user_id)

    return jsonify({
        "success":    True,
        "stats":      stats,
        "has_profile": bool(profile),
        "last_run":   dict(last_run) if last_run else None,
    })


@notifications_bp.route('/api/update-status', methods=['POST'])
@api_login_required
def update_status():
    """
    API: Update a job notification status.
    Actions: save, apply, hide
    """
    data   = request.json or {}
    job_id = data.get('job_id')
    action = data.get('action', '').lower()

    status_map = {
        'save':  'saved',
        'apply': 'applied',
        'hide':  'hidden',
        'reset': 'new',
    }
    status = status_map.get(action)

    if not job_id or not status:
        return jsonify({"success": False, "error": "Invalid job_id or action"}), 400

    rows_affected = JobNotificationModel.update_status(job_id, status)
    return jsonify({"success": rows_affected > 0, "new_status": status})


@notifications_bp.route('/api/insights')
@api_login_required
def get_insights():
    """API: Get AI-generated career insights."""
    user_id  = session['user_id']
    insights = JobNotificationAgent.get_insights(user_id)
    return jsonify({"success": True, "insights": insights})


@notifications_bp.route('/api/chart-data')
@api_login_required
def get_chart_data():
    """API: Get all chart datasets for the notification dashboard."""
    user_id    = session['user_id']
    chart_data = JobNotificationAgent.get_chart_data(user_id)
    return jsonify({"success": True, "charts": chart_data})


@notifications_bp.route('/api/daily-summary')
@api_login_required
def get_daily_summary():
    """API: Get today's AI daily briefing."""
    user_id = session['user_id']
    profile_row = AgentProfileModel.get_by_user(user_id)
    stats = JobNotificationModel.get_stats(user_id)
    top_jobs = JobNotificationModel.get_by_user(user_id, limit=5)
    profile = AgentProfileModel.parse(profile_row) if profile_row else {}

    summary = JobNotificationAgent._generate_daily_summary(profile, stats, top_jobs)
    return jsonify({"success": True, "summary": summary})


@notifications_bp.route('/api/missing-skills')
@api_login_required
def get_missing_skills():
    """API: Get aggregated missing skills across all job notifications."""
    user_id = session['user_id']
    skills  = JobNotificationModel.get_missing_skills_summary(user_id)
    return jsonify({"success": True, "missing_skills": skills})


@notifications_bp.route('/api/profile')
@api_login_required
def get_profile():
    """API: Get user's AI career profile."""
    user_id     = session['user_id']
    profile_row = AgentProfileModel.get_by_user(user_id)
    if not profile_row:
        return jsonify({"success": False, "error": "No profile found. Run the agent first."}), 404
    profile = AgentProfileModel.parse(profile_row)
    return jsonify({"success": True, "profile": profile})
