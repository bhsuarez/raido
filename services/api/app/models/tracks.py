from sqlalchemy import Column, Integer, String, JSON, DateTime, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base
from .stations import station_tracks


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    artist = Column(String(500), nullable=False, index=True)
    album = Column(String(500), nullable=True, index=True)
    year = Column(Integer, nullable=True, index=True)
    genre = Column(String(100), nullable=True, index=True)
    duration_ms = Column(Integer, nullable=True)
    duration_sec = Column(Float, nullable=True)
    file_path = Column(String(1000), nullable=False, unique=True, index=True)
    file_size = Column(Integer, nullable=True)
    bitrate = Column(Integer, nullable=True)
    sample_rate = Column(Integer, nullable=True)

    # Audio features
    bpm = Column(Float, nullable=True)
    key = Column(Integer, nullable=True)  # 0=C, 1=C#, etc.
    mode = Column(Integer, nullable=True)  # 0=minor, 1=major
    energy = Column(Float, nullable=True)
    danceability = Column(Float, nullable=True)
    valence = Column(Float, nullable=True)
    acousticness = Column(Float, nullable=True)
    instrumentalness = Column(Float, nullable=True)
    liveness = Column(Float, nullable=True)
    loudness_db = Column(Float, nullable=True)

    # Metadata
    artwork_url = Column(String(1000), nullable=True)
    artwork_embedded = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)  # Additional metadata tags

    # External IDs
    isrc = Column(String(50), nullable=True, index=True)
    recording_mbid = Column(String(36), nullable=True, index=True)
    release_mbid = Column(String(36), nullable=True, index=True)
    spotify_id = Column(String(100), nullable=True, index=True)

    # Enrichment data
    facts = Column(JSON, nullable=True)  # Song facts from AI/APIs
    popularity_score = Column(Float, nullable=True)
    mood_tags = Column(JSON, nullable=True)  # Array of mood strings

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_played_at = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    play_count = Column(Integer, default=0, nullable=False)
    skip_count = Column(Integer, default=0, nullable=False)
    last_commentary_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    plays = relationship("Play", back_populates="track")
    stations = relationship(
        "Station", secondary=station_tracks, back_populates="tracks"
    )
    voicing_cache = relationship("TrackVoicingCache", back_populates="track", uselist=False)

    def __repr__(self):
        return f"<Track(id={self.id}, title='{self.title}', artist='{self.artist}')>"
