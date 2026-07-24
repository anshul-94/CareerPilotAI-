"""
CareerPilot AI — Admin Routes
Admin panel with user management, analytics, and logs.
"""

from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from backend.utils.decorators import admin_required
from backend.models.user import UserModel
from backend.models.resume import ResumeModel
from backend.models.chat import ChatModel
from backend.models.job import JobModel
from backend.database.db import get_table_count

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@admin_required
def index():
    """Admin dashboard with analytics."""
    stats = {
        'total_users': get_table_count('users'),
        'total_resumes': get_table_count('resumes'),
        'total_chats': get_table_count('chat_history'),
        'total_jobs': get_table_count('job_history'),
        'total_interviews': get_table_count('interview_history'),
        'total_roadmaps': get_table_count('learning_roadmaps'),
        'total_projects': get_table_count('projects'),
        'total_code_reviews': get_table_count('code_reviews'),
    }
    
    recent_users = UserModel.get_all(limit=10)
    return render_template('admin/index.html', stats=stats, recent_users=recent_users)


@admin_bp.route('/users')
@admin_required
def users():
    """View all users."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = UserModel.get_all(limit=per_page, offset=(page - 1) * per_page)
    total = UserModel.count()
    return render_template('admin/users.html', users=users, total=total, page=page)


@admin_bp.route('/resumes')
@admin_required
def resumes():
    """View all uploaded resumes."""
    all_resumes = ResumeModel.get_all(limit=50)
    return render_template('admin/resumes.html', resumes=all_resumes)


@admin_bp.route('/chats')
@admin_required
def chats():
    """View chat logs."""
    all_chats = ChatModel.get_all_chats(limit=100)
    return render_template('admin/chats.html', chats=all_chats)


@admin_bp.route('/jobs')
@admin_required
def jobs():
    """View job search analytics."""
    all_jobs = JobModel.get_all(limit=100)
    return render_template('admin/jobs.html', jobs=all_jobs)
