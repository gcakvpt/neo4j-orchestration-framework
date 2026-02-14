"""
Logging utilities for consistent logging across framework.
"""

import logging
import sys
from typing import Optional


# Default log format
DEFAULT_FORMAT = (
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

# Detailed format with file/line info
DETAILED_FORMAT = (
    "%(asctime)s | %(name)s | %(levelname)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)


def get_logger(
    name: str,
    level: str = "INFO",
    detailed: bool = False
) -> logging.Logger:
    """Get configured logger
    
    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        detailed: Whether to include file/line numbers
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        fmt = DETAILED_FORMAT if detailed else DEFAULT_FORMAT
        formatter = logging.Formatter(fmt)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper()))
    
    return logger


def log_execution_time(logger: logging.Logger):
    """Decorator to log function execution time"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"{func.__name__} completed in {duration:.3f}s")
            return result
        return wrapper
    return decorator


__all__ = ["get_logger", "log_execution_time"]
