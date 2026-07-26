"""
CareerPilot AI — Centralized Logging System
Manages distinct log files for application, errors, AI requests, and database.
"""
import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """Function to setup as many loggers as you want."""
    
    # Ensure logs directory exists
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Rotating file handler (max 5MB per file, keep 3 backups)
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # For plain console output (so we can print custom panels without the timestamp prefix)
    class PlainConsoleHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                # Strip out the '2026-07-26 23:15:10 - app - INFO - ' prefix for console display
                # We'll just print the raw message to console for the beautiful panels.
                print(record.getMessage())
            except Exception:
                self.handleError(record)

    console_handler = PlainConsoleHandler()
    
    # To prevent adding handlers multiple times in development reloaders
    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(console_handler)

    return logger

# Mute noisy Werkzeug access logs
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

# Initialize standard loggers
app_logger = setup_logger('app', 'logs/app.log')
error_logger = setup_logger('error', 'logs/errors.log', level=logging.ERROR)
ai_logger = setup_logger('ai', 'logs/ai.log')
db_logger = setup_logger('db', 'logs/database.log')
jobs_logger = setup_logger('jobs', 'logs/jobs.log')
scheduler_logger = setup_logger('scheduler', 'logs/scheduler.log')
security_logger = setup_logger('security', 'logs/security.log')
