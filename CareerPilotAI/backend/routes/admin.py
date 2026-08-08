"""
CareerPilot AI — Admin Routes & Controller
Provides endpoints for the isolated Admin Panel: Authentication, Dashboard, User Management,
Submissions, Problem Analytics, AI Usage, Activity Timeline, Search, and Audit Logs.
"""

import functools
from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash
from backend.models.admin import AdminModel
from backend.services.admin_service import AdminAuthService, AdminAnalyticsService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """
    Strict security decorator: Protects all admin endpoints.
    Requires an authenticated admin session.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id') or session.get('admin_role') != 'admin':
            if request.is_json or request.path.startswith('/admin/api/'):
                return jsonify({
                    "success": False,
                    "error": "Admin authorization required."
                }), 403
            flash("Admin login required.", "warning")
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ── Authentication Routes ────────────────────────────────────────

@admin_bp.route('/')
def root():
    """Admin entrypoint: Redirects to dashboard if logged in, else login."""
    if session.get('admin_id') and session.get('admin_role') == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page and authentication."""
    if session.get('admin_id') and session.get('admin_role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip_addr = request.remote_addr or ""

        success, message, admin_user = AdminAuthService.login(username, password, ip_addr)

        if success and admin_user:
            session['admin_id'] = admin_user['id']
            session['admin_username'] = admin_user['username']
            session['admin_email'] = admin_user['email']
            session['admin_role'] = admin_user['role']

            flash("Welcome to CareerPilot AI Admin Panel.", "success")
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin.dashboard'))
        else:
            flash(message, "danger")

    return render_template('admin/login.html')


@admin_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Log out admin and clear admin session keys."""
    admin_id = session.get('admin_id')
    admin_username = session.get('admin_username', 'Admin')
    ip_addr = request.remote_addr or ""

    AdminAuthService.log_logout(admin_id, admin_username, ip_addr)

    session.pop('admin_id', None)
    session.pop('admin_username', None)
    session.pop('admin_email', None)
    session.pop('admin_role', None)

    flash("Admin logged out successfully.", "info")
    return redirect(url_for('admin.login'))


# ── Dashboard ───────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin overview dashboard with real platform metrics and charts."""
    stats = AdminAnalyticsService.get_dashboard_metrics()
    chart_data = AdminAnalyticsService.get_dashboard_chart_data()
    recent_activities = AdminAnalyticsService.get_activity_timeline(limit=8)

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        chart_data=chart_data,
        recent_activities=recent_activities
    )


# ── User Management ─────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    """List registered users with search, status filters, sorting, and pagination."""
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    sort_by = request.args.get('sort', 'created_at').strip()
    order = request.args.get('order', 'DESC').strip()
    page = request.args.get('page', 1, type=int)

    users_list, total_count, total_pages = AdminAnalyticsService.get_users_list(
        search=search,
        status=status,
        sort_by=sort_by,
        order=order,
        page=page,
        per_page=20
    )

    return render_template(
        'admin/users.html',
        users=users_list,
        total_count=total_count,
        total_pages=total_pages,
        page=page,
        search=search,
        status=status,
        sort=sort_by,
        order=order
    )


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id: int):
    """Inspect detailed activity for a single user."""
    data = AdminAnalyticsService.get_user_detail(user_id)
    if not data:
        flash(f"User #{user_id} not found.", "danger")
        return redirect(url_for('admin.users'))

    # Record audit log
    AdminModel.log_audit(
        session.get('admin_id'),
        session.get('admin_username', 'Admin'),
        "VIEW_USER",
        f"User ID: {user_id} ({data['user']['username']})",
        request.remote_addr or ""
    )

    return render_template('admin/user_detail.html', **data)


# ── Submissions Monitoring ──────────────────────────────────────

@admin_bp.route('/submissions')
@admin_required
def submissions():
    """Monitor coding submissions with multi-criteria filters and pagination."""
    user_query = request.args.get('user', '').strip()
    problem_query = request.args.get('problem', '').strip()
    language = request.args.get('language', '').strip()
    verdict = request.args.get('verdict', '').strip()
    date_filter = request.args.get('date', '').strip()
    page = request.args.get('page', 1, type=int)

    submissions_list, total_count, total_pages = AdminAnalyticsService.get_submissions_list(
        user_query=user_query,
        problem_query=problem_query,
        language=language,
        verdict=verdict,
        date_filter=date_filter,
        page=page,
        per_page=25
    )

    return render_template(
        'admin/submissions.html',
        submissions=submissions_list,
        total_count=total_count,
        total_pages=total_pages,
        page=page,
        user_query=user_query,
        problem_query=problem_query,
        language=language,
        verdict=verdict,
        date_filter=date_filter
    )


