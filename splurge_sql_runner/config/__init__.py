"""
Configuration management package for splurge-sql-runner.

Provides centralized configuration management with support for
JSON configuration files and CLI arguments.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

# Import configuration functions from the module at package level
# This is a temporary compatibility layer while config.py is refactored

from ..config.constants import (
    DANGEROUS_PATH_PATTERNS,
    DANGEROUS_SQL_PATTERNS,
    DANGEROUS_URL_PATTERNS,
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_ENABLE_DEBUG_MODE,
    DEFAULT_ENABLE_VALIDATION,
    DEFAULT_ENABLE_VERBOSE_OUTPUT,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_STATEMENT_LENGTH,
    DEFAULT_MAX_STATEMENTS_PER_FILE,
)


# These will be imported from config.py module when it's properly reorganized
# For now, define placeholder implementations
def get_default_config() -> dict:
    """Get default configuration."""
    from .config import get_default_config as _get_default_config

    return _get_default_config()


def get_env_config() -> dict:
    """Get configuration from environment variables."""
    from .config import get_env_config as _get_env_config

    return _get_env_config()


def load_config(config_file_path: str | None = None) -> dict:
    """Load configuration from file and environment."""
    from .config import load_config as _load_config

    return _load_config(config_file_path)


def load_json_config(file_path: str) -> dict:
    """Load JSON configuration file."""
    from .config import load_json_config as _load_json_config

    return _load_json_config(file_path)


def save_config(config: dict, file_path: str) -> None:
    """Save configuration to file."""
    from .config import save_config as _save_config

    return _save_config(config, file_path)


# Package domains
__domains__ = ["config", "constants"]

__all__ = [
    # Main configuration functions
    "load_config",
    "get_default_config",
    "get_env_config",
    "load_json_config",
    "save_config",
    # Legacy constants kept for backward compatibility
    "DEFAULT_MAX_STATEMENTS_PER_FILE",
    "DEFAULT_MAX_STATEMENT_LENGTH",
    "DEFAULT_CONNECTION_TIMEOUT",
    "DANGEROUS_PATH_PATTERNS",
    "DANGEROUS_SQL_PATTERNS",
    "DANGEROUS_URL_PATTERNS",
    "DEFAULT_ALLOWED_FILE_EXTENSIONS",
    "DEFAULT_ENABLE_VERBOSE_OUTPUT",
    "DEFAULT_ENABLE_DEBUG_MODE",
    "DEFAULT_ENABLE_VALIDATION",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_LOG_FORMAT",
]
