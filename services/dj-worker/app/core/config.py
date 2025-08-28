from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    LOG_LEVEL: str = "info"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://raido:password@db:5432/raido"
    
    # Redis for task queue
    REDIS_URL: str = "redis://redis:6379/0"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_TTS_VOICE: str = "onyx"
    OPENAI_TTS_MODEL: str = "tts-1"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    
    # XTTS
    XTTS_BASE_URL: Optional[str] = None
    XTTS_VOICE: str = "pirate_dj"
    
    # Kokoro TTS
    KOKORO_BASE_URL: str = "http://localhost:8090"
    KOKORO_VOICE: str = "af_bella"
    KOKORO_SPEED: float = 1.0
    
    # DJ Configuration
    DJ_PROVIDER: str = "templates"  # openai, ollama, templates, disabled
    DJ_VOICE_PROVIDER: str = "kokoro"  # liquidsoap, openai_tts, kokoro, xtts
    DJ_MAX_SECONDS: int = 30
    DJ_COMMENTARY_INTERVAL: int = 1
    DJ_TONE: str = "energetic"
    DJ_PROFANITY_FILTER: bool = True
    STATION_NAME: str = "Raido Pirate Radio"
    
    # File Paths
    SHARED_DIR: str = "/shared"
    TTS_CACHE_DIR: str = "/shared/tts"
    LOGS_DIR: str = "/shared/logs"
    
    # API endpoints
    API_BASE_URL: str = "http://api:8000"
    
    # Worker settings
    WORKER_POLL_INTERVAL: int = 5  # seconds
    MAX_CONCURRENT_JOBS: int = 3
    COMMENTARY_TIMEOUT: int = 60  # seconds
    TTS_TIMEOUT: int = 30  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()