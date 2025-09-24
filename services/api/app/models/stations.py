from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship

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
    name = Column(String(200), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True, index=True)
    dj_persona = Column(String(100), nullable=True)
    artwork_url = Column(String(1000), nullable=True)
    stream_mount = Column(String(200), unique=True, nullable=False)
    stream_name = Column(String(200), nullable=True)

    tracks = relationship("Track", secondary=station_tracks, back_populates="stations")
    plays = relationship("Play", back_populates="station")
