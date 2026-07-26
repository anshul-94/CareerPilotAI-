"""
CareerPilot AI — Resume Routes
Resume upload, analysis, and builder.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from backend.utils.decorators import login_required, api_login_required, handle_errors
from backend.services.resume_service import ResumeService
from backend.services.resume_intelligence_service import ResumeIntelligenceService
from backend.services.career_profile_service import CareerProfileService
from backend.models.resume import ResumeModel
from backend.utils.helpers import safe_json_loads

resume_bp = Blueprint('resume', __name__, url_prefix='/resume')


@resume_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Resume upload page."""
    user_id = session['user_id']
    
    if request.method == 'POST':
        file = request.files.get('resume')
        success, message, resume_id = ResumeService.upload_resume(user_id, file)
        
        if success:
            flash(message, 'success')
            
            # Smart Synchronization: invalidate and regenerate
            from backend.services.autonomous_agent import AutonomousAgent
            AutonomousAgent.invalidate_and_regenerate(user_id)
            
            return redirect(url_for('resume.analyze', resume_id=resume_id))
        else:
            flash(message, 'danger')
    
    resumes = ResumeService.get_user_resumes(user_id)
    return render_template('resume/upload.html', resumes=resumes)


@resume_bp.route('/analyze')
@resume_bp.route('/analyze/<int:resume_id>')
@login_required
def analyze(resume_id=None):
    """Resume analysis page."""
    user_id = session['user_id']
    
    if not resume_id:
        primary = ResumeModel.get_primary(user_id)
        if primary:
            resume_id = primary['id']
        else:
            flash("Please upload a resume first.", 'warning')
            return redirect(url_for('resume.upload'))
    
    resume = ResumeModel.get_by_id(resume_id)
    if not resume or resume['user_id'] != user_id:
        flash("Resume not found.", 'danger')
        return redirect(url_for('resume.upload'))
    
    # Check for existing analysis
    from backend.models.project import ResumeAnalysisModel
    analysis = ResumeAnalysisModel.get_by_resume(resume_id)
    if analysis:
        for field in ['strong_skills', 'weak_skills', 'missing_keywords',
                      'grammar_issues', 'action_plan', 'full_analysis']:
            if isinstance(analysis.get(field), str):
                analysis[field] = safe_json_loads(analysis[field], [])
    
    return render_template('resume/analyze.html', resume=resume, analysis=analysis)


@resume_bp.route('/analyze/run', methods=['POST'])
@api_login_required
def run_analysis():
    """API: Run AI analysis on a resume."""
    user_id = session['user_id']
    resume_id = request.json.get('resume_id')
    target_role = request.json.get('target_role', '')
    
    if not resume_id:
        return jsonify({"success": False, "error": "Resume ID required"}), 400
    
    success, message, analysis = ResumeService.analyze_resume(
        resume_id, user_id, target_role
    )
    
    if success:
        return jsonify({"success": True, "analysis": analysis})
    else:
        return jsonify({"success": False, "error": message}), 400


@resume_bp.route('/builder')
@login_required
def builder():
    """AI Resume Intelligence Dashboard."""
    user_id = session['user_id']
    from backend.models.user import UserModel
    user = UserModel.get_by_id(user_id)
    
    # Pre-fetch the latest AI version if it exists
    latest_version = ResumeIntelligenceService.get_latest_version(user_id)
    profile = CareerProfileService.get_profile(user_id)
    
    # Autonomous AI: trigger generation silently (will skip if fresh)
    from backend.services.autonomous_agent import AutonomousAgent
    AutonomousAgent.trigger_resume_generation(user_id, profile.get('preferred_role', ''))
    
    return render_template('resume/intelligence.html', 
                           user=user, 
                           latest_version=latest_version,
                           profile=profile)


@resume_bp.route('/api/intelligence/generate', methods=['POST'])
@api_login_required
def intelligence_generate():
    """API: Trigger AI to rewrite and optimize the resume."""
    user_id = session['user_id']
    data = request.json
    target_role = data.get('target_role', 'Software Developer')
    template = data.get('template', 'modern')
    
    result = ResumeIntelligenceService.generate_optimized_resume(user_id, target_role, template)
    
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 500
        
    return jsonify(result)


@resume_bp.route('/api/intelligence/versions', methods=['GET'])
@api_login_required
def intelligence_versions():
    """API: Fetch version history."""
    user_id = session['user_id']
    versions = ResumeIntelligenceService.get_version_history(user_id)
    return jsonify({"success": True, "versions": versions})


@resume_bp.route('/api/intelligence/daily-optimize', methods=['POST'])
@api_login_required
def intelligence_daily_optimize():
    """API: Trigger the daily background optimization manually for demo purposes."""
    user_id = session['user_id']
    result = ResumeIntelligenceService.run_daily_optimization(user_id)
    
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 500
        
    return jsonify(result)


@resume_bp.route('/delete/<int:resume_id>', methods=['POST'])
@login_required
def delete(resume_id):
    """Delete a resume."""
    user_id = session['user_id']
    resume = ResumeModel.get_by_id(resume_id)
    
    if resume and resume['user_id'] == user_id:
        import os
        filepath = os.path.join(ResumeService.UPLOAD_FOLDER, resume['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        ResumeModel.delete(resume_id)
        flash("Resume deleted.", 'info')
    
    return redirect(url_for('resume.upload'))
