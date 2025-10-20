"""
Configuration management package for splurge-sql-runner.

Provides centralized configuration management with support for
JSON configuration files and CLI arguments.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

# Simplified configuration system
# Import main config functions
import importlib.util
import os

from splurge_sql_runner.config.constants import (
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

# Find the config.py file relative to this __init__.py file
_current_dir = os.path.dirname(__file__)
_config_file = os.path.join(_current_dir, "..", "config.py")
_config_file = os.path.abspath(_config_file)

spec = importlib.util.spec_from_file_location("config", _config_file)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load config module from {_config_file}")
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

get_default_config = config_module.get_default_config
get_env_config = config_module.get_env_config
load_config = config_module.load_config
load_json_config = config_module.load_json_config
save_config = config_module.save_config

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
