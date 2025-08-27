from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"
    GENERATING_TEXT = "generating_text"
    GENERATING_AUDIO = "generating_audio"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class CommentaryJob:
    """Represents a commentary generation job"""
    track_info: Dict[str, Any]
    play_info: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Job status
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now())
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Generated content
    commentary_text: Optional[str] = None
    audio_file: Optional[str] = None
    audio_duration_ms: Optional[int] = None
    
    # Error handling
    error: Optional[str] = None
    retry_count: int = 0
    
    @property
    def is_complete(self) -> bool:
        return self.status in [JobStatus.READY, JobStatus.FAILED, JobStatus.CANCELLED]
    
    @property
    def processing_time_ms(self) -> Optional[int]:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None