"""Structured logging configuration for the image processing service."""

import structlog
import sys
import os
from typing import Any, Dict


def setup_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
    """
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set the log level
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO)
    )
    
    return structlog.get_logger()


def log_processing_start(logger: structlog.BoundLogger, media_id: str, storage_path: str) -> None:
    """Log the start of image processing."""
    logger.info(
        "image_processing_started",
        media_id=media_id,
        storage_path=storage_path,
        event_type="processing_start"
    )


def log_processing_complete(
    logger: structlog.BoundLogger, 
    media_id: str, 
    duration_seconds: float,
    metadata: Dict[str, Any]
) -> None:
    """Log successful completion of image processing."""
    logger.info(
        "image_processing_completed",
        media_id=media_id,
        duration_seconds=duration_seconds,
        metadata=metadata,
        event_type="processing_complete"
    )


def log_processing_failed(
    logger: structlog.BoundLogger,
    media_id: str,
    error: Exception,
    stage: str
) -> None:
    """Log processing failure with error details."""
    logger.error(
        "image_processing_failed",
        media_id=media_id,
        error_type=type(error).__name__,
        error_message=str(error),
        stage=stage,
        event_type="processing_failed",
        exc_info=True
    )


def log_database_operation(
    logger: structlog.BoundLogger,
    operation: str,
    success: bool,
    details: Dict[str, Any] = None
) -> None:
    """Log database operations."""
    if success:
        logger.info(
            "database_operation_success",
            operation=operation,
            details=details,
            event_type="db_operation"
        )
    else:
        logger.error(
            "database_operation_failed",
            operation=operation,
            details=details,
            event_type="db_operation"
        ) 