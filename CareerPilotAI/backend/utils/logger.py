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
    
    # To prevent adding handlers multiple times in development reloaders
    if not logger.handlers:
        logger.addHandler(handler)

    return logger

# Initialize standard loggers
app_logger = setup_logger('app', 'logs/app.log')
error_logger = setup_logger('error', 'logs/error.log', level=logging.ERROR)
ai_logger = setup_logger('ai', 'logs/ollama.log')
db_logger = setup_logger('db', 'logs/database.log')
