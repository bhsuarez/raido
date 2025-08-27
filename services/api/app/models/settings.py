from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, Float
from sqlalchemy.sql import func

from app.core.database import Base

class Setting(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string", nullable=False)  # string, int, float, bool, json
    category = Column(String(50), nullable=False, index=True)  # dj, stream, ui, security, etc.
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False)  # Sensitive values
    
    # Validation
    min_value = Column(Float, nullable=True)  # For numeric types
    max_value = Column(Float, nullable=True)  # For numeric types
    allowed_values = Column(JSON, nullable=True)  # For enum-like settings
    validation_regex = Column(String(500), nullable=True)  # For string validation
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(100), nullable=True)  # User who last updated
    
    def __repr__(self):
        return f"<Setting(key='{self.key}', category='{self.category}')>"