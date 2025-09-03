"""
Core logging functionality for splurge-sql-runner.

Provides main logging setup and configuration functions.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

from splurge_sql_runner.errors import ConfigValidationError

# Global configuration registry to prevent multiple setups
_LOGGING_CONFIGURED = False
_LOGGING_CONFIG = {}

# Private constants
_DEFAULT_LOG_LEVEL: str = "INFO"
_DEFAULT_BACKUP_COUNT: int = 7
_DEFAULT_LOG_FILENAME: str = "splurge_sql_runner.log"
_DEFAULT_LOG_SUBDIR: str = ".splurge_sql_runner"
_DEFAULT_LOG_DIR: str = "logs"
_VALID_LOG_LEVELS: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def setup_logging(
    *,
    log_level: str = "INFO",
    log_file: str | None = None,
    log_dir: str | None = None,
    enable_console: bool = True,
    enable_json: bool = False,
    backup_count: int = 7,
) -> logging.Logger:
    """
    Set up logging configuration with timed rotation and security features.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Specific log file path (optional)
        log_dir: Directory for log files (optional)
        enable_console: Whether to enable console logging
        enable_json: Whether to use JSON formatting for file logs
        backup_count: Number of backup files to keep (7 days)

    Returns:
        Configured logger instance

    Raises:
        ValueError: If log_level is invalid
        OSError: If log directory cannot be created
    """
    global _LOGGING_CONFIGURED, _LOGGING_CONFIG

    # Validate log level
    if log_level.upper() not in _VALID_LOG_LEVELS:
        raise ConfigValidationError(
            f"Invalid log level: {log_level}. Must be one of {_VALID_LOG_LEVELS}"
        )

    # Store configuration
    _LOGGING_CONFIG = {
        "log_level": log_level,
        "log_file": log_file,
        "log_dir": log_dir,
        "enable_console": enable_console,
        "enable_json": enable_json,
        "backup_count": backup_count,
    }

    # Determine log file path
    if log_file:
        log_path = Path(log_file)
    elif log_dir:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        log_path = log_dir_path / _DEFAULT_LOG_FILENAME
    else:
        # Default to user's home directory
        home_dir = Path.home()
        log_dir_path = home_dir / _DEFAULT_LOG_SUBDIR / _DEFAULT_LOG_DIR
        log_dir_path.mkdir(parents=True, exist_ok=True)
        log_path = log_dir_path / _DEFAULT_LOG_FILENAME

    # Create logger
    logger = logging.getLogger("splurge_sql_runner")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # File handler with timed rotation (daily at midnight)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_path),
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_formatter = logging.Formatter(
        fmt=(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        # Console formatter (always human-readable)
        console_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    # Mark as configured
    _LOGGING_CONFIGURED = True

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance for the specified name.

    Args:
        name: Logger name (optional, defaults to 'splurge_sql_runner')

    Returns:
        Logger instance
    """
    if name is None:
        name = "splurge_sql_runner"

    return logging.getLogger(name)


def configure_module_logging(
    module_name: str,
    *,
    log_level: str | None = None,
    log_file: str | None = None,
    log_dir: str | None = None,
) -> logging.Logger:
    """
    Configure logging for a specific module.

    Args:
        module_name: Name of the module
        log_level: Logging level (optional, uses global config if not specified)
        log_file: Specific log file path (optional)
        log_dir: Directory for log files (optional)

    Returns:
        Configured logger for the module
    """
    # Set up main logging if not already configured
    main_logger = logging.getLogger("splurge_sql_runner")
    if not main_logger.handlers:
        # Use provided parameters or defaults
        setup_logging(
            log_level=log_level or _DEFAULT_LOG_LEVEL,
            log_file=log_file,
            log_dir=log_dir,
        )

    # Return module-specific logger
    return get_logger(f"splurge_sql_runner.{module_name}")


def get_logging_config() -> dict[str, Any]:
    """
    Get the current logging configuration.

    Returns:
        Dictionary containing current logging configuration
    """
    return _LOGGING_CONFIG.copy()


def is_logging_configured() -> bool:
    """
    Check if logging has been configured.

    Returns:
        True if logging is configured, False otherwise
    """
    return _LOGGING_CONFIGURED
