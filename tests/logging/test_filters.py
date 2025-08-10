"""
Unit tests for logging filters.

Tests the PasswordFilter and CorrelationIdFilter functionality.
"""

import logging
from unittest.mock import patch

import pytest

from splurge_sql_runner.logging.filters import (
    PasswordFilter,
    CorrelationIdFilter,
)


class TestPasswordFilter:
    """Test password filtering functionality."""
    
    def test_password_filter_initialization(self) -> None:
        """Test PasswordFilter initialization."""
        filter_instance = PasswordFilter("test_filter")
        assert filter_instance.name == "test_filter"
        assert len(filter_instance._compiled_patterns) == 7
    
    def test_password_filter_with_password_in_message(self) -> None:
        """Test password filtering in log message."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Connection string: postgresql://user:secret123@localhost/db",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        assert "secret123" not in record.msg
        assert "[REDACTED]" in record.msg
    
    def test_password_filter_with_password_in_args(self) -> None:
        """Test password filtering in log record args."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Connection failed: %s",
            args=("postgresql://user:secret123@localhost/db",),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        assert "secret123" not in str(record.args)
        assert "[REDACTED]" in str(record.args)
    
    def test_password_filter_with_no_password(self) -> None:
        """Test password filter with no password in message."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Normal log message without password",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        assert record.msg == "Normal log message without password"
    
    def test_password_filter_with_api_key(self) -> None:
        """Test password filtering with API key pattern."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="API key: sk-1234567890abcdef",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        assert "sk-1234567890abcdef" not in record.msg
        assert "[REDACTED]" in record.msg
    
    def test_password_filter_with_bearer_token(self) -> None:
        """Test password filtering with bearer token pattern."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        # Authorization tokens should be redacted (case-insensitive matching)
        assert "Authorization: bearer [REDACTED]" in record.msg
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in record.msg
    
    def test_password_filter_with_basic_auth(self) -> None:
        """Test password filtering with basic auth pattern."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Authorization: Basic dXNlcjpwYXNzd29yZA==",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        # Basic auth credentials should be redacted (case-insensitive matching)
        assert "Authorization: basic [REDACTED]" in record.msg
        assert "dXNlcjpwYXNzd29yZA==" not in record.msg
    
    def test_password_filter_with_generic_auth_header(self) -> None:
        """Test password filtering with generic auth header pattern."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Auth: custom-token-12345",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        # Generic auth headers should be redacted
        assert "Auth: [REDACTED]" in record.msg
        assert "custom-token-12345" not in record.msg
    
    def test_password_filter_with_standalone_bearer_token(self) -> None:
        """Test password filtering with standalone bearer token."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        # Standalone bearer tokens should be redacted (case-insensitive matching)
        assert "bearer [REDACTED]" in record.msg
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in record.msg
    
    def test_password_filter_with_standalone_basic_auth(self) -> None:
        """Test password filtering with standalone basic auth."""
        filter_instance = PasswordFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Basic dXNlcjpwYXNzd29yZA==",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        # Standalone basic auth should be redacted (case-insensitive matching)
        assert "basic [REDACTED]" in record.msg
        assert "dXNlcjpwYXNzd29yZA==" not in record.msg

class TestCorrelationIdFilter:
    """Test correlation ID filtering functionality."""
    
    def test_correlation_id_filter_initialization(self) -> None:
        """Test CorrelationIdFilter initialization."""
        filter_instance = CorrelationIdFilter("test_filter")
        assert filter_instance.name == "test_filter"
    
    def test_correlation_id_filter_with_correlation_id(self) -> None:
        """Test correlation ID filtering with correlation ID present."""
        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Set correlation ID in thread-local storage
        from splurge_sql_runner.logging.filters import _thread_local
        _thread_local.correlation_id = "test-correlation-123"
        
        result = filter_instance.filter(record)
        assert result is True
        assert record.correlation_id == "test-correlation-123"
        
        # Clean up
        delattr(_thread_local, "correlation_id")
    
    def test_correlation_id_filter_without_correlation_id(self) -> None:
        """Test correlation ID filtering without correlation ID."""
        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        assert result is True
        assert record.msg == "Test message"
