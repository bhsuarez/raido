from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import enum

from app.core.database import Base

class RequestType(enum.Enum):
    MUSIC = "music"
    COMMENTARY = "commentary"
    JINGLE = "jingle"
    SILENCE = "silence"

class RequestStatus(enum.Enum):
    PENDING = "pending"
    PLAYING = "playing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RequestQueue(Base):
    __tablename__ = "request_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Request details
    request_type = Column(Enum(RequestType), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    
    # Metadata
    title = Column(String)
    artist = Column(String)  
    album = Column(String)
    duration_sec = Column(Float)
    
    # Queue management
    queue_order = Column(Integer, nullable=False, index=True)  # Order in queue
    priority = Column(Integer, default=0, index=True)  # Higher = more important
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, index=True)
    
    # Timing
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    requested_at = Column(DateTime)  # When Liquidsoap should request this
    started_at = Column(DateTime)   # When playback actually started
    completed_at = Column(DateTime) # When playback finished
    
    # Additional data
    liquidsoap_request_id = Column(Integer)
    extra_data = Column(Text)  # JSON metadata
    notes = Column(String)
    
    def __repr__(self):
        return f"<RequestQueue(id={self.id}, type={self.request_type}, title='{self.title}', status={self.status})>"