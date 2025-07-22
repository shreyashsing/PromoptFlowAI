"""
Comprehensive logging configuration for PromptFlow AI platform.
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        extra_fields = {
            key: value for key, value in record.__dict__.items()
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }
        }
        
        if extra_fields:
            log_data.update(extra_fields)
        
        return json.dumps(log_data, default=str)


class ContextFilter(logging.Filter):
    """Filter to add context information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class ErrorCountHandler(logging.Handler):
    """Handler to count errors for monitoring."""
    
    def __init__(self):
        super().__init__()
        self.error_counts: Dict[str, int] = {}
        self.warning_counts: Dict[str, int] = {}
    
    def emit(self, record: logging.LogRecord):
        """Count errors and warnings."""
        if record.levelno >= logging.ERROR:
            logger_name = record.name
            self.error_counts[logger_name] = self.error_counts.get(logger_name, 0) + 1
        elif record.levelno >= logging.WARNING:
            logger_name = record.name
            self.warning_counts[logger_name] = self.warning_counts.get(logger_name, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get error and warning statistics."""
        return {
            "errors": self.error_counts.copy(),
            "warnings": self.warning_counts.copy(),
            "total_errors": sum(self.error_counts.values()),
            "total_warnings": sum(self.warning_counts.values())
        }
    
    def reset_stats(self):
        """Reset error and warning counts."""
        self.error_counts.clear()
        self.warning_counts.clear()


# Global error count handler for monitoring
error_count_handler = ErrorCountHandler()


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True
) -> Dict[str, Any]:
    """
    Set up comprehensive logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("json" or "text")
        log_file: Path to log file (optional)
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Whether to enable console logging
        
    Returns:
        Dictionary with logging configuration details
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Set up formatters
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handlers_added = []
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        handlers_added.append("console")
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        handlers_added.append("file")
    
    # Add error counting handler
    error_count_handler.setLevel(logging.WARNING)
    root_logger.addHandler(error_count_handler)
    handlers_added.append("error_counter")
    
    # Configure specific loggers
    configure_logger_levels()
    
    return {
        "level": log_level,
        "format": log_format,
        "handlers": handlers_added,
        "log_file": log_file,
        "max_file_size": max_file_size,
        "backup_count": backup_count
    }


def configure_logger_levels():
    """Configure specific logger levels to reduce noise."""
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.INFO)
    
    # Set application loggers to appropriate levels
    logging.getLogger("app.services").setLevel(logging.INFO)
    logging.getLogger("app.connectors").setLevel(logging.INFO)
    logging.getLogger("app.api").setLevel(logging.INFO)
    logging.getLogger("app.core").setLevel(logging.DEBUG)


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Get a logger with optional context.
    
    Args:
        name: Logger name
        context: Additional context to include in all log messages
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if context:
        # Add context filter
        context_filter = ContextFilter(context)
        logger.addFilter(context_filter)
    
    return logger


def log_function_call(
    logger: logging.Logger,
    function_name: str,
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
    level: int = logging.DEBUG
):
    """
    Log function call with parameters.
    
    Args:
        logger: Logger instance
        function_name: Name of the function being called
        args: Function arguments
        kwargs: Function keyword arguments
        level: Logging level
    """
    kwargs = kwargs or {}
    
    # Sanitize sensitive data
    sanitized_kwargs = {}
    sensitive_keys = {'password', 'token', 'key', 'secret', 'auth'}
    
    for key, value in kwargs.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            sanitized_kwargs[key] = "[REDACTED]"
        else:
            sanitized_kwargs[key] = str(value)[:100]  # Truncate long values
    
    logger.log(
        level,
        f"Calling {function_name}",
        extra={
            "function": function_name,
            "args_count": len(args),
            "kwargs": sanitized_kwargs
        }
    )


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration: float,
    success: bool = True,
    additional_data: Optional[Dict[str, Any]] = None
):
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        duration: Duration in seconds
        success: Whether the operation was successful
        additional_data: Additional data to log
    """
    additional_data = additional_data or {}
    
    logger.info(
        f"Performance: {operation} {'succeeded' if success else 'failed'} in {duration:.3f}s",
        extra={
            "operation": operation,
            "duration": duration,
            "success": success,
            **additional_data
        }
    )


def get_logging_stats() -> Dict[str, Any]:
    """Get logging statistics for monitoring."""
    return {
        "error_stats": error_count_handler.get_stats(),
        "handlers": [
            {
                "name": handler.__class__.__name__,
                "level": logging.getLevelName(handler.level)
            }
            for handler in logging.getLogger().handlers
        ],
        "loggers": {
            name: {
                "level": logging.getLevelName(logger.level),
                "effective_level": logging.getLevelName(logger.getEffectiveLevel()),
                "handlers_count": len(logger.handlers)
            }
            for name, logger in logging.getLogger().manager.loggerDict.items()
            if isinstance(logger, logging.Logger)
        }
    }


# Initialize logging based on settings
def init_logging():
    """Initialize logging configuration based on application settings."""
    log_config = setup_logging(
        log_level=getattr(settings, 'LOG_LEVEL', 'INFO'),
        log_format=getattr(settings, 'LOG_FORMAT', 'json'),
        log_file=getattr(settings, 'LOG_FILE', None),
        enable_console=getattr(settings, 'LOG_CONSOLE', True)
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized", extra={"config": log_config})
    
    return log_config