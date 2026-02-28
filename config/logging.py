"""Logging configuration for the application."""

import os
import logging
import logging.config
import json
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger

from . import config


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['environment'] = config.ENV
        log_record['app_version'] = config.APP_VERSION
        
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id


def setup_logging():
    """Setup logging configuration."""
    
    # Create logs directory if it doesn't exist
    if config.LOGS_DIR:
        log_dir = Path(config.LOGS_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Logging configuration
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': config.LOG_FORMAT,
                'datefmt': config.LOG_DATE_FORMAT,
            },
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(message)s %(levelname)s %(name)s %(asctime)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': config.LOG_LEVEL,
                'formatter': 'json' if config.LOG_JSON_FORMAT else 'standard',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console'],
                'level': config.LOG_LEVEL,
                'propagate': True,
            },
            'sqlalchemy.engine': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'urllib3': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'celery': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
        }
    }
    
    # Add file handler if logs directory exists
    if config.LOGS_DIR:
        log_config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': config.LOG_LEVEL,
            'formatter': 'json' if config.LOG_JSON_FORMAT else 'standard',
            'filename': os.path.join(config.LOGS_DIR, 'app.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        }
        log_config['loggers']['']['handlers'].append('file')
    
    # Apply configuration
    logging.config.dictConfig(log_config)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for environment: {config.ENV}")
    
    return logger


class RequestIdFilter(logging.Filter):
    """Add request ID to log records."""
    
    def __init__(self, request_id: str = None):
        super().__init__()
        self.request_id = request_id
    
    def filter(self, record):
        record.request_id = self.request_id
        return True


class UserIdFilter(logging.Filter):
    """Add user ID to log records."""
    
    def __init__(self, user_id: int = None):
        super().__init__()
        self.user_id = user_id
    
    def filter(self, record):
        record.user_id = self.user_id
        return True


# Initialize logging
logger = setup_logging()