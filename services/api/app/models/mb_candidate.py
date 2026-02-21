"""MusicBrainz candidate matches awaiting user review."""
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CandidateStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    skipped = "skipped"


class MBCandidate(Base):
    __tablename__ = "mb_candidates"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(Enum(CandidateStatus), default=CandidateStatus.pending, nullable=False, index=True)
    score = Column(Float, nullable=True)  # MusicBrainz match confidence 0–100

    # Proposed metadata values
    mb_recording_id = Column(String(36), nullable=True)
    mb_release_id = Column(String(36), nullable=True)
    mb_artist_id = Column(String(36), nullable=True)

    proposed_title = Column(String(500), nullable=True)
    proposed_artist = Column(String(500), nullable=True)
    proposed_album = Column(String(500), nullable=True)
    proposed_year = Column(Integer, nullable=True)
    proposed_genre = Column(String(100), nullable=True)
    proposed_isrc = Column(String(50), nullable=True)
    proposed_country = Column(String(10), nullable=True)
    proposed_label = Column(String(255), nullable=True)
    proposed_artwork_url = Column(String(1000), nullable=True)

    # Full API response for reference
    mb_raw_response = Column(JSON, nullable=True)

    # Review tracking
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    track = relationship("Track", backref="mb_candidates")

    def __repr__(self):
        return f"<MBCandidate(id={self.id}, track_id={self.track_id}, status={self.status}, score={self.score})>"
