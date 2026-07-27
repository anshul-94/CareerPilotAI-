"""
CareerPilot AI — Problem Solving Controller Routes
Exposes views and REST APIs for compiler code submission and learning analytics.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import json
from backend.utils.decorators import login_required, api_login_required
from backend.services.problem_service import ProblemService
from backend.database.db import execute_insert, execute_update, execute_one

problem_solving_bp = Blueprint('problem_solving', __name__, url_prefix='/problem_solving')

@problem_solving_bp.route('/')
@login_required
def index():
    """Render the problem listing directory."""
    difficulty = request.args.get('difficulty')
    topic = request.args.get('topic')
    company = request.args.get('company')
    
    problems = ProblemService.get_problems(difficulty, topic, company)
    return render_template(
        'problem_solving/problems.html',
        problems=problems,
        current_difficulty=difficulty,
        current_topic=topic,
        current_company=company
    )

@problem_solving_bp.route('/dashboard')
@login_required
def dashboard():
    """Render the learning analytics dashboard."""
    user_id = session.get('user_id')
    stats = ProblemService.get_dashboard_stats(user_id)
    return render_template('problem_solving/dashboard.html', stats=stats)

@problem_solving_bp.route('/problem/<int:problem_id>')
@login_required
def problem_detail(problem_id: int):
    """Render Monaco IDE code editor for a problem."""
    user_id = session.get('user_id')
    problem = ProblemService.get_problem_by_id(problem_id)
    if not problem:
        return redirect(url_for('problem_solving.index'))
        
    hints_used = ProblemService.get_hints_used(user_id, problem_id)
    
    # Retrieve previous submissions
    submissions = execute_one(
        "SELECT * FROM problem_submissions WHERE user_id = ? AND problem_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id, problem_id)
    )
    
    return render_template(
        'problem_solving/editor.html',
        problem=problem,
        hints_used=hints_used,
        last_submission=submissions
    )

class JudgeResult:
    @staticmethod
    def validate(result: dict) -> dict:
        required_keys = ["status", "success", "passed", "total", "runtime", "memory"]
        for key in required_keys:
            if key not in result:
                return {
                    "success": False,
                    "status": "Internal Judge Error",
                    "error": f"Judge did not return required key: {key}"
                }
        return result

@problem_solving_bp.errorhandler(Exception)
def handle_blueprint_exception(e):
    from backend.utils.logger import app_logger
    import traceback
    app_logger.error(f"[Blueprint Error] {str(e)}\n{traceback.format_exc()}")
    return jsonify({
        "success": False,
        "status": "Internal Error",
        "error": str(e)
    }), 200

@problem_solving_bp.route('/api/run/<int:problem_id>', methods=['POST'])
@api_login_required
def run_code(problem_id: int):
    """REST API endpoint to compile and run code against public test cases."""
    from backend.utils.logger import app_logger
    app_logger.info(f"[IDE Run] Request received for Problem ID: {problem_id}")
    try:
        data = request.get_json() or {}
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        if not code:
            return jsonify({"success": False, "status": "Error", "message": "Code is required"}), 400
            
        raw_result = ProblemService.execute_code(problem_id, code, language)
        result = JudgeResult.validate(raw_result)
        
        if result.get("status") == "Internal Judge Error":
            return jsonify(result)
            
        return jsonify(result)
    except Exception as e:
        import traceback
        app_logger.error(f"[IDE Run] Internal error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "status": "Internal Error", "error": str(e)})

@problem_solving_bp.route('/api/submit/<int:problem_id>', methods=['POST'])
@api_login_required
def submit_code(problem_id: int):
    """REST API endpoint to submit code, save it, and trigger AI analysis."""
    from backend.utils.logger import app_logger
    
    app_logger.info(f"[IDE Submit] Request received for Problem ID: {problem_id}")
    
    try:
        user_id = session.get('user_id')
        data = request.get_json() or {}
        code = data.get('code', '')
        language = data.get('language', 'python')
        metrics = data.get('metrics', {})
        
        if not code:
            app_logger.warning(f"[IDE Submit] Empty code payload submitted.")
            return jsonify({"success": False, "status": "Error", "message": "Code is required"}), 400
            
        app_logger.info(f"[IDE Submit] Compiler started. Code size: {len(code)} chars. Language: {language}")
        
        # 1. Run all tests
        app_logger.info(f"[IDE Submit] Execution started...")
        raw_result = ProblemService.execute_code(problem_id, code, language)
        result = JudgeResult.validate(raw_result)
        app_logger.info(f"[IDE Submit] Execution finished. Judge finished with status: {result.get('status')}")
        
        if result.get("status") == "Internal Judge Error":
            return jsonify(result)
            
        # 2. Save submission to database
        app_logger.info(f"[IDE Submit] Database save started...")
        submission_id = execute_insert("""
            INSERT INTO problem_submissions (user_id, problem_id, code, language, status, execution_time, memory, coding_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, problem_id, code, language, result["status"],
            result.get("runtime", 0), result.get("memory", 1024), json.dumps(metrics)
        ))
        
        # Update stats
        if result["status"] == "Accepted":
            execute_update("""
                INSERT INTO user_problem_analytics (user_id, streak, last_submission_at)
                VALUES (?, 1, date('now'))
                ON CONFLICT(user_id) DO UPDATE SET 
                    streak = CASE 
                        WHEN last_submission_at = date('now', '-1 day') THEN streak + 1
                        WHEN last_submission_at = date('now') THEN streak
                        ELSE 1
                    END,
                    last_submission_at = date('now')
            """, (user_id,))
            
        # 3. Analyze solution via AI mentor ONLY if Accepted
        ai_feedback = None
        if result["status"] == "Accepted":
            app_logger.info(f"[IDE Submit] Invoking AI Code Review for Accepted solution...")
            ai_feedback = ProblemService.analyze_submission_ai(user_id, problem_id, code, language, submission_id)
            app_logger.info(f"[IDE Submit] AI review completed successfully.")
        else:
            app_logger.info(f"[IDE Submit] Generating AI feedback for failure status {result['status']}...")
            error_message = result.get("stderr") or result.get("compile_error") or result.get("runtime_error") or result.get("details", "")
            ai_feedback = ProblemService.analyze_error_ai(
                user_id=user_id,
                problem_id=problem_id,
                code=code,
                language=language,
                status=result["status"],
                error_message=error_message,
                expected_output=result.get("expected"),
                actual_output=result.get("actual")
            )
            app_logger.info(f"[IDE Submit] AI error feedback generated successfully.")
        
        result["ai_feedback"] = ai_feedback
        result["ai_metrics"] = ai_feedback or {}
        app_logger.info(f"[IDE Submit] JSON returned to client.")
        return jsonify(result)
        
    except Exception as e:
        import traceback
        app_logger.error(f"[IDE Submit] Internal error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "status": "Internal Error", "error": str(e)})

@problem_solving_bp.route('/api/unlock_hint/<int:problem_id>', methods=['POST'])
@api_login_required
def unlock_hint(problem_id: int):
    """Register hint usage to calculate score penalties."""
    try:
        user_id = session.get('user_id')
        data = request.get_json() or {}
        hint_index = data.get('hint_index')
        
        if hint_index is None:
            return jsonify({"success": False, "status": "Error", "message": "Hint index is required"}), 400
            
        ProblemService.unlock_hint(user_id, problem_id, int(hint_index))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "status": "Internal Error", "error": str(e)})

@problem_solving_bp.route('/api/dashboard', methods=['GET'])
@api_login_required
def get_dashboard_api():
    """REST API endpoint to return full dynamic coding metrics and analytics."""
    try:
        user_id = session.get('user_id')
        stats = ProblemService.get_dashboard_stats(user_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"success": False, "status": "Internal Error", "error": str(e)})
