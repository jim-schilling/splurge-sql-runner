"""
Shared test fixtures and configuration for splurge-sql-runner test suite.

This module provides common fixtures, test utilities, and configuration
that can be shared across all test modules to reduce duplication and
improve test consistency.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, Engine

from splurge_sql_runner.config import (
    DatabaseConfig,
    SecurityConfig,
    LoggingConfig,
    ConnectionConfig,
    AppConfig,
    ConfigManager,
)
from splurge_sql_runner.database import UnifiedDatabaseEngine
from splurge_sql_runner.logging import setup_logging


# Test constants
TEST_DATABASE_URL = "sqlite:///:memory:"
TEST_SQL_CONTENT = """
-- Test table creation
CREATE TABLE test_users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);

-- Insert test data
INSERT INTO test_users (name, email) VALUES 
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com');

-- Query test data
SELECT * FROM test_users WHERE name = 'Alice';
"""

COMPLEX_SQL_CONTENT = """
-- Complex SQL with CTE
WITH active_users AS (
    SELECT id, name, email 
    FROM test_users 
    WHERE id > 0
),
user_stats AS (
    SELECT COUNT(*) as total_users
    FROM active_users
)
SELECT au.*, us.total_users
FROM active_users au
CROSS JOIN user_stats us;

-- Multi-line comment
/*
This is a multi-line comment
that spans several lines
*/
UPDATE test_users SET name = 'Alice Updated' WHERE id = 1;
"""


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_database_config() -> DatabaseConfig:
    """Create a mock database configuration for testing."""
    return DatabaseConfig(
        url=TEST_DATABASE_URL,
        connection=ConnectionConfig(timeout=30),
        enable_debug=False,
    )


@pytest.fixture
def mock_security_config() -> SecurityConfig:
    """Create a mock security configuration for testing."""
    return SecurityConfig(
        enable_validation=True,
        max_file_size_mb=10,
        max_statements_per_file=100,
        allowed_file_extensions=[".sql"],
    )


@pytest.fixture
def mock_logging_config() -> LoggingConfig:
    """Create a mock logging configuration for testing."""
    return LoggingConfig(
        level="INFO",
        format="TEXT",
        enable_console=True,
        enable_file=False,
    )


@pytest.fixture
def mock_app_config(
    mock_database_config: DatabaseConfig,
    mock_security_config: SecurityConfig,
    mock_logging_config: LoggingConfig,
) -> AppConfig:
    """Create a mock application configuration for testing."""
    return AppConfig(
        database=mock_database_config,
        security=mock_security_config,
        logging=mock_logging_config,
        max_file_size_mb=10,
        max_statements_per_file=100,
        enable_verbose_output=False,
        enable_debug_mode=False,
    )


@pytest.fixture
def mock_config_manager() -> ConfigManager:
    """Create a mock configuration manager for testing."""
    return ConfigManager()


@pytest.fixture
def in_memory_engine() -> Generator[Engine, None, None]:
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def mock_database_engine(mock_database_config: DatabaseConfig) -> Mock:
    """Create a mock database engine for testing."""
    engine = Mock(spec=UnifiedDatabaseEngine)
    engine._config = mock_database_config
    
    # Mock the batch method
    engine.batch.return_value = [
        {
            "statement": "SELECT 1",
            "statement_type": "fetch",
            "result": [{"test": 1}],
            "row_count": 1,
        }
    ]
    
    # Mock the create_connection method
    mock_connection = Mock()
    engine.create_connection.return_value = mock_connection
    
    # Mock the close method
    engine.close.return_value = None
    
    return engine


@pytest.fixture
def real_database_engine(mock_database_config: DatabaseConfig) -> Generator[UnifiedDatabaseEngine, None, None]:
    """Create a real database engine for integration testing."""
    engine = UnifiedDatabaseEngine(mock_database_config)
    yield engine
    engine.close()


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_directory() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_sql_file(temp_directory: str) -> str:
    """Create a temporary SQL file for testing."""
    file_path = os.path.join(temp_directory, "test.sql")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(TEST_SQL_CONTENT)
    return file_path


@pytest.fixture
def complex_sql_file(temp_directory: str) -> str:
    """Create a temporary complex SQL file for testing."""
    file_path = os.path.join(temp_directory, "complex.sql")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(COMPLEX_SQL_CONTENT)
    return file_path


@pytest.fixture
def empty_sql_file(temp_directory: str) -> str:
    """Create an empty SQL file for testing."""
    file_path = os.path.join(temp_directory, "empty.sql")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")
    return file_path


@pytest.fixture
def large_sql_file(temp_directory: str) -> str:
    """Create a large SQL file for testing."""
    file_path = os.path.join(temp_directory, "large.sql")
    with open(file_path, "w", encoding="utf-8") as f:
        # Create a large SQL file with many statements
        for i in range(1000):
            f.write(f"SELECT {i} as number;\n")
    return file_path


@pytest.fixture
def invalid_sql_file(temp_directory: str) -> str:
    """Create an invalid SQL file for testing."""
    file_path = os.path.join(temp_directory, "invalid.sql")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("""
        -- Invalid SQL that will cause errors
        SELECT * FROM nonexistent_table;
        INSERT INTO nonexistent_table VALUES (1, 2, 3);
        DROP TABLE nonexistent_table;
        """)
    return file_path


# ============================================================================
# CLI and Error Handling Fixtures
# ============================================================================

@pytest.fixture
def cli_args_basic() -> Dict[str, Any]:
    """Create basic CLI arguments for testing."""
    return {
        "connection": TEST_DATABASE_URL,
        "file": "test.sql",
        "verbose": False,
        "debug": False,
        "disable_security": False,
        "max_file_size": 10,
        "max_statements": 100,
    }


@pytest.fixture
def cli_args_verbose(cli_args_basic: Dict[str, Any]) -> Dict[str, Any]:
    """Create verbose CLI arguments for testing."""
    args = cli_args_basic.copy()
    args["verbose"] = True
    return args


@pytest.fixture
def cli_args_debug(cli_args_basic: Dict[str, Any]) -> Dict[str, Any]:
    """Create debug CLI arguments for testing."""
    args = cli_args_basic.copy()
    args["debug"] = True
    args["verbose"] = True
    return args


@pytest.fixture
def test_logger():
    """Create a test logger for testing."""
    with patch("splurge_sql_runner.logging.setup_logging") as mock_setup:
        mock_logger = Mock()
        mock_setup.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def dangerous_sql_file(temp_directory: str) -> str:
    """Create a SQL file with dangerous content for testing."""
    file_path = os.path.join(temp_directory, "dangerous.sql")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("""
        -- Dangerous SQL patterns
        DROP DATABASE test;
        EXEC xp_cmdshell 'dir';
        DELETE FROM INFORMATION_SCHEMA.TABLES;
        """)
    return file_path


@pytest.fixture
def dangerous_file_path() -> str:
    """Create a dangerous file path for testing."""
    return "/etc/passwd"


@pytest.fixture
def mock_sqlalchemy_engine():
    """Create a mock SQLAlchemy engine for testing."""
    engine = Mock()
    connection = Mock()
    engine.connect.return_value = connection
    return engine


@pytest.fixture
def mock_file_operations():
    """Create mock file operations for testing."""
    with patch("builtins.open") as mock_open, \
         patch("os.path.exists") as mock_exists, \
         patch("os.path.getsize") as mock_getsize:
        
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # 1KB
        
        yield {
            "open": mock_open,
            "exists": mock_exists,
            "getsize": mock_getsize,
        }


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def sample_sql_statements() -> list[str]:
    """Create sample SQL statements for testing."""
    return [
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
        "INSERT INTO users (name) VALUES ('Alice')",
        "SELECT * FROM users",
        "UPDATE users SET name = 'Bob' WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
    ]


@pytest.fixture
def sample_query_results() -> list[Dict[str, Any]]:
    """Create sample query results for testing."""
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def integration_test_setup(
    real_database_engine: UnifiedDatabaseEngine,
    temp_sql_file: str,
) -> Dict[str, Any]:
    """Create an integration test setup."""
    return {
        "engine": real_database_engine,
        "sql_file": temp_sql_file,
        "database_url": TEST_DATABASE_URL,
    }


@pytest.fixture
def performance_test_data() -> Dict[str, Any]:
    """Create performance test data."""
    return {
        "large_sql_file": "large.sql",
        "statement_count": 1000,
        "expected_execution_time": 5.0,  # seconds
    }
