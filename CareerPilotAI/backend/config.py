"""
CareerPilot AI — Global Configuration
Centralized configuration management using environment variables.

AI Provider modes:
    AI_PROVIDER=ollama  →  Local Ollama (development)
    AI_PROVIDER=groq    →  Groq cloud API (production / Render)
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

    # ── AI Provider Selection ─────────────────────────────────
    # "ollama" = local development, "groq" = production/Render
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'ollama').strip().lower()

    # Ollama (local dev)
    OLLAMA_HOST  = os.getenv('OLLAMA_HOST',  'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')

    # Groq (production)
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL   = os.getenv('GROQ_MODEL',   'llama-3.3-70b-versatile')
    GROQ_TIMEOUT = int(os.getenv('GROQ_TIMEOUT', 60))

    # AI Retry / Resilience
    AI_MAX_RETRIES = int(os.getenv('AI_MAX_RETRIES', 3))

    # Tavily API
    TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')
    TAVILY_API_URL = os.getenv('TAVILY_API_URL', 'https://api.tavily.com/search')

    # Uploads & Cache
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', 10))
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    CACHE_DIR = os.getenv('CACHE_DIR', 'backend/cache/data')
    CACHE_TTL = int(os.getenv('CACHE_TTL_SECONDS', 3600))
