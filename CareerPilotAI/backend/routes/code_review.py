"""
CareerPilot AI — Code Review Routes
AI code review and SQL coaching.
"""

from flask import Blueprint, render_template, request, session, jsonify
from backend.utils.decorators import login_required, api_login_required
from backend.services.code_service import CodeService, SQLCoachService

code_bp = Blueprint('code', __name__)


@code_bp.route('/code-review')
@login_required
def code_review():
    """Code review page."""
    user_id = session['user_id']
    history = CodeService.get_history(user_id)
    return render_template('jobs/code_review.html', history=history)


@code_bp.route('/code-review/analyze', methods=['POST'])
@api_login_required
def analyze_code():
    """API: Analyze code."""
    user_id = session['user_id']
    data = request.json
    
    code = data.get('code', '').strip()
    language = data.get('language', 'python')
    
    if not code:
        return jsonify({"success": False, "error": "Code input required"}), 400
    
    if len(code) > 50000:
        return jsonify({"success": False, "error": "Code too long (max 50000 chars)"}), 400
    
    review = CodeService.review_code(user_id, code, language)
    return jsonify({"success": True, "review": review})


@code_bp.route('/sql-coach')
@login_required
def sql_coach():
    """SQL coach page."""
    user_id = session['user_id']
    history = SQLCoachService.get_history(user_id)
    return render_template('jobs/sql_coach.html', history=history)


@code_bp.route('/sql-coach/analyze', methods=['POST'])
@api_login_required
def analyze_sql():
    """API: Analyze SQL query."""
    user_id = session['user_id']
    data = request.json
    
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({"success": False, "error": "SQL query required"}), 400
    
    analysis = SQLCoachService.analyze_query(user_id, query)
    return jsonify({"success": True, "analysis": analysis})
