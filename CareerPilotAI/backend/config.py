"""
CareerPilot AI — Global Configuration
Centralized configuration management using environment variables.
"""
import os
from dotenv import load_dotenv

# Load the base .env or specific ones if passed
load_dotenv()

class BaseConfig:
    """Base configuration with generic properties."""
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
    
    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'careerpilot-dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')
    
    # AI Routing Logic (Determined by .env flags)
    USE_OLLAMA = os.getenv('USE_OLLAMA', 'False').lower() == 'true'
    USE_GROQ = os.getenv('USE_GROQ', 'False').lower() == 'true'
    
    @property
    def AI_PROVIDER(self):
        if self.USE_OLLAMA:
            return 'ollama'
        elif self.USE_GROQ:
            return 'groq'
        return 'ollama' # default fallback
    
    # Ollama settings
    OLLAMA_HOST = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
    
    # Groq settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    GROQ_TIMEOUT = int(os.getenv('GROQ_TIMEOUT', 60))
    
    # AI Retry / Resilience
    AI_MAX_RETRIES = int(os.getenv('AI_MAX_RETRIES', 3))
    
    # Tavily API
    TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')
    TAVILY_API_URL = os.getenv('TAVILY_API_URL', 'https://api.tavily.com/search')
    
    # Uploads & Cache
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE', 10485760)) / 1024 / 1024
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    CACHE_DIR = os.getenv('CACHE_DIR', 'backend/cache/data')
    CACHE_TTL = int(os.getenv('CACHE_TTL_SECONDS', 3600))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class DevelopmentConfig(BaseConfig):
    """Development-specific overrides."""
    DEBUG = True
    USE_OLLAMA = True
    USE_GROQ = False


class ProductionConfig(BaseConfig):
    """Production-specific overrides."""
    DEBUG = False
    USE_OLLAMA = False
    USE_GROQ = True


def get_config():
    """Factory to retrieve the appropriate config based on environment."""
    env = os.getenv('ENVIRONMENT', 'development').lower()
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()

# Expose a default instance for easy access
Config = get_config()
