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


# Integration and E2E specific fixtures

@pytest.fixture(scope="session")
def integration_test_db_path(tmp_path_factory):
    """Create a temporary database file for integration tests."""
    return tmp_path_factory.mktemp("integration_db") / "integration.db"


@pytest.fixture(scope="session")
def e2e_test_db_path(tmp_path_factory):
    """Create a temporary database file for e2e tests."""
    return tmp_path_factory.mktemp("e2e_db") / "e2e.db"


@pytest.fixture
def integration_db_client(integration_test_db_path):
    """Database client fixture for integration tests."""
    from splurge_sql_runner.database.database_client import DatabaseClient
    from splurge_sql_runner.config.database_config import DatabaseConfig

    config = DatabaseConfig(url=f"sqlite:///{integration_test_db_path}")
    client = DatabaseClient(config)
    yield client
    client.close()


@pytest.fixture
def e2e_db_client(e2e_test_db_path):
    """Database client fixture for e2e tests."""
    from splurge_sql_runner.database.database_client import DatabaseClient
    from splurge_sql_runner.config.database_config import DatabaseConfig

    config = DatabaseConfig(url=f"sqlite:///{e2e_test_db_path}")
    client = DatabaseClient(config)
    yield client
    client.close()


@pytest.fixture
def temp_sql_file_factory(tmp_path):
    """Factory fixture for creating temporary SQL files."""
    def _create_sql_file(content: str, filename: str = "test.sql") -> Path:
        sql_file = tmp_path / filename
        sql_file.write_text(content)
        return sql_file
    return _create_sql_file


@pytest.fixture
def temp_config_file_factory(tmp_path):
    """Factory fixture for creating temporary config files."""
    def _create_config_file(config_data: dict, filename: str = "config.json") -> Path:
        config_file = tmp_path / filename
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        return config_file
    return _create_config_file


@pytest.fixture
def complex_test_data():
    """Complex test data for integration testing."""
    return {
        "users": [
            {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "department": "Engineering"},
            {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "department": "Sales"},
            {"id": 3, "name": "Charlie Brown", "email": "charlie@example.com", "department": "Engineering"},
        ],
        "orders": [
            {"id": 1, "user_id": 1, "amount": 99.99, "status": "completed"},
            {"id": 2, "user_id": 1, "amount": 149.50, "status": "pending"},
            {"id": 3, "user_id": 2, "amount": 75.00, "status": "completed"},
        ]
    }


@pytest.fixture
def sample_complex_sql(complex_test_data):
    """Generate complex SQL for testing."""
    sql_parts = []

    # Create tables
    sql_parts.append("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        department TEXT
    );

    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        amount REAL,
        status TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    # Insert users
    user_inserts = []
    for user in complex_test_data["users"]:
        user_inserts.append(f"INSERT INTO users (id, name, email, department) VALUES ({user['id']}, '{user['name']}', '{user['email']}', '{user['department']}');")
    sql_parts.append("\n".join(user_inserts))

    # Insert orders
    order_inserts = []
    for order in complex_test_data["orders"]:
        order_inserts.append(f"INSERT INTO orders (id, user_id, amount, status) VALUES ({order['id']}, {order['user_id']}, {order['amount']}, '{order['status']}');")
    sql_parts.append("\n".join(order_inserts))

    # Complex query
    sql_parts.append("""
    SELECT
        u.name,
        u.department,
        COUNT(o.id) as order_count,
        ROUND(SUM(o.amount), 2) as total_amount,
        AVG(o.amount) as avg_order_amount
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    GROUP BY u.id, u.name, u.department
    ORDER BY total_amount DESC NULLS LAST;
    """)

    return "\n\n".join(sql_parts)