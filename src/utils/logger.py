"""
Structured logging utility for MCP Maximo Server
Provides correlation ID tracking and JSON formatting
"""
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor

from src.config import settings

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log entries"""
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries"""
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def configure_logging() -> None:
    """Configure structured logging for the application"""

    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Processors for structlog
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_correlation_id,
        add_app_context,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add appropriate renderer based on format
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name"""
    return structlog.get_logger(name)


def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for current context"""
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context"""
    correlation_id_var.set(None)


# Configure logging on module import
configure_logging()


# Convenience function for getting module-specific loggers
def get_module_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for the calling module"""
    import inspect
    frame = inspect.currentframe()
    if frame and frame.f_back:
        module_name = frame.f_back.f_globals.get("__name__", "unknown")
        return get_logger(module_name)
    return get_logger("unknown")
