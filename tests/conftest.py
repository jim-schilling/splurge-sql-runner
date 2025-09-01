"""
Pytest configuration and shared fixtures for splurge-sql-runner tests.

This module provides common test fixtures and configuration for all test modules.
"""

import json
import logging
import os
import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any, Generator

# Test constants
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_CONFIG_DIR = Path(__file__).parent / "test_configs"
TEST_SQL_DIR = Path(__file__).parent / "test_sql"

# Ensure test directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
TEST_CONFIG_DIR.mkdir(exist_ok=True)
TEST_SQL_DIR.mkdir(exist_ok=True)


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Provide the test data directory path."""
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def test_config_dir() -> Path:
    """Provide the test configuration directory path."""
    return TEST_CONFIG_DIR


@pytest.fixture(scope="session")
def test_sql_dir() -> Path:
    """Provide the test SQL directory path."""
    return TEST_SQL_DIR


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config_data() -> Dict[str, Any]:
    """Provide sample configuration data for testing."""
    return {
        "database": {
            "engine": "sqlite",
            "connection": {"database": ":memory:", "echo": False},
        },
        "logging": {"level": "INFO", "format": "json", "file": None},
        "security": {
            "validate_sql": True,
            "allowed_commands": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            "blocked_patterns": ["DROP", "TRUNCATE"],
        },
    }


@pytest.fixture
def sample_sql_content() -> str:
    """Provide sample SQL content for testing."""
    return """
-- Test SQL file
SELECT 1 as test_column;

-- Another statement
SELECT 'hello' as greeting;
"""


@pytest.fixture
def sample_sql_file(temp_dir: Path, sample_sql_content: str) -> Path:
    """Provide a temporary SQL file with sample content."""
    sql_file = temp_dir / "test.sql"
    sql_file.write_text(sample_sql_content)
    return sql_file


@pytest.fixture
def sample_config_file(temp_dir: Path, sample_config_data: Dict[str, Any]) -> Path:
    """Provide a temporary config file with sample data."""
    config_file = temp_dir / "test_config.json"
    with open(config_file, "w") as f:
        json.dump(sample_config_data, f, indent=2)
    return config_file


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Reset to basic configuration
    logging.basicConfig(level=logging.WARNING)

    yield

    # Cleanup after test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test."""
    # Store original environment
    original_env = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
