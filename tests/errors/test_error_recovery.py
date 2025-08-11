"""
Tests for error recovery strategies.

Tests the error recovery strategies with minimal or no mocks,
using actual error instances and real recovery logic.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import pytest
from splurge_sql_runner.errors.error_recovery import (
    DatabaseErrorRecovery,
    SqlErrorRecovery,
    SecurityErrorRecovery,
    CliErrorRecovery,
)
from splurge_sql_runner.errors.error_handler import ErrorContext
from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
)
from splurge_sql_runner.errors.sql_errors import (
    SqlParseError,
    SqlFileError,
    SqlValidationError,
)
from splurge_sql_runner.errors.security_errors import (
    SecurityValidationError,
    SecurityFileError,
    SecurityUrlError,
)
from splurge_sql_runner.errors.cli_errors import (
    CliArgumentError,
    CliFileError,
    CliExecutionError,
)


class TestDatabaseErrorRecovery:
    """Test database error recovery strategies."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.recovery = DatabaseErrorRecovery()
        self.context = ErrorContext(operation="test_operation", component="test_component")

    def test_can_recover_connection_error(self) -> None:
        """Test recovery capability for connection errors."""
        error = DatabaseConnectionError("Connection failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_can_recover_operation_error_with_timeout(self) -> None:
        """Test recovery capability for operation errors with timeout."""
        error = DatabaseOperationError("Operation timeout occurred")
        assert self.recovery.can_recover(error, self.context) is True

    def test_can_recover_operation_error_with_connection(self) -> None:
        """Test recovery capability for operation errors with connection issues."""
        error = DatabaseOperationError("Connection lost during operation")
        assert self.recovery.can_recover(error, self.context) is True

    def test_cannot_recover_operation_error_without_keywords(self) -> None:
        """Test recovery capability for operation errors without recovery keywords."""
        error = DatabaseOperationError("Invalid SQL syntax")
        assert self.recovery.can_recover(error, self.context) is False

    def test_can_recover_batch_error(self) -> None:
        """Test recovery capability for batch errors."""
        error = DatabaseBatchError("Batch execution failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_cannot_recover_other_exceptions(self) -> None:
        """Test recovery capability for non-database exceptions."""
        error = ValueError("Some other error")
        assert self.recovery.can_recover(error, self.context) is False

    def test_recover_connection_error(self) -> None:
        """Test recovery from connection error."""
        error = DatabaseConnectionError("Connection failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "reconnected"
        assert result["error"] == "Connection failed"
        assert self.context.get_metadata("recovery_action") == "reconnect"

    def test_recover_operation_error(self) -> None:
        """Test recovery from operation error."""
        error = DatabaseOperationError("Operation failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "retried"
        assert result["error"] == "Operation failed"
        assert self.context.get_metadata("recovery_action") == "retry_operation"

    def test_recover_batch_error(self) -> None:
        """Test recovery from batch error."""
        error = DatabaseBatchError("Batch failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "partial"
        assert result["error"] == "Batch failed"
        assert self.context.get_metadata("recovery_action") == "partial_results"

    def test_recover_unrecoverable_error(self) -> None:
        """Test recovery from unrecoverable error."""
        error = ValueError("Unrecoverable error")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "unrecoverable"
        assert result["error"] == "Unrecoverable error"


class TestSqlErrorRecovery:
    """Test SQL error recovery strategies."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.recovery = SqlErrorRecovery()
        self.context = ErrorContext(operation="test_operation", component="test_component")

    def test_cannot_recover_parse_error(self) -> None:
        """Test recovery capability for parse errors."""
        error = SqlParseError("Invalid SQL syntax")
        assert self.recovery.can_recover(error, self.context) is False

    def test_can_recover_file_error_not_found(self) -> None:
        """Test recovery capability for file errors with 'not found'."""
        error = SqlFileError("SQL file not found")
        assert self.recovery.can_recover(error, self.context) is True

    def test_can_recover_file_error_permission(self) -> None:
        """Test recovery capability for file errors with 'permission'."""
        error = SqlFileError("Permission denied accessing SQL file")
        assert self.recovery.can_recover(error, self.context) is True

    def test_cannot_recover_file_error_other(self) -> None:
        """Test recovery capability for file errors without recovery keywords."""
        error = SqlFileError("SQL file corrupted")
        assert self.recovery.can_recover(error, self.context) is False

    def test_can_recover_validation_error(self) -> None:
        """Test recovery capability for validation errors."""
        error = SqlValidationError("SQL validation failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_cannot_recover_other_exceptions(self) -> None:
        """Test recovery capability for non-SQL exceptions."""
        error = ValueError("Some other error")
        assert self.recovery.can_recover(error, self.context) is False

    def test_recover_file_error(self) -> None:
        """Test recovery from file error."""
        error = SqlFileError("SQL file not found")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "file_alternative"
        assert result["error"] == "SQL file not found"
        assert self.context.get_metadata("recovery_action") == "file_alternative"

    def test_recover_validation_error(self) -> None:
        """Test recovery from validation error."""
        error = SqlValidationError("SQL validation failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "sanitized"
        assert result["error"] == "SQL validation failed"
        assert self.context.get_metadata("recovery_action") == "sanitize_sql"

    def test_recover_unrecoverable_error(self) -> None:
        """Test recovery from unrecoverable error."""
        error = ValueError("Unrecoverable error")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "unrecoverable"
        assert result["error"] == "Unrecoverable error"


class TestSecurityErrorRecovery:
    """Test security error recovery strategies."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.recovery = SecurityErrorRecovery()
        self.context = ErrorContext(operation="test_operation", component="test_component")

    def test_can_recover_validation_error(self) -> None:
        """Test recovery capability for validation errors."""
        error = SecurityValidationError("Security validation failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_can_recover_file_error(self) -> None:
        """Test recovery capability for file errors."""
        error = SecurityFileError("Security file check failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_can_recover_url_error(self) -> None:
        """Test recovery capability for URL errors."""
        error = SecurityUrlError("Security URL check failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_cannot_recover_other_exceptions(self) -> None:
        """Test recovery capability for non-security exceptions."""
        error = ValueError("Some other error")
        assert self.recovery.can_recover(error, self.context) is False

    def test_recover_validation_error(self) -> None:
        """Test recovery from validation error."""
        error = SecurityValidationError("Security validation failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "revalidated"
        assert result["error"] == "Security validation failed"
        assert self.context.get_metadata("recovery_action") == "additional_validation"

    def test_recover_file_error(self) -> None:
        """Test recovery from file error."""
        error = SecurityFileError("Security file check failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "alternative_file"
        assert result["error"] == "Security file check failed"
        assert self.context.get_metadata("recovery_action") == "alternative_file"

    def test_recover_url_error(self) -> None:
        """Test recovery from URL error."""
        error = SecurityUrlError("Security URL check failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "sanitized_url"
        assert result["error"] == "Security URL check failed"
        assert self.context.get_metadata("recovery_action") == "sanitize_url"

    def test_recover_unrecoverable_error(self) -> None:
        """Test recovery from unrecoverable error."""
        error = ValueError("Unrecoverable error")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "unrecoverable"
        assert result["error"] == "Unrecoverable error"


class TestCliErrorRecovery:
    """Test CLI error recovery strategies."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.recovery = CliErrorRecovery()
        self.context = ErrorContext(operation="test_operation", component="test_component")

    def test_can_recover_argument_error(self) -> None:
        """Test recovery capability for argument errors."""
        error = CliArgumentError("Invalid CLI arguments")
        assert self.recovery.can_recover(error, self.context) is True

    def test_can_recover_file_error(self) -> None:
        """Test recovery capability for file errors."""
        error = CliFileError("CLI file operation failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_can_recover_execution_error(self) -> None:
        """Test recovery capability for execution errors."""
        error = CliExecutionError("CLI execution failed")
        assert self.recovery.can_recover(error, self.context) is True

    def test_cannot_recover_other_exceptions(self) -> None:
        """Test recovery capability for non-CLI exceptions."""
        error = ValueError("Some other error")
        assert self.recovery.can_recover(error, self.context) is False

    def test_recover_argument_error(self) -> None:
        """Test recovery from argument error."""
        error = CliArgumentError("Invalid CLI arguments")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "defaults_used"
        assert result["error"] == "Invalid CLI arguments"
        assert self.context.get_metadata("recovery_action") == "use_defaults"

    def test_recover_file_error(self) -> None:
        """Test recovery from file error."""
        error = CliFileError("CLI file operation failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "alternative_file"
        assert result["error"] == "CLI file operation failed"
        assert self.context.get_metadata("recovery_action") == "alternative_file"

    def test_recover_execution_error(self) -> None:
        """Test recovery from execution error."""
        error = CliExecutionError("CLI execution failed")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "partial_results"
        assert result["error"] == "CLI execution failed"
        assert self.context.get_metadata("recovery_action") == "partial_results"

    def test_recover_unrecoverable_error(self) -> None:
        """Test recovery from unrecoverable error."""
        error = ValueError("Unrecoverable error")
        result = self.recovery.recover(error, self.context)
        
        assert result["status"] == "unrecoverable"
        assert result["error"] == "Unrecoverable error"


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery strategies."""

    def test_database_recovery_with_context_metadata(self) -> None:
        """Test database recovery with context metadata accumulation."""
        recovery = DatabaseErrorRecovery()
        context = ErrorContext(operation="batch_insert", component="database")
        
        # Simulate multiple recovery attempts
        error1 = DatabaseConnectionError("Connection lost")
        result1 = recovery.recover(error1, context)
        
        error2 = DatabaseOperationError("Operation timeout")
        result2 = recovery.recover(error2, context)
        
        assert result1["status"] == "reconnected"
        assert result2["status"] == "retried"
        assert context.get_metadata("recovery_action") == "retry_operation"
        assert len(context.metadata) == 1  # Last action overwrites previous

    def test_sql_recovery_with_context_metadata(self) -> None:
        """Test SQL recovery with context metadata accumulation."""
        recovery = SqlErrorRecovery()
        context = ErrorContext(operation="sql_execution", component="sql_parser")
        
        error = SqlValidationError("SQL contains unsafe operations")
        result = recovery.recover(error, context)
        
        assert result["status"] == "sanitized"
        assert context.get_metadata("recovery_action") == "sanitize_sql"

    def test_security_recovery_with_context_metadata(self) -> None:
        """Test security recovery with context metadata accumulation."""
        recovery = SecurityErrorRecovery()
        context = ErrorContext(operation="security_check", component="security_validator")
        
        error = SecurityUrlError("URL contains suspicious content")
        result = recovery.recover(error, context)
        
        assert result["status"] == "sanitized_url"
        assert context.get_metadata("recovery_action") == "sanitize_url"

    def test_cli_recovery_with_context_metadata(self) -> None:
        """Test CLI recovery with context metadata accumulation."""
        recovery = CliErrorRecovery()
        context = ErrorContext(operation="cli_execution", component="cli_parser")
        
        error = CliArgumentError("Missing required arguments")
        result = recovery.recover(error, context)
        
        assert result["status"] == "defaults_used"
        assert context.get_metadata("recovery_action") == "use_defaults"

    def test_recovery_strategies_with_different_contexts(self) -> None:
        """Test recovery strategies work with different context configurations."""
        db_recovery = DatabaseErrorRecovery()
        sql_recovery = SqlErrorRecovery()
        
        # Test with different context configurations
        context1 = ErrorContext(operation="test1", component="component1", attempt=1)
        context2 = ErrorContext(operation="test2", component="component2", attempt=5)
        
        error = DatabaseConnectionError("Connection failed")
        
        result1 = db_recovery.recover(error, context1)
        result2 = db_recovery.recover(error, context2)
        
        assert result1["status"] == "reconnected"
        assert result2["status"] == "reconnected"
        assert context1.get_metadata("recovery_action") == "reconnect"
        assert context2.get_metadata("recovery_action") == "reconnect"

    def test_error_message_preservation(self) -> None:
        """Test that error messages are preserved in recovery results."""
        recoveries = [
            (DatabaseErrorRecovery(), DatabaseConnectionError("Custom connection error")),
            (SqlErrorRecovery(), SqlValidationError("Custom validation error")),
            (SecurityErrorRecovery(), SecurityValidationError("Custom security error")),
            (CliErrorRecovery(), CliArgumentError("Custom argument error")),
        ]
        
        for recovery, error in recoveries:
            context = ErrorContext(operation="test", component="test")
            result = recovery.recover(error, context)
            
            assert result["error"] == str(error)
            assert "Custom" in result["error"]

    def test_recovery_strategy_consistency(self) -> None:
        """Test that recovery strategies are consistent across multiple calls."""
        recovery = DatabaseErrorRecovery()
        error = DatabaseConnectionError("Connection failed")
        
        # Multiple recoveries should produce consistent results
        results = []
        for _ in range(3):
            context = ErrorContext(operation="test", component="test")
            result = recovery.recover(error, context)
            results.append(result)
        
        # All results should be identical
        assert all(r["status"] == "reconnected" for r in results)
        assert all(r["error"] == "Connection failed" for r in results)
