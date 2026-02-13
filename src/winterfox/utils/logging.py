"""
Structured logging configuration for winterfox.

Provides:
- Console logging with rich formatting
- File logging with rotation
- Log level configuration
- Structured context (cycle_id, workspace_id, etc.)
"""

import logging
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    rich_tracebacks: bool = True,
    show_time: bool = True,
    show_path: bool = False,
) -> logging.Logger:
    """
    Set up structured logging for winterfox.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        rich_tracebacks: Enable rich exception formatting
        show_time: Show timestamps in console logs
        show_path: Show file paths in console logs

    Returns:
        Root logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler with rich formatting
    console_handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=rich_tracebacks,
        show_time=show_time,
        show_path=show_path,
        show_level=True,
        markup=True,
        tracebacks_show_locals=False,
    )
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(
        "%(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set levels for third-party libraries (reduce noise)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """
    Logger with structured context for research cycles.

    Usage:
        logger = StructuredLogger("orchestrator", workspace_id="test", cycle_id=5)
        logger.info("Starting cycle")
        # Output: [workspace=test cycle=5] Starting cycle
    """

    def __init__(self, name: str, **context: Any):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            **context: Context fields (workspace_id, cycle_id, etc.)
        """
        self.logger = logging.getLogger(name)
        self.context = context

    def _format_message(self, msg: str) -> str:
        """Format message with context."""
        if not self.context:
            return msg

        context_str = " ".join(f"{k}={v}" for k, v in self.context.items())
        return f"[{context_str}] {msg}"

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message(msg), **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(self._format_message(msg), **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message(msg), **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(self._format_message(msg), **kwargs)

    def critical(self, msg: str, **kwargs: Any) -> None:
        """Log critical message."""
        self.logger.critical(self._format_message(msg), **kwargs)

    def exception(self, msg: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(self._format_message(msg), **kwargs)

    def add_context(self, **context: Any) -> "StructuredLogger":
        """
        Create new logger with additional context.

        Args:
            **context: Additional context fields

        Returns:
            New StructuredLogger with combined context
        """
        combined_context = {**self.context, **context}
        return StructuredLogger(self.logger.name, **combined_context)
