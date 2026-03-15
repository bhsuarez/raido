from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ListenerSession(Base):
    __tablename__ = "listener_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    station = Column(String(100), nullable=False, default="main")

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_heartbeat_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)  # written on session close

    # Location
    ip_address = Column(String(45), nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    country_code = Column(String(2), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Device metadata
    user_agent = Column(Text, nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    device_type = Column(String(20), nullable=True)  # mobile, tablet, desktop

    user = relationship("User", back_populates=None)

    def __repr__(self):
        return f"<ListenerSession(id={self.id}, user_id={self.user_id}, station='{self.station}')>"
