from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TrackVoicingCache(Base):
    """Pre-rendered DJ script and audio cache for a track."""
    __tablename__ = "track_voicing_cache"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Content
    genre_persona = Column(String(100), nullable=True)   # persona name used for generation
    script_text = Column(Text, nullable=True)             # Claude-generated DJ script
    audio_filename = Column(String(500), nullable=True)   # filename in /shared/tts/voicing/
    audio_duration_sec = Column(Float, nullable=True)

    # Generation metadata
    provider = Column(String(50), nullable=True)          # anthropic
    model = Column(String(100), nullable=True)            # claude-3-5-haiku-20241022
    voice_provider = Column(String(50), nullable=True)    # chatterbox, kokoro
    voice_id = Column(String(100), nullable=True)

    # Cost tracking
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)

    # Status
    status = Column(String(50), default="pending", nullable=False)  # pending/generating/ready/failed
    error_message = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    track = relationship("Track", back_populates="voicing_cache")

    def __repr__(self):
        return f"<TrackVoicingCache(id={self.id}, track_id={self.track_id}, status='{self.status}')>"


class VoicingBudget(Base):
    """Daily API spend tracking for the voicing engine."""
    __tablename__ = "voicing_budget"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    total_input_tokens = Column(Integer, default=0, nullable=False)
    total_output_tokens = Column(Integer, default=0, nullable=False)
    total_cost_usd = Column(Float, default=0.0, nullable=False)
    requests_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<VoicingBudget(date={self.date}, cost=${self.total_cost_usd:.4f})>"


class VoicingWorkerConfig(Base):
    """Singleton config/status for the voicing background worker."""
    __tablename__ = "voicing_worker_config"

    id = Column(Integer, primary_key=True, index=True)  # always 1

    # Control
    is_running = Column(Boolean, default=False, nullable=False)
    dry_run_mode = Column(Boolean, default=False, nullable=False)

    # Budget limits
    daily_spend_limit_usd = Column(Float, default=1.00, nullable=False)
    total_project_limit_usd = Column(Float, default=10.00, nullable=False)
    rate_limit_per_minute = Column(Integer, default=10, nullable=False)

    # Progress
    total_tracks_estimated = Column(Integer, nullable=True)
    voiced_tracks_count = Column(Integer, default=0, nullable=False)
    total_spent_usd = Column(Float, default=0.0, nullable=False)
    last_processed_track_id = Column(Integer, nullable=True)
    paused_reason = Column(Text, nullable=True)

    # Dry-run results
    dry_run_projected_cost_usd = Column(Float, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<VoicingWorkerConfig(running={self.is_running}, spent=${self.total_spent_usd:.4f})>"
