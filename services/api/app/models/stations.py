from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base

# Association table linking stations and tracks
station_tracks = Table(
    "station_tracks",
    Base.metadata,
    Column("station_id", Integer, ForeignKey("stations.id"), primary_key=True),
    Column("track_id", Integer, ForeignKey("tracks.id"), primary_key=True),
)


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "main", "christmas"
    name = Column(String(200), nullable=False)  # Display name
    description = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True, index=True)
    dj_persona = Column(String(100), nullable=True)
    artwork_url = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    tracks = relationship("Track", secondary=station_tracks, back_populates="stations")
