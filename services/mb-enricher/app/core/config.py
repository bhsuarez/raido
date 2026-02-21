from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://raido:password@db:5432/raido"
    LOG_LEVEL: str = "info"

    # MusicBrainz rate limit: 1 request/second per their ToS
    MB_REQUEST_INTERVAL: float = 1.1  # seconds between requests
    MB_SEARCH_LIMIT: int = 5          # max candidates to fetch per track
    MB_BATCH_SIZE: int = 10           # tracks to process per batch
    MB_USER_AGENT: str = "Raido/1.0.0 (raido@bhsuarez.com)"

    # How long to pause between batches (seconds)
    BATCH_PAUSE: float = 5.0
    # Poll interval when no work is available (seconds)
    IDLE_PAUSE: float = 60.0

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
