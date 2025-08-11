"""
Typed error context classes for splurge-sql-runner.

Provides specific, strongly-typed error context classes for different
error scenarios with structured metadata and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""


from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from splurge_sql_runner.errors.error_handler import ErrorContext


@dataclass
class DatabaseErrorContext(ErrorContext):
    """
    Specialized error context for database-related errors.
    
    Provides database-specific context information including connection
    details, query information, and transaction state.
    """
    
    # Database connection information
    connection_string: str = ""
    database_type: str = ""
    database_version: str = ""
    
    # Operation details
    operation_type: str = ""  # query, command, batch, transaction
    sql_statement: str | None = None
    statement_parameters: Dict[str, Any] | None = None
    
    # Transaction context
    transaction_active: bool = False
    transaction_id: str | None = None
    savepoint_name: str | None = None
    
    # Performance metrics
    execution_time_ms: float | None = None
    rows_affected: int | None = None
    
    # Connection pool information
    pool_size: int | None = None
    active_connections: int | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization to set component if not provided."""
        if not self.component:
            self.component = "database"

    def sanitize_connection_string(self) -> str:
        """Get sanitized connection string with credentials removed."""
        # Simple sanitization - remove password from connection string
        if "://" in self.connection_string:
            try:
                parts = self.connection_string.split("://")
                if "@" in parts[1]:
                    user_host = parts[1].split("@")
                    if ":" in user_host[0]:
                        user = user_host[0].split(":")[0]
                        return f"{parts[0]}://{user}:***@{user_host[1]}"
                return self.connection_string
            except (IndexError, AttributeError):
                return self.connection_string
        return self.connection_string

    def get_database_metadata(self) -> Dict[str, Any]:
        """Get database-specific metadata for logging and debugging."""
        return {
            "database_type": self.database_type,
            "database_version": self.database_version,
            "connection_string": self.sanitize_connection_string(),
            "operation_type": self.operation_type,
            "transaction_active": self.transaction_active,
            "pool_size": self.pool_size,
            "active_connections": self.active_connections,
        }


