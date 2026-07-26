"""
CareerPilot AI — Chat Routes (AI Career Coach)
Real-time AI career coaching chat interface.
"""

from flask import Blueprint, render_template, request, session, jsonify, Response, stream_with_context
from backend.utils.decorators import login_required, api_login_required
from backend.services.ai_service import AIService
from backend.models.chat import ChatModel, ChatSessionModel
from backend.prompts.career_prompt import get_suggested_questions
from backend.utils.logger import app_logger
import threading

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
    
    # Get user's active chat sessions
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
    
    # Before chat, check message count to see if we need title generation
    messages_before = ChatModel.get_session(session_id)
    is_first_message = len(messages_before) == 0

    result = AIService.chat(user_id, message, session_id, user_context)
    
    if is_first_message:
        # Generate title in background
        threading.Thread(target=_generate_and_save_title, args=(session_id, message)).start()
    
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
    
    messages_before = ChatModel.get_session(session_id)
    is_first_message = len(messages_before) == 0
    
    if is_first_message:
        threading.Thread(target=_generate_and_save_title, args=(session_id, message)).start()
    
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


def _generate_and_save_title(session_id: str, first_message: str):
    """Generate a 3-5 word title using Ollama for a new chat session."""
    try:
        from backend.services.ollama_service import OllamaService
        prompt = f"Generate a short 3 to 5 word title for a conversation that starts with this message: '{first_message}'. Do not include quotes or extra text. Just the title."
        title = OllamaService.generate_completion(prompt)
        title = title.replace('"', '').replace("'", '').strip()
        if title:
            ChatSessionModel.update_title(session_id, title)
    except Exception as e:
        app_logger.error(f"Error generating title for session {session_id}: {e}")


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
    app_logger.info(f"Attempting to delete session {session_id}")
    try:
        ChatSessionModel.delete(session_id)
        app_logger.info(f"Successfully deleted session {session_id}")
        return jsonify({"success": True, "message": "Session deleted"})
    except Exception as e:
        app_logger.error(f"Failed to delete session {session_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@chat_bp.route('/session/<session_id>/rename', methods=['POST'])
@api_login_required
def rename_session(session_id):
    """API: Rename a chat session."""
    data = request.json
    title = data.get('title', 'New Conversation').strip()
    ChatSessionModel.update_title(session_id, title)
    return jsonify({"success": True, "title": title})


@chat_bp.route('/session/<session_id>/pin', methods=['POST'])
@api_login_required
def pin_session(session_id):
    """API: Pin/Unpin a chat session."""
    data = request.json
    is_pinned = data.get('is_pinned', False)
    ChatSessionModel.toggle_pin(session_id, is_pinned)
    return jsonify({"success": True, "is_pinned": is_pinned})


@chat_bp.route('/session/<session_id>/archive', methods=['POST'])
@api_login_required
def archive_session(session_id):
    """API: Archive/Unarchive a chat session."""
    data = request.json
    is_archived = data.get('is_archived', False)
    ChatSessionModel.toggle_archive(session_id, is_archived)
    return jsonify({"success": True, "is_archived": is_archived})


@chat_bp.route('/session/<session_id>/duplicate', methods=['POST'])
@api_login_required
def duplicate_session(session_id):
    """API: Duplicate a chat session."""
    user_id = session['user_id']
    original_session = ChatSessionModel.get(session_id)
    if not original_session:
        return jsonify({"success": False, "error": "Session not found"}), 404
        
    messages = ChatModel.get_session(session_id)
    
    new_session_id = ChatModel.generate_session_id()
    new_title = original_session.get('title', 'Conversation') + ' (Copy)'
    ChatSessionModel.create(new_session_id, user_id, title=new_title)
    
    for msg in messages:
        # We manually insert to avoid updating updated_at for each message unnecessarily
        ChatModel.create(user_id, new_session_id, msg['role'], msg['message'], msg['module'])
        
    return jsonify({"success": True, "new_session_id": new_session_id})


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
