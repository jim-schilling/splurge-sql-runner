"""
Shared test utilities for splurge-sql-runner tests.

This module provides common test utilities, constants, and helper functions
used across multiple test modules.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock

# Test constants
VALID_SQL_STATEMENTS = [
    "SELECT 1 as test_column;",
    "SELECT 'hello' as greeting;",
    "INSERT INTO test_table (id, name) VALUES (1, 'test');",
    "UPDATE test_table SET name = 'updated' WHERE id = 1;",
    "DELETE FROM test_table WHERE id = 1;",
]

INVALID_SQL_STATEMENTS = [
    "DROP TABLE test_table;",
    "TRUNCATE TABLE test_table;",
    "DROP DATABASE test_db;",
    "EXEC sp_configure 'show advanced options', 1;",
]

TEST_DATABASE_CONFIGS = {
    "sqlite": {
        "engine": "sqlite",
        "connection": {
            "database": ":memory:",
            "echo": False
        }
    },
    "postgresql": {
        "engine": "postgresql",
        "connection": {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass"
        }
    },
    "mysql": {
        "engine": "mysql",
        "connection": {
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass"
        }
    }
}

TEST_LOGGING_CONFIGS = {
    "basic": {
        "level": "INFO",
        "format": "text",
        "file": None
    },
    "json": {
        "level": "DEBUG",
        "format": "json",
        "file": "test.log"
    },
    "detailed": {
        "level": "WARNING",
        "format": "detailed",
        "file": "detailed.log"
    }
}

TEST_SECURITY_CONFIGS = {
    "permissive": {
        "validate_sql": False,
        "allowed_commands": ["SELECT", "INSERT", "UPDATE", "DELETE"],
        "blocked_patterns": []
    },
    "restrictive": {
        "validate_sql": True,
        "allowed_commands": ["SELECT"],
        "blocked_patterns": ["DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT"]
    },
    "moderate": {
        "validate_sql": True,
        "allowed_commands": ["SELECT", "INSERT", "UPDATE", "DELETE"],
        "blocked_patterns": ["DROP", "TRUNCATE"]
    }
}


class TestDataBuilder:
    """Builder class for creating test data structures."""
    
    @staticmethod
    def create_config_data(
        database_config: Optional[Dict[str, Any]] = None,
        logging_config: Optional[Dict[str, Any]] = None,
        security_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a complete configuration data structure."""
        return {
            "database": database_config or TEST_DATABASE_CONFIGS["sqlite"],
            "logging": logging_config or TEST_LOGGING_CONFIGS["basic"],
            "security": security_config or TEST_SECURITY_CONFIGS["moderate"]
        }
    
    @staticmethod
    def create_sql_file_content(statements: List[str]) -> str:
        """Create SQL file content from a list of statements."""
        return "\n".join(statements)
    
    @staticmethod
    def create_mock_database_connection() -> Mock:
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_conn.execute.return_value = Mock()
        mock_conn.commit.return_value = None
        mock_conn.rollback.return_value = None
        mock_conn.close.return_value = None
        return mock_conn
    
    @staticmethod
    def create_mock_sql_result(rows: List[Dict[str, Any]]) -> Mock:
        """Create a mock SQL result with specified rows."""
        mock_result = Mock()
        mock_result.fetchall.return_value = rows
        mock_result.fetchone.return_value = rows[0] if rows else None
        mock_result.rowcount = len(rows)
        return mock_result


class TestFileHelper:
    """Helper class for file operations in tests."""
    
    @staticmethod
    def create_temp_file(content: str, suffix: str = ".txt") -> Path:
        """Create a temporary file with specified content."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    
    @staticmethod
    def create_temp_json_file(data: Dict[str, Any]) -> Path:
        """Create a temporary JSON file with specified data."""
        content = json.dumps(data, indent=2)
        return TestFileHelper.create_temp_file(content, ".json")
    
    @staticmethod
    def create_temp_sql_file(statements: List[str]) -> Path:
        """Create a temporary SQL file with specified statements."""
        content = TestDataBuilder.create_sql_file_content(statements)
        return TestFileHelper.create_temp_file(content, ".sql")


class TestAssertions:
    """Custom assertion methods for tests."""
    
    @staticmethod
    def assert_config_structure(config: Dict[str, Any]) -> None:
        """Assert that a configuration has the expected structure."""
        assert "database" in config
        assert "logging" in config
        assert "security" in config
        
        assert "engine" in config["database"]
        assert "connection" in config["database"]
        
        assert "level" in config["logging"]
        assert "format" in config["logging"]
        
        assert "validate_sql" in config["security"]
        assert "allowed_commands" in config["security"]
        assert "blocked_patterns" in config["security"]
    
    @staticmethod
    def assert_sql_statements_valid(statements: List[str]) -> None:
        """Assert that SQL statements are valid."""
        for statement in statements:
            assert statement.strip().endswith(';')
            assert len(statement.strip()) > 0
    
    @staticmethod
    def assert_error_has_context(error: Exception, expected_context: Dict[str, Any]) -> None:
        """Assert that an error has the expected context."""
        if hasattr(error, 'context'):
            for key, value in expected_context.items():
                assert key in error.context
                assert error.context[key] == value


class TestConstants:
    """Constants used across tests."""
    
    # File paths
    TEST_SQL_FILE = "test_queries.sql"
    TEST_CONFIG_FILE = "test_config.json"
    TEST_LOG_FILE = "test.log"
    
    # Database names
    TEST_DATABASE_NAME = "test_database"
    TEST_TABLE_NAME = "test_table"
    
    # Timeouts
    DEFAULT_TIMEOUT = 30
    SHORT_TIMEOUT = 5
    LONG_TIMEOUT = 60
    
    # Retry settings
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 1
    
    # Log levels
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # SQL commands
    SQL_COMMANDS = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "TRUNCATE"]
    
    # Error messages
    ERROR_MESSAGES = {
        "config_not_found": "Configuration file not found",
        "invalid_sql": "Invalid SQL statement",
        "connection_failed": "Database connection failed",
        "permission_denied": "Permission denied",
        "timeout": "Operation timed out"
    }
