"""
CareerPilot AI — Dashboard Routes
Main dashboard with stats, charts, and recent activity.
"""

from flask import Blueprint, render_template, session
from backend.utils.decorators import login_required
from backend.models.user import UserModel
from backend.models.resume import ResumeModel
from backend.models.chat import ChatModel
from backend.models.interview import InterviewModel
from backend.models.learning import LearningModel
from backend.services.resume_service import ResumeService
from backend.services.job_service import JobService
from backend.services.career_profile_service import CareerProfileService
from backend.utils.helpers import get_greeting, safe_json_loads

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main dashboard page."""
    user_id = session['user_id']
    user = UserModel.get_by_id(user_id)
    
    # Gather dashboard data
    resume_analysis = ResumeService.get_latest_analysis(user_id)
    job_stats = JobService.get_dashboard_stats(user_id)
    interview_stats = InterviewModel.get_stats(user_id)
    recent_chats = ChatModel.get_recent(user_id, limit=5)
    resumes = ResumeModel.get_by_user(user_id)
    
    # Learning progress
    active_roadmap = LearningModel.get_active(user_id)
    learning_progress = 0
    if active_roadmap:
        learning_progress = active_roadmap.get('progress_percent', 0)
    
    # Recent interview scores for chart
    recent_scores = InterviewModel.get_recent_scores(user_id, limit=7)
    
    dashboard_data = {
        'user':             user,
        'greeting':         get_greeting(),
        'resume_score':     resume_analysis.get('ats_score', 0) if resume_analysis else 0,
        'resume_analysis':  resume_analysis,
        'has_resume':       len(resumes) > 0,
        'job_stats':        job_stats,
        'interview_stats':  interview_stats,
        'interview_scores': recent_scores,
        'learning_progress':learning_progress,
        'recent_chats':     recent_chats,
        'total_resumes':    len(resumes),
        'total_chats':      ChatModel.count_by_user(user_id),
        # Career DNA snapshot for the Career Snapshot widget
        'career_snapshot':  CareerProfileService.get_career_snapshot(user_id),
    }

    return render_template('dashboard/index.html', **dashboard_data)