# ── Problem Analytics ───────────────────────────────────────────

@admin_bp.route('/problems')
@admin_required
def problems():
    """Analytics on problems, difficulty, attempt rates, and performance."""
    search = request.args.get('search', '').strip()
    difficulty = request.args.get('difficulty', '').strip()
    topic = request.args.get('topic', '').strip()
    sort_by = request.args.get('sort', 'attempts').strip()
    page = request.args.get('page', 1, type=int)

    problems_list, highlights, total_count, total_pages = AdminAnalyticsService.get_problems_analytics(
        search=search,
        difficulty=difficulty,
        topic=topic,
        sort_by=sort_by,
        page=page,
        per_page=25
    )

    return render_template(
        'admin/problems.html',
        problems=problems_list,
        highlights=highlights,
        total_count=total_count,
        total_pages=total_pages,
        page=page,
        search=search,
        difficulty=difficulty,
        topic=topic,
        sort=sort_by
    )


# ── AI Usage Analytics ──────────────────────────────────────────

@admin_bp.route('/ai-analytics')
@admin_required
def ai_analytics():
    """Review real AI interactions across Mentor, Coach, Job Agent, and Code Review."""
    analytics = AdminAnalyticsService.get_ai_analytics()
    return render_template('admin/ai_analytics.html', analytics=analytics)


# ── Activity Timeline ───────────────────────────────────────────

@admin_bp.route('/activity')
@admin_required
def activity():
    """Real platform activity stream."""
    events = AdminAnalyticsService.get_activity_timeline(limit=60)
    return render_template('admin/activity.html', events=events)


# ── Audit Logs ──────────────────────────────────────────────────

@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    """Administrative action audit history."""
    page = request.args.get('page', 1, type=int)
    per_page = 30
    logs = AdminModel.get_audit_logs(limit=per_page, offset=(page - 1) * per_page)
    total_count = AdminModel.count_audit_logs()
    total_pages = max(1, (total_count + per_page - 1) // per_page)

    return render_template(
        'admin/audit_logs.html',
        logs=logs,
        total_count=total_count,
        total_pages=total_pages,
        page=page
    )


# ── Global Search ───────────────────────────────────────────────

@admin_bp.route('/search')
@admin_required
def search():
    """Global search across users, problems, and submissions."""
    q = request.args.get('q', '').strip()
    results = {"users": [], "problems": [], "submissions": []}
    if q:
        results = AdminAnalyticsService.global_search(q)

    return render_template('admin/search.html', q=q, results=results)


# ── Admin JSON APIs ─────────────────────────────────────────────

@admin_bp.route('/api/users/<int:user_id>/status', methods=['POST'])
@admin_required
def api_toggle_user_status(user_id: int):
    """Toggle user active / inactive state with audit logging."""
    data = request.get_json(silent=True) or {}
    active_val = data.get('active')
    
    if active_val is None:
        # Toggle if not explicitly sent
        from backend.database.db import execute_one
        curr = execute_one("SELECT is_active FROM users WHERE id = ?", (user_id,))
        if not curr:
            return jsonify({"success": False, "error": "User not found"}), 404
        active_val = 0 if curr.get("is_active") == 1 else 1

    success = AdminAnalyticsService.toggle_user_status(
        user_id=user_id,
        active=int(active_val),
        admin_id=session.get('admin_id'),
        admin_username=session.get('admin_username', 'Admin'),
        ip=request.remote_addr or ""
    )

    if success:
        return jsonify({
            "success": True,
            "data": {
                "user_id": user_id,
                "is_active": int(active_val),
                "status_label": "Active" if active_val == 1 else "Inactive"
            }
        })
    else:
        return jsonify({"success": False, "error": "Failed to update user status."}), 500


@admin_bp.route('/api/charts/dashboard')
@admin_required
def api_dashboard_charts():
    """Fetch dashboard charts data as JSON."""
    data = AdminAnalyticsService.get_dashboard_chart_data()
    return jsonify({"success": True, "data": data})
