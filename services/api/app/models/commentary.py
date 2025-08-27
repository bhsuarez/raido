from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base

class Commentary(Base):
    __tablename__ = "commentary"
    
    id = Column(Integer, primary_key=True, index=True)
    play_id = Column(Integer, ForeignKey("plays.id"), nullable=True, index=True)  # Associated play
    
    # Content
    text = Column(Text, nullable=False)  # Raw text content
    ssml = Column(Text, nullable=True)   # SSML version for TTS
    audio_url = Column(String(1000), nullable=True)  # Path to generated audio file
    transcript = Column(Text, nullable=True)  # Clean transcript for display
    
    # Generation metadata
    provider = Column(String(50), nullable=False)  # openai, ollama, etc.
    model = Column(String(100), nullable=True)     # Specific model used
    voice_provider = Column(String(50), nullable=True)  # TTS provider
    voice_id = Column(String(100), nullable=True)       # Voice/style used
    
    # Timing
    duration_ms = Column(Integer, nullable=True)    # Audio duration
    generation_time_ms = Column(Integer, nullable=True)  # Time to generate
    tts_time_ms = Column(Integer, nullable=True)    # Time for TTS
    
    # Context used for generation
    context_data = Column(JSON, nullable=True)  # Track info, history, etc.
    prompt_template = Column(String(100), nullable=True)  # Which template was used
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True)  # Generation confidence
    content_flags = Column(JSON, nullable=True)     # Content moderation flags
    user_rating = Column(Integer, nullable=True)    # User feedback (1-5)
    
    # Status
    status = Column(String(50), default="pending", nullable=False)  # pending, generating, ready, failed, archived
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Broadcasting
    broadcasted_at = Column(DateTime(timezone=True), nullable=True)
    play_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Cache expiration
    
    # Relationships
    play = relationship("Play", back_populates="commentaries")
    
    def __repr__(self):
        return f"<Commentary(id={self.id}, provider='{self.provider}', status='{self.status}')>"