@dataclass
class SqlErrorContext(ErrorContext):
    """
    Specialized error context for SQL-related errors.
    
    Provides SQL-specific context including statement details,
    file information, and parsing context.
    """
    
    # SQL statement details
    sql_statement: str = ""
    statement_type: str = ""  # SELECT, INSERT, UPDATE, DELETE, CREATE, etc.
    statement_index: int = 0  # Index in batch if applicable
    
    # File context
    file_path: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    
    # Parsing context
    parsing_stage: str = ""  # tokenization, parsing, validation, execution
    syntax_error_position: int | None = None
    
    # Security context
    security_validation_failed: bool = False
    dangerous_patterns_found: List[str] = field(default_factory=list)
    
    # Statement metrics
    statement_length: int = 0
    parameter_count: int = 0
    
    def __post_init__(self) -> None:
        """Post-initialization to set component and calculate metrics."""
        if not self.component:
            self.component = "sql"
        
        if self.sql_statement:
            self.statement_length = len(self.sql_statement)
            # Simple parameter counting (? or :param style)
            self.parameter_count = self.sql_statement.count("?") + len([
                part for part in self.sql_statement.split() 
                if part.startswith(":")
            ])

    def get_file_context(self) -> Dict[str, Any] | None:
        """Get file context information if available."""
        if not self.file_path:
            return None
        
        return {
            "file_path": self.file_path,
            "file_name": Path(self.file_path).name if self.file_path else None,
            "line_number": self.line_number,
            "column_number": self.column_number,
        }

    def get_sql_snippet(self, context_chars: int = 100) -> str:
        """Get a snippet of SQL around the error position."""
        if not self.sql_statement or not self.syntax_error_position:
            return self.sql_statement[:context_chars] if self.sql_statement else ""
        
        start = max(0, self.syntax_error_position - context_chars // 2)
        end = min(len(self.sql_statement), self.syntax_error_position + context_chars // 2)
        
        snippet = self.sql_statement[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(self.sql_statement):
            snippet = snippet + "..."
            
        return snippet

    def get_security_metadata(self) -> Dict[str, Any]:
        """Get security-related metadata."""
        return {
            "security_validation_failed": self.security_validation_failed,
            "dangerous_patterns_found": self.dangerous_patterns_found,
            "statement_length": self.statement_length,
            "parameter_count": self.parameter_count,
        }


@dataclass
class SecurityErrorContext(ErrorContext):
    """
    Specialized error context for security-related errors.
    
    Provides security-specific context including validation details,
    threat assessment, and mitigation information.
    """
    
    # Security validation details
    validation_type: str = ""  # file_path, sql_content, database_url
    validation_rule: str = ""  # specific rule that failed
    threat_level: str = "medium"  # low, medium, high, critical
    
    # Input details
    input_value: str = ""
    sanitized_value: str = ""
    
    # Pattern matching
    matched_patterns: List[str] = field(default_factory=list)
    pattern_categories: List[str] = field(default_factory=list)
    
    # File security context
    file_path: str | None = None
    file_size_bytes: int | None = None
    file_extension: str | None = None
    
    # URL security context
    url_scheme: str | None = None
    url_host: str | None = None
    
    # Mitigation information
    suggested_actions: List[str] = field(default_factory=list)
    can_be_sanitized: bool = False
    
    def __post_init__(self) -> None:
        """Post-initialization to set component and extract URL components."""
        if not self.component:
            self.component = "security"
        
        # Extract URL components if input looks like a URL
        if "://" in self.input_value:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.input_value)
                self.url_scheme = parsed.scheme
                self.url_host = parsed.hostname
            except Exception:
                pass
        
        # Extract file extension if input looks like a file path
        if self.file_path or ("." in self.input_value and "/" in self.input_value):
            path = self.file_path or self.input_value
            self.file_extension = Path(path).suffix

    def get_threat_assessment(self) -> Dict[str, Any]:
        """Get threat assessment information."""
        return {
            "threat_level": self.threat_level,
            "validation_type": self.validation_type,
            "validation_rule": self.validation_rule,
            "matched_patterns": self.matched_patterns,
            "pattern_categories": self.pattern_categories,
            "can_be_sanitized": self.can_be_sanitized,
        }

    def get_input_analysis(self) -> Dict[str, Any]:
        """Get detailed input analysis."""
        return {
            "input_length": len(self.input_value),
            "sanitized_length": len(self.sanitized_value),
            "file_extension": self.file_extension,
            "url_scheme": self.url_scheme,
            "url_host": self.url_host,
            "file_size_bytes": self.file_size_bytes,
        }

    def add_suggested_action(self, action: str) -> None:
        """Add a suggested mitigation action."""
        if action not in self.suggested_actions:
            self.suggested_actions.append(action)


@dataclass
class CliErrorContext(ErrorContext):
    """
    Specialized error context for CLI-related errors.
    
    Provides CLI-specific context including command-line arguments,
    file processing details, and user interaction context.
    """
    
    # Command line context
    cli_command: str = ""
    cli_arguments: Dict[str, Any] = field(default_factory=dict)
    current_working_directory: str = ""
    
    # File processing context
    files_to_process: List[str] = field(default_factory=list)
    current_file_index: int = 0
    current_file_path: str | None = None
    
    # Processing statistics
    files_processed: int = 0
    files_successful: int = 0
    files_failed: int = 0
    
    # User interaction context
    verbose_mode: bool = False
    debug_mode: bool = False
    security_disabled: bool = False
    
    # Environment context
    shell_type: str = ""
    terminal_width: int | None = None
    
    def __post_init__(self) -> None:
        """Post-initialization to set component and gather environment info."""
        if not self.component:
            self.component = "cli"
        
        # Try to get current working directory
        if not self.current_working_directory:
            try:
                import os
                self.current_working_directory = os.getcwd()
            except Exception:
                self.current_working_directory = "unknown"
        
        # Try to get terminal width
        if self.terminal_width is None:
            try:
                import shutil
                self.terminal_width = shutil.get_terminal_size().columns
            except Exception:
                self.terminal_width = 80  # Default width

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get file processing summary."""
        total_files = len(self.files_to_process)
        return {
            "total_files": total_files,
            "files_processed": self.files_processed,
            "files_successful": self.files_successful,
            "files_failed": self.files_failed,
            "current_file_index": self.current_file_index,
            "current_file_path": self.current_file_path,
            "success_rate": (
                self.files_successful / max(1, self.files_processed) * 100
                if self.files_processed > 0 else 0
            ),
        }

    def get_cli_environment(self) -> Dict[str, Any]:
        """Get CLI environment information."""
        return {
            "cli_command": self.cli_command,
            "current_working_directory": self.current_working_directory,
            "verbose_mode": self.verbose_mode,
            "debug_mode": self.debug_mode,
            "security_disabled": self.security_disabled,
            "shell_type": self.shell_type,
            "terminal_width": self.terminal_width,
        }

    def update_file_progress(self, file_path: str, success: bool) -> None:
        """Update file processing progress."""
        self.current_file_path = file_path
        self.files_processed += 1
        
        if success:
            self.files_successful += 1
        else:
            self.files_failed += 1


# Factory functions for creating specific error contexts

def create_database_error_context(
    operation: str,
    connection_string: str = "",
    sql_statement: str | None = None,
    **kwargs: Any
) -> DatabaseErrorContext:
    """
    Create a DatabaseErrorContext with common defaults.
    
    Args:
        operation: Database operation being performed
        connection_string: Database connection string
        sql_statement: SQL statement if applicable
        **kwargs: Additional context fields
        
    Returns:
        DatabaseErrorContext instance
    """
    return DatabaseErrorContext(
        operation=operation,
        component="database",
        connection_string=connection_string,
        sql_statement=sql_statement,
        timestamp=datetime.now(),
        **kwargs
    )


def create_sql_error_context(
    operation: str,
    sql_statement: str,
    file_path: str | None = None,
    **kwargs: Any
) -> SqlErrorContext:
    """
    Create a SqlErrorContext with common defaults.
    
    Args:
        operation: SQL operation being performed
        sql_statement: SQL statement that caused the error
        file_path: Path to SQL file if applicable
        **kwargs: Additional context fields
        
    Returns:
        SqlErrorContext instance
    """
    return SqlErrorContext(
        operation=operation,
        component="sql",
        sql_statement=sql_statement,
        file_path=file_path,
        timestamp=datetime.now(),
        **kwargs
    )


def create_security_error_context(
    operation: str,
    validation_type: str,
    input_value: str,
    **kwargs: Any
) -> SecurityErrorContext:
    """
    Create a SecurityErrorContext with common defaults.
    
    Args:
        operation: Security operation being performed
        validation_type: Type of security validation
        input_value: Input value being validated
        **kwargs: Additional context fields
        
    Returns:
        SecurityErrorContext instance
    """
    return SecurityErrorContext(
        operation=operation,
        component="security",
        validation_type=validation_type,
        input_value=input_value,
        timestamp=datetime.now(),
        **kwargs
    )


def create_cli_error_context(
    operation: str,
    cli_command: str,
    cli_arguments: Dict[str, Any] | None = None,
    **kwargs: Any
) -> CliErrorContext:
    """
    Create a CliErrorContext with common defaults.
    
    Args:
        operation: CLI operation being performed
        cli_command: CLI command being executed
        cli_arguments: Command line arguments
        **kwargs: Additional context fields
        
    Returns:
        CliErrorContext instance
    """
    return CliErrorContext(
        operation=operation,
        component="cli",
        cli_command=cli_command,
        cli_arguments=cli_arguments or {},
        timestamp=datetime.now(),
        **kwargs
    )
