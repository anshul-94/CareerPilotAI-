"""
CareerPilot AI — Global Configuration
Centralized configuration management using environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'careerpilot-dev-secret-key')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')

    # Ollama Local AI
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')

    # Tavily API
    TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')
    TAVILY_API_URL = os.getenv('TAVILY_API_URL', 'https://api.tavily.com/search')

    # Uploads & Cache
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', 10))
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    CACHE_DIR = os.getenv('CACHE_DIR', 'backend/cache/data')
    CACHE_TTL = int(os.getenv('CACHE_TTL_SECONDS', 3600))
