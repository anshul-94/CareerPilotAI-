"""
CareerPilot AI — Chat Routes (AI Career Coach)
Real-time AI career coaching chat interface.
"""

from flask import Blueprint, render_template, request, session, jsonify, Response, stream_with_context
from backend.utils.decorators import login_required, api_login_required
from backend.services.ai_service import AIService
from backend.models.chat import ChatModel
from backend.prompts.career_prompt import get_suggested_questions

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/')
@login_required
def index():
    """AI Career Coach chat page."""
    user_id = session['user_id']
    
    # Get or create session
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = ChatModel.generate_session_id()
    
    # Get chat history for this session
    messages = ChatModel.get_session(session_id)
    
    # Get user's chat sessions
    sessions = ChatModel.get_user_sessions(user_id, module='career_coach')
    
    # Get suggested questions
    suggestions = get_suggested_questions('general')
    
    return render_template('chat/index.html',
                         session_id=session_id,
                         messages=messages,
                         sessions=sessions,
                         suggestions=suggestions)


@chat_bp.route('/send', methods=['POST'])
@api_login_required
def send():
    """API: Send a message to the AI Career Coach."""
    user_id = session['user_id']
    data = request.json
    
    message = data.get('message', '').strip()
    session_id = data.get('session_id', ChatModel.generate_session_id())
    
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400
    
    if len(message) > 5000:
        return jsonify({"success": False, "error": "Message too long"}), 400
    
    # Get user context from resume if available
    user_context = _get_user_context(user_id)
    
    result = AIService.chat(user_id, message, session_id, user_context)
    
    return jsonify({
        "success": True,
        "response": result["response"],
        "response_html": result.get("response_html", result["response"]),
        "session_id": result["session_id"],
        "suggested_questions": result.get("suggested_questions", []),
        "mock": result.get("mock", False)
    })


@chat_bp.route('/stream', methods=['POST'])
@api_login_required
def stream():
    """API: Stream a response from the AI Career Coach."""
    user_id = session['user_id']
    data = request.json
    
    message = data.get('message', '').strip()
    session_id = data.get('session_id', ChatModel.generate_session_id())
    
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400
    
    user_context = _get_user_context(user_id)
    
    def generate():
        for chunk in AIService.stream_chat(user_id, message, session_id, user_context):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@chat_bp.route('/history')
@api_login_required
def history():
    """API: Get chat session list."""
    user_id = session['user_id']
    sessions = ChatModel.get_user_sessions(user_id)
    return jsonify({"success": True, "sessions": sessions})


@chat_bp.route('/session/<session_id>')
@api_login_required
def get_session(session_id):
    """API: Get messages for a specific session."""
    messages = ChatModel.get_session(session_id)
    return jsonify({"success": True, "messages": messages})


@chat_bp.route('/session/<session_id>/delete', methods=['POST'])
@api_login_required
def delete_session(session_id):
    """API: Delete a chat session."""
    ChatModel.delete_session(session_id)
    return jsonify({"success": True, "message": "Session deleted"})


def _get_user_context(user_id: int) -> dict:
    """Build user context from profile and resume."""
    from backend.models.resume import ResumeModel
    from backend.utils.helpers import extract_skills_from_text
    
    context = {}
    resume = ResumeModel.get_primary(user_id)
    if resume and resume.get('raw_text'):
        context['skills'] = extract_skills_from_text(resume['raw_text'])
        context['has_resume'] = True
    
    from backend.models.project import SettingsModel
    settings = SettingsModel.get_by_user(user_id)
    if settings:
        context['target_role'] = settings.get('preferred_role', '')
        context['experience'] = settings.get('experience_level', '')
    
    return context
