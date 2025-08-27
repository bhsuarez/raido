import logging
import sys
from typing import Any, Dict
import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import settings

def configure_logging() -> None:
    """Configure structured logging with structlog and standard library logging"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    class StructlogFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
            super().add_fields(log_record, record, message_dict)
            
            # Add standard fields
            log_record['timestamp'] = self.formatTime(record)
            log_record['level'] = record.levelname
            log_record['logger'] = record.name
            
            # Add extra context if available
            if hasattr(record, 'request_id'):
                log_record['request_id'] = record.request_id
    
    # Set up handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructlogFormatter(
        fmt="%(timestamp)s %(level)s %(logger)s %(message)s"
    ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)