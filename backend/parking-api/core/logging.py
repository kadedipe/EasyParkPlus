"""
Logging configuration for the application.
"""

import logging
import sys
from typing import Optional
from loguru import logger
import json
from datetime import datetime

from .config import settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging and redirect to loguru.
    """
    
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    """
    Configure logging for the application.
    """
    # Remove default handlers
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL.upper(),
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler for production
    if settings.ENVIRONMENT == "production":
        logger.add(
            "logs/app.log",
            rotation="500 MB",
            retention="30 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="INFO",
            backtrace=False,
            diagnose=False
        )
        
        # Add JSON format for structured logging
        logger.add(
            "logs/app.json",
            rotation="500 MB",
            retention="30 days",
            compression="zip",
            format=lambda record: json.dumps({
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
                "message": record["message"],
                "exception": record["exception"]
            }),
            level="INFO"
        )
    
    # Intercept all standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set logs for specific libraries
    for log_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "sqlalchemy"]:
        logging_logger = logging.getLogger(log_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
    
    logger.info("Logging configured successfully")