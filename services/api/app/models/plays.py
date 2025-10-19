from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base

class Play(Base):
    __tablename__ = "plays"
    
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False, index=True)
    station_identifier = Column(String(50), nullable=True, index=True)
    
    # Play session info
    liquidsoap_id = Column(String(100), nullable=True, index=True)  # Liquidsoap track ID
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    elapsed_ms = Column(Integer, nullable=True)  # How much was actually played
    
    # Play context
    play_position = Column(Integer, nullable=True)  # Position in playlist/queue
    crossfade_duration = Column(Integer, nullable=True)  # Crossfade duration in ms
    was_skipped = Column(Boolean, default=False, nullable=False)
    skip_reason = Column(String(100), nullable=True)  # user, error, system, etc.
    
    # Commentary association
    triggered_commentary = Column(Boolean, default=False, nullable=False)
    commentary_before = Column(Boolean, default=False, nullable=False)  # Commentary before this track
    commentary_after = Column(Boolean, default=False, nullable=False)   # Commentary after this track
    
    # Source information
    source_type = Column(String(50), default="playlist", nullable=False)  # playlist, request, fallback
    user_agent = Column(String(500), nullable=True)  # If from a request
    client_ip = Column(String(50), nullable=True)     # If from a request
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    track = relationship("Track", back_populates="plays")
    commentaries = relationship("Commentary", back_populates="play")
    
    def __repr__(self):
        return f"<Play(id={self.id}, track_id={self.track_id}, station='{self.station_identifier}', started_at={self.started_at})>"
