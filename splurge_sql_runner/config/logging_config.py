"""
Logging configuration classes for splurge-sql-runner.

Provides type-safe configuration classes for logging settings,
formats, and output destinations.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """Create LogLevel from string."""
        try:
            return cls(level.upper())
        except ValueError:
            return cls.INFO  # Default to INFO for invalid levels


class LogFormat(Enum):
    """Supported log formats."""

    TEXT = "TEXT"
    JSON = "JSON"

    @classmethod
    def from_string(cls, format_str: str) -> "LogFormat":
        """Create LogFormat from string."""
        try:
            return cls(format_str.upper())
        except ValueError:
            return cls.TEXT  # Default to TEXT for invalid formats


@dataclass
class LoggingConfig:
    """Complete logging configuration."""

    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.TEXT
    enable_console: bool = True
    enable_file: bool = False
    log_file: str | None = None
    log_dir: str | None = None
    backup_count: int = 7

    def __post_init__(self) -> None:
        """Validate logging configuration."""
        if self.backup_count < 0:
            raise ValueError("Backup count must be non-negative")

        if self.enable_file and not self.log_file and not self.log_dir:
            raise ValueError("Log file or directory must be specified when file logging is enabled")

    @classmethod
    def from_dict(cls, config_dict: dict) -> "LoggingConfig":
        """Create LoggingConfig from dictionary."""
        return cls(
            level=LogLevel.from_string(config_dict.get("level", "INFO")),
            format=LogFormat.from_string(config_dict.get("format", "TEXT")),
            enable_console=config_dict.get("enable_console", True),
            enable_file=config_dict.get("enable_file", False),
            log_file=config_dict.get("log_file"),
            log_dir=config_dict.get("log_dir"),
            backup_count=config_dict.get("backup_count", 7),
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "level": self.level.value,
            "format": self.format.value,
            "enable_console": self.enable_console,
            "enable_file": self.enable_file,
            "log_file": self.log_file,
            "log_dir": self.log_dir,
            "backup_count": self.backup_count,
        }

    @property
    def log_level_name(self) -> str:
        """Get log level as string."""
        return self.level.value

    @property
    def format_name(self) -> str:
        """Get format as string."""
        return self.format.value

    @property
    def is_json_format(self) -> bool:
        """Check if JSON format is enabled."""
        return self.format == LogFormat.JSON

    @property
    def is_text_format(self) -> bool:
        """Check if TEXT format is enabled."""
        return self.format == LogFormat.TEXT

    def get_log_file_path(self) -> str | None:
        """Get the log file path."""
        if self.log_file:
            return self.log_file
        elif self.log_dir:
            # Generate a default log file name in the log directory
            import os

            return os.path.join(self.log_dir, "splurge_sql_runner.log")
        return None
