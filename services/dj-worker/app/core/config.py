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
    OLLAMA_BASE_URL: str = "http://192.168.1.204:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    
    
    # Kokoro TTS
    KOKORO_BASE_URL: str = "http://kokoro-tts:8880"
    KOKORO_VOICE: str = "am_onyx"
    KOKORO_SPEED: float = 1.0
    KOKORO_VOLUME: float = 1.0
    
    # Chatterbox TTS (via shim proxy)
    CHATTERBOX_BASE_URL: str = "http://chatterbox-shim:8000"
    CHATTERBOX_VOICE: str = "default"
    CHATTERBOX_EXAGGERATION: float = 1.0
    CHATTERBOX_CFG_WEIGHT: float = 0.5
    
    # DJ Configuration
    DJ_PROVIDER: str = "templates"  # openai, ollama, templates, disabled
    DJ_VOICE_PROVIDER: str = "kokoro"  # liquidsoap, openai_tts, kokoro, chatterbox
    DJ_MAX_SECONDS: int = 30
    DJ_COMMENTARY_INTERVAL: int = 1
    DJ_TONE: str = "energetic"
    DJ_PROFANITY_FILTER: bool = True

    # Station Configuration
    STATION_NAME: str = "main"  # Station identifier (main, christmas, etc.)
    LIQUIDSOAP_HOST: str = "liquidsoap"  # Liquidsoap hostname
    LIQUIDSOAP_PORT: int = 1234  # Liquidsoap telnet port

    # File Paths
    SHARED_DIR: str = "/shared"
    TTS_CACHE_DIR: str = "/shared/tts"
    LOGS_DIR: str = "/shared/logs"
    
    # Anthropic API (for Voicing Engine pre-rendering)
    ANTHROPIC_API_KEY: Optional[str] = None

    # API endpoints
    API_BASE_URL: str = "http://api:8000"
    
    # Worker settings
    # Poll a bit less aggressively and serialize jobs by default to avoid CPU spikes
    WORKER_POLL_INTERVAL: int = 10  # seconds
    MAX_CONCURRENT_JOBS: int = 1
    COMMENTARY_TIMEOUT: int = 60  # seconds
    TTS_TIMEOUT: int = 30  # seconds
    CHATTERBOX_TTS_TIMEOUT: int = 180  # seconds (3 minutes for Chatterbox)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
