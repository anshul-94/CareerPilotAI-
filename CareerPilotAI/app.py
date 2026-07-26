"""
CareerPilot AI — Main Application
Flask application factory with blueprint registration, error handlers, and initialization.
"""

import os
import socket
from flask import Flask, render_template, session
from werkzeug.exceptions import HTTPException
from backend.config import Config

def create_app() -> Flask:
    """Create and configure the Flask application."""
    
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    
    # ── Configuration ─────────────────────────────────────────────
    app.secret_key = Config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    
    # ── Database Initialization ───────────────────────────────────
    from backend.database.schema import init_db
    db_path = Config.DATABASE_PATH
    if not os.path.exists(db_path):
        init_db(db_path)
        
    # Run dynamic migrations
    from backend.models.career_profile import migrate_career_profile_table
    from backend.models.resume_version import migrate_resume_versions_table
    from backend.models.job_notification import migrate_notification_tables
    from backend.models.chat import migrate_chat_sessions_table
    
    migrate_career_profile_table()
    migrate_resume_versions_table()
    migrate_notification_tables()
    migrate_chat_sessions_table()
    
    # ── Register Blueprints ───────────────────────────────────────
    from backend.routes.auth import auth_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.resume import resume_bp
    from backend.routes.chat import chat_bp
    from backend.routes.learning import learning_bp
    from backend.routes.interview import interview_bp
    from backend.routes.jobs import jobs_bp
    from backend.routes.code_review import code_bp
    from backend.routes.projects import projects_bp
    from backend.routes.profile import profile_bp
    from backend.routes.admin import admin_bp
    from backend.routes.notifications import notifications_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(code_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)
    
    # ── Landing Page Route ────────────────────────────────────────
    @app.route('/')
    def home():
        """Landing page."""
        if 'user_id' in session:
            return render_template('index.html', logged_in=True)
        return render_template('index.html', logged_in=False)
    
    # ── Context Processors ────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates."""
        return {
            'app_name': 'CareerPilot AI',
            'app_tagline': 'Learn. Build. Get Hired.',
            'current_user': {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'full_name': session.get('full_name'),
                'avatar_url': session.get('avatar_url', '/static/images/default-avatar.png'),
                'role': session.get('user_role', 'user'),
                'is_authenticated': 'user_id' in session,
                'is_admin': session.get('user_role') == 'admin'
            }
        }
    
    # ── Error Handlers ────────────────────────────────────────────
    from backend.utils.logger import error_logger
    
    @app.errorhandler(403)
    def forbidden(e):
        error_logger.warning(f"403 Forbidden: {e}")
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        error_logger.warning(f"404 Not Found: {e}")
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        import traceback
        traceback.print_exc()
        error_logger.error(f"500 Server Error: {e}", exc_info=True)
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return e
        # Log unexpected exceptions
        error_logger.error(f"Unhandled Exception: {e}", exc_info=True)
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def too_large(e):
        from flask import flash, redirect, url_for
        error_logger.warning(f"413 File Too Large: {e}")
        flash("File is too large. Maximum size is 10MB.", "danger")
        return redirect(url_for('resume.upload'))
    
    return app


# ── Utilities ────────────────────────────────────────────────────
def get_available_port(start_port: int, max_port: int = 65535) -> int:
    """
    Finds the next available open port starting from `start_port`.
    Cross-platform solution using the standard `socket` library to detect free ports.
    """
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # SO_REUSEADDR prevents "Address already in use" for sockets in TIME_WAIT
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue # Port is in use, try the next one
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}.")


# ── Application Entry Point ──────────────────────────────────────

app = create_app()

if __name__ == '__main__':
    # 1. Use environment variable PORT if exists, otherwise fallback to FLASK_PORT or 5000
    preferred_port = Config.PORT
    debug = Config.DEBUG
    
    # 2. Handle Werkzeug reloader (child process) correctly
    is_reloader = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    
    if not is_reloader:
        # Parent process: Find next free port automatically without crashing
        port = get_available_port(preferred_port)
        
        # Save the found port so the child process uses the same one
        os.environ['PORT'] = str(port)
        
        # 3. Print the beautiful startup banner
        url_line = f"   Running on: http://localhost:{port}"
        debug_line = f"   Debug mode: {'ON' if debug else 'OFF'}"
        print(f"""
╔══════════════════════════════════════════════════╗
║           🚀 CareerPilot AI                      ║
║           AI-Powered Career Intelligence         ║
║                                                  ║
║{url_line:<50}║
║{debug_line:<50}║
╚══════════════════════════════════════════════════╝
        """)
    else:
        # Child process: Use the port provided by the parent
        port = int(os.environ.get('PORT', preferred_port))
    
    # Suppress default Flask banner if we already printed ours
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.run(host='0.0.0.0', port=port, debug=debug)
