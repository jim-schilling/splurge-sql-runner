"""
Typed error context classes for splurge-sql-runner.

Provides specific, strongly-typed error context classes for different
error scenarios with structured metadata and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""


from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
import re

import sqlparse
from sqlparse.tokens import Comment, DML, Punctuation, Name
from sqlparse.sql import Statement, Token

from splurge_sql_runner.errors.error_handler import ErrorContext


def _count_sql_parameters(sql_statement: str) -> int:
    """
    Count SQL parameters in a statement using sqlparse.
    
    This function properly handles:
    - Question mark parameters (?)
    - Named parameters (:param)
    - Quoted strings (single and double quotes)
    - SQL comments (-- and /* */)
    - Complex SQL statements with proper tokenization
    
    Args:
        sql_statement: The SQL statement to analyze
        
    Returns:
        Number of parameters found in the statement
    """
    if not sql_statement:
        return 0
    
    try:
        # Parse the SQL statement using sqlparse
        parsed = sqlparse.parse(sql_statement)
        if not parsed:
            return 0
        
        parameter_count = 0
        
        # Process each statement
        for statement in parsed:
            # Get all tokens from the statement
            tokens = statement.flatten()
            
            for token in tokens:
                # Skip comments
                if token.ttype in Comment:
                    continue
                
                # Count all placeholder parameters (both ? and :param)
                if token.ttype == Name.Placeholder:
                    parameter_count += 1
        
        return parameter_count
        
    except Exception:
        # Fallback to simple counting if sqlparse fails
        return _fallback_count_parameters(sql_statement)


def _fallback_count_parameters(sql_statement: str) -> int:
    """
    Fallback parameter counting method for when sqlparse fails.
    
    This is a simplified version that handles basic cases.
    
    Args:
        sql_statement: The SQL statement to analyze
        
    Returns:
        Number of parameters found in the statement
    """
    if not sql_statement:
        return 0
    
    # Simple counting - this is less accurate but provides a fallback
    question_mark_count = sql_statement.count('?')
    
    # Count named parameters with basic regex
    named_param_pattern = r':[a-zA-Z_][a-zA-Z0-9_]*'
    named_params = re.findall(named_param_pattern, sql_statement)
    
    return question_mark_count + len(named_params)


def _remove_sql_comments(sql_statement: str) -> str:
    """
    Remove SQL comments from a statement using sqlparse.
    
    Handles both single-line (--) and multi-line (/* */) comments.
    
    Args:
        sql_statement: The SQL statement with comments
        
    Returns:
        SQL statement with comments removed
    """
    if not sql_statement:
        return sql_statement
    
    try:
        # Use sqlparse to remove comments
        return sqlparse.format(sql_statement, strip_comments=True)
    except Exception:
        # Fallback to original statement if sqlparse fails
        return sql_statement


def _extract_sql_statement_type(sql_statement: str) -> str:
    """
    Extract the type of SQL statement using sqlparse.
    
    Args:
        sql_statement: The SQL statement to analyze
        
    Returns:
        Statement type in uppercase, or empty string if unknown
    """
    if not sql_statement:
        return ""
    
    try:
        # Parse the SQL statement
        parsed = sqlparse.parse(sql_statement.strip())
        if not parsed:
            return ""
        
        # Get the first statement
        statement = parsed[0]
        
        # Get the first token (should be the statement type)
        tokens = statement.flatten()
        for token in tokens:
            # Skip whitespace and comments
            if token.is_whitespace or token.ttype in Comment:
                continue
            
            # Check if it's a DML token (SELECT, INSERT, UPDATE, DELETE, etc.)
            if token.ttype in DML:
                return token.value.upper()
            
            # If it's not a DML token but looks like a statement type, return it
            if token.ttype == Name and token.value.upper() in [
                'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 
                'ALTER', 'GRANT', 'REVOKE', 'BEGIN', 'COMMIT', 'ROLLBACK'
            ]:
                return token.value.upper()
            
            # Return the first non-whitespace, non-comment token
            return token.value.upper()
        
        return ""
        
    except Exception:
        # Fallback to regex-based extraction
        return _fallback_extract_statement_type(sql_statement)


def _fallback_extract_statement_type(sql_statement: str) -> str:
    """
    Fallback statement type extraction using regex.
    
    Args:
        sql_statement: The SQL statement to analyze
        
    Returns:
        Statement type in uppercase, or empty string if unknown
    """
    if not sql_statement:
        return ""
    
    # Remove comments first
    clean_sql = _remove_sql_comments(sql_statement.strip())
    
    # Extract first word (should be the statement type)
    match = re.match(r'^\s*(\w+)', clean_sql, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return ""


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
            # Use robust parameter counting
            self.parameter_count = _count_sql_parameters(self.sql_statement)
            
            # Extract statement type if not provided
            if not self.statement_type:
                self.statement_type = _extract_sql_statement_type(self.sql_statement)

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
