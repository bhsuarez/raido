from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    LOG_LEVEL: str = "info"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://raido:password@db:5432/raido"
    
    # Security
    JWT_SECRET: str = "your-super-secret-jwt-signing-key-minimum-32-chars"
    SESSION_SECRET: str = "your-session-secret-key-here"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_TTS_VOICE: str = "onyx"
    OPENAI_TTS_MODEL: str = "tts-1"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.1"
    
    # XTTS
    XTTS_BASE_URL: Optional[str] = None
    XTTS_VOICE: str = "pirate_dj"
    
    # Kokoro TTS (API service)
    KOKORO_BASE_URL: str = "http://kokoro-tts:8880"
    
    # Chatterbox TTS
    CHATTERBOX_BASE_URL: str = "http://chatterbox-tts:4123"
    CHATTERBOX_VOICE: str = "default"
    CHATTERBOX_EXAGGERATION: float = 1.0
    CHATTERBOX_CFG_WEIGHT: float = 0.5
    
    # DJ Configuration
    DJ_PROVIDER: str = "openai"  # openai, ollama
    DJ_VOICE_PROVIDER: str = "openai_tts"  # liquidsoap, openai_tts, xtts, chatterbox
    DJ_MAX_SECONDS: int = 30
    DJ_COMMENTARY_INTERVAL: int = 1
    DJ_TONE: str = "energetic"
    DJ_PROFANITY_FILTER: bool = True
    STATION_NAME: str = "Raido Pirate Radio"
    
    # Stream Configuration
    ICECAST_PASSWORD: str = "hackme"
    ICECAST_HOST: str = "icecast"
    ICECAST_PORT: int = 8000
    LIQUIDSOAP_TELNET_PASSWORD: str = "liquidsoap"
    
    # External Services
    MUSICBRAINZ_USER_AGENT: str = "Raido/1.0.0 (https://raido.local)"
    LASTFM_API_KEY: Optional[str] = None
    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None
    
    # File Paths
    MUSIC_DIR: str = "/music"
    SHARED_DIR: str = "/shared"
    TTS_CACHE_DIR: str = "/shared/tts"
    LOGS_DIR: str = "/shared/logs"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
