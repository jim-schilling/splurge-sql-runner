"""
Configuration validation and source tracking for splurge-sql-runner.

Provides comprehensive configuration validation with detailed source tracking,
validation summaries, and configuration audit capabilities.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any
from datetime import datetime


class ConfigSource(Enum):
    """Enumeration of configuration sources."""

    DEFAULT = "default"
    JSON_FILE = "json_file"
    ENVIRONMENT = "environment"
    CLI_ARGS = "cli_args"
    OVERRIDE = "override"


class ValidationSeverity(Enum):
    """Enumeration of validation message severities."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ConfigSourceInfo:
    """Information about a configuration value's source."""

    source: ConfigSource
    source_location: str  # File path, env var name, CLI arg, etc.
    original_value: Any
    final_value: Any
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def was_transformed(self) -> bool:
        """Check if the value was transformed from its original form."""
        return self.original_value != self.final_value


@dataclass
class ValidationMessage:
    """A validation message with context and severity."""

    severity: ValidationSeverity
    message: str
    config_key: str
    source_info: ConfigSourceInfo | None = None
    suggestion: str | None = None

    @property
    def is_error(self) -> bool:
        """Check if this is an error or critical message."""
        return self.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)


@dataclass
class ConfigValidationSummary:
    """
    Comprehensive configuration validation summary.

    Tracks configuration sources, validation results, overrides,
    and provides audit information for troubleshooting.
    """

    # Source tracking
    source_map: Dict[str, ConfigSourceInfo] = field(default_factory=dict)
    overrides: List[str] = field(default_factory=list)

    # Validation results
    validation_messages: List[ValidationMessage] = field(default_factory=list)

    # Metadata
    validation_timestamp: datetime = field(default_factory=datetime.now)
    config_file_path: str | None = None
    environment_prefix: str = "SPLURGE_SQL_RUNNER_"
    
    def add_source_info(
        self,
        config_key: str,
        source: ConfigSource,
        source_location: str,
        original_value: Any,
        final_value: Any
    ) -> None:
        """
        Add source information for a configuration key.

        Args:
            config_key: Configuration key (e.g., "database.url")
            source: Source of the configuration value
            source_location: Specific location (file path, env var, etc.)
            original_value: Original value from source
            final_value: Final processed value
        """
        self.source_map[config_key] = ConfigSourceInfo(
            source=source,
            source_location=source_location,
            original_value=original_value,
            final_value=final_value,
        )

        # Track overrides (non-default sources)
        if source != ConfigSource.DEFAULT and config_key not in self.overrides:
            self.overrides.append(config_key)

    def add_validation_message(
        self,
        severity: ValidationSeverity,
        message: str,
        config_key: str,
        suggestion: str | None = None
    ) -> None:
        """
        Add a validation message.

        Args:
            severity: Message severity level
            message: Validation message text
            config_key: Configuration key this message relates to
            suggestion: Optional suggestion for fixing the issue
        """
        source_info = self.source_map.get(config_key)
        self.validation_messages.append(ValidationMessage(
            severity=severity,
            message=message,
            config_key=config_key,
            source_info=source_info,
            suggestion=suggestion,
        ))

    def add_info(self, message: str, config_key: str, suggestion: str | None = None) -> None:
        """Add an info-level validation message."""
        self.add_validation_message(ValidationSeverity.INFO, message, config_key, suggestion)

    def add_warning(self, message: str, config_key: str, suggestion: str | None = None) -> None:
        """Add a warning-level validation message."""
        self.add_validation_message(ValidationSeverity.WARNING, message, config_key, suggestion)

    def add_error(self, message: str, config_key: str, suggestion: str | None = None) -> None:
        """Add an error-level validation message."""
        self.add_validation_message(ValidationSeverity.ERROR, message, config_key, suggestion)

    def add_critical(self, message: str, config_key: str, suggestion: str | None = None) -> None:
        """Add a critical-level validation message."""
        self.add_validation_message(ValidationSeverity.CRITICAL, message, config_key, suggestion)

    @property
    def has_errors(self) -> bool:
        """Check if there are any error or critical validation messages."""
        return any(msg.is_error for msg in self.validation_messages)

    @property
    def error_count(self) -> int:
        """Get the number of error and critical messages."""
        return sum(1 for msg in self.validation_messages if msg.is_error)

    @property
    def warning_count(self) -> int:
        """Get the number of warning messages."""
        return sum(1 for msg in self.validation_messages if msg.severity == ValidationSeverity.WARNING)

    def get_sources_by_type(self) -> Dict[ConfigSource, List[str]]:
        """Get configuration keys grouped by source type."""
        sources = {}
        for key, info in self.source_map.items():
            if info.source not in sources:
                sources[info.source] = []
            sources[info.source].append(key)
        return sources

    def get_transformed_values(self) -> List[str]:
        """Get list of configuration keys that had their values transformed."""
        return [
            key for key, info in self.source_map.items()
            if info.was_transformed
        ]

    def get_messages_by_severity(self, severity: ValidationSeverity) -> List[ValidationMessage]:
        """Get validation messages filtered by severity."""
        return [msg for msg in self.validation_messages if msg.severity == severity]

    def get_source_info(self, config_key: str) -> ConfigSourceInfo | None:
        """Get source information for a specific configuration key."""
        return self.source_map.get(config_key)

    def generate_report(self, include_source_details: bool = True) -> str:
        """
        Generate a human-readable configuration validation report.
        
        Args:
            include_source_details: Whether to include detailed source information
            
        Returns:
            Formatted validation report as string
        """
        lines = []
        lines.append("Configuration Validation Report")
        lines.append("=" * 50)
        lines.append(f"Generated: {self.validation_timestamp.isoformat()}")
        
        if self.config_file_path:
            lines.append(f"Config File: {self.config_file_path}")
        
        lines.append("")
        
        # Summary statistics
        lines.append("Summary:")
        lines.append(f"  Total configuration keys: {len(self.source_map)}")
        lines.append(f"  Overridden from defaults: {len(self.overrides)}")
        lines.append(f"  Values transformed: {len(self.get_transformed_values())}")
        lines.append(f"  Validation messages: {len(self.validation_messages)}")
        lines.append(f"    Errors/Critical: {self.error_count}")
        lines.append(f"    Warnings: {self.warning_count}")
        lines.append("")
        
        # Validation messages
        if self.validation_messages:
            lines.append("Validation Messages:")
            # Define severity order for proper sorting (highest to lowest)
            severity_order = {
                ValidationSeverity.CRITICAL: 0,
                ValidationSeverity.ERROR: 1,
                ValidationSeverity.WARNING: 2,
                ValidationSeverity.INFO: 3,
            }
            for msg in sorted(self.validation_messages, key=lambda x: (severity_order[x.severity], x.config_key)):
                severity_marker = {
                    ValidationSeverity.INFO: "ℹ️",
                    ValidationSeverity.WARNING: "⚠️",
                    ValidationSeverity.ERROR: "❌",
                    ValidationSeverity.CRITICAL: "🚨",
                }.get(msg.severity, "?")
                
                lines.append(f"  {severity_marker} [{msg.severity.value.upper()}] {msg.config_key}: {msg.message}")
                if msg.suggestion:
                    lines.append(f"    💡 Suggestion: {msg.suggestion}")
            lines.append("")
        
        # Source breakdown
        if include_source_details:
            sources_by_type = self.get_sources_by_type()
            lines.append("Configuration Sources:")
            for source_type in ConfigSource:
                keys = sources_by_type.get(source_type, [])
                if keys:
                    lines.append(f"  {source_type.value.title()} ({len(keys)} keys):")
                    for key in sorted(keys):
                        info = self.source_map[key]
                        transformed = " (transformed)" if info.was_transformed else ""
                        lines.append(f"    - {key}: {info.source_location}{transformed}")
            lines.append("")
        
        # Overrides section
        if self.overrides:
            lines.append("Configuration Overrides:")
            for key in sorted(self.overrides):
                info = self.source_map[key]
                lines.append(f"  {key}: {info.source.value} -> {info.final_value}")
            lines.append("")
        
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation summary to dictionary representation."""
        return {
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "config_file_path": self.config_file_path,
            "environment_prefix": self.environment_prefix,
            "summary": {
                "total_keys": len(self.source_map),
                "overridden_keys": len(self.overrides),
                "transformed_values": len(self.get_transformed_values()),
                "validation_messages": len(self.validation_messages),
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "has_errors": self.has_errors,
            },
            "sources": {
                source.value: keys 
                for source, keys in self.get_sources_by_type().items()
            },
            "overrides": self.overrides,
            "validation_messages": [
                {
                    "severity": msg.severity.value,
                    "message": msg.message,
                    "config_key": msg.config_key,
                    "suggestion": msg.suggestion,
                }
                for msg in self.validation_messages
            ],
            "source_details": {
                key: {
                    "source": info.source.value,
                    "source_location": info.source_location,
                    "original_value": str(info.original_value),
                    "final_value": str(info.final_value),
                    "was_transformed": info.was_transformed,
                    "timestamp": info.timestamp.isoformat(),
                }
                for key, info in self.source_map.items()
            },
        }
