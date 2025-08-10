"""
Tests for database.interfaces module.

Tests the database interface protocols and abstract classes using actual implementations.
"""

import pytest
from sqlalchemy import create_engine, text

from splurge_sql_runner.database.interfaces import (
    DatabaseConnection,
    DatabaseEngine,
    ConnectionPool,
    StatementExecutor,
    DatabaseRepository,
)
from splurge_sql_runner.database.engines import (
    SqlAlchemyConnection,
    SqlAlchemyConnectionPool,
    UnifiedDatabaseEngine,
)
from splurge_sql_runner.config.database_config import DatabaseConfig


class TestDatabaseConnection:
    """Test DatabaseConnection protocol with actual implementation."""

    def test_database_connection_protocol_implementation(self) -> None:
        """Test that SqlAlchemyConnection implements DatabaseConnection protocol."""
        # Create an in-memory SQLite engine
        engine = create_engine("sqlite:///:memory:")
        connection = engine.connect()
        
        # Create our implementation
        db_connection = SqlAlchemyConnection(connection)
        
        # Verify the protocol methods exist and work
        assert hasattr(db_connection, 'execute')
        assert hasattr(db_connection, 'fetch_all')
        assert hasattr(db_connection, 'fetch_one')
        assert hasattr(db_connection, 'commit')
        assert hasattr(db_connection, 'rollback')
        assert hasattr(db_connection, 'close')
        
        # Test basic functionality
        db_connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        db_connection.execute("INSERT INTO test (id, name) VALUES (:id, :name)", {"id": 1, "name": "test"})
        
        # Test fetch operations
        result = db_connection.fetch_one("SELECT * FROM test WHERE id = :id", {"id": 1})
        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "test"
        
        results = db_connection.fetch_all("SELECT * FROM test")
        assert len(results) == 1
        assert results[0]["id"] == 1
        
        # Test transaction operations
        db_connection.commit()
        
        # Clean up
        db_connection.close()


class TestDatabaseEngine:
    """Test DatabaseEngine with actual implementation."""

    def test_database_engine_implementation(self) -> None:
        """Test that UnifiedDatabaseEngine implements DatabaseEngine interface."""
        # Create a simple SQLite configuration
        config = DatabaseConfig(url="sqlite:///:memory:")
        
        # Create our implementation
        engine = UnifiedDatabaseEngine(config)
        
        # Verify the abstract methods exist
        assert hasattr(engine, 'create_connection')
        assert hasattr(engine, 'create_connection_pool')
        assert hasattr(engine, 'test_connection')
        assert hasattr(engine, 'get_database_info')
        assert hasattr(engine, 'close')
        
        # Test connection creation
        connection = engine.create_connection()
        assert isinstance(connection, SqlAlchemyConnection)
        
        # Test connection pool creation
        pool = engine.create_connection_pool(pool_size=3)
        assert isinstance(pool, SqlAlchemyConnectionPool)
        
        # Test database info
        info = engine.get_database_info()
        assert isinstance(info, dict)
        assert "url" in info
        
        # Test basic connection functionality
        connection.execute("SELECT 1")
        connection.close()
        
        # Clean up
        pool.close_all()
        engine.close()


class TestConnectionPool:
    """Test ConnectionPool with actual implementation."""

    def test_connection_pool_implementation(self) -> None:
        """Test that SqlAlchemyConnectionPool implements ConnectionPool interface."""
        # Create an in-memory SQLite engine
        engine = create_engine("sqlite:///:memory:")
        
        # Create our implementation
        pool = SqlAlchemyConnectionPool(engine, pool_size=3)
        
        # Verify the abstract methods exist
        assert hasattr(pool, 'get_connection')
        assert hasattr(pool, 'return_connection')
        assert hasattr(pool, 'close_all')
        assert hasattr(pool, 'health_check')
        
        # Test basic functionality
        assert pool.health_check()
        
        # Test connection management
        connection1 = pool.get_connection()
        assert isinstance(connection1, SqlAlchemyConnection)
        
        connection2 = pool.get_connection()
        assert isinstance(connection2, SqlAlchemyConnection)
        
        # Test that connections work
        connection1.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        connection1.execute("INSERT INTO test (id) VALUES (:id)", {"id": 1})
        
        result = connection2.fetch_one("SELECT * FROM test WHERE id = :id", {"id": 1})
        assert result is not None
        assert result["id"] == 1
        
        # Return connections to pool
        pool.return_connection(connection1)
        pool.return_connection(connection2)
        
        # Clean up
        pool.close_all()


class TestDatabaseIntegration:
    """Test integration between database components."""

    def test_full_database_workflow(self) -> None:
        """Test a complete database workflow using actual implementations."""
        # Create configuration
        config = DatabaseConfig(url="sqlite:///:memory:")
        
        # Create engine
        engine = UnifiedDatabaseEngine(config)
        
        # Create connection pool
        pool = engine.create_connection_pool(pool_size=2)
        
        # Get connection and perform operations
        connection = pool.get_connection()
        
        # Create table
        connection.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            )
        """)
        
        # Insert data
        connection.execute(
            "INSERT INTO users (id, name, email) VALUES (:id, :name, :email)",
            {"id": 1, "name": "John Doe", "email": "john@example.com"}
        )
        connection.execute(
            "INSERT INTO users (id, name, email) VALUES (:id, :name, :email)",
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
        )
        
        # Commit changes
        connection.commit()
        
        # Query data
        users = connection.fetch_all("SELECT * FROM users ORDER BY id")
        assert len(users) == 2
        assert users[0]["name"] == "John Doe"
        assert users[1]["name"] == "Jane Smith"
        
        # Test single row fetch
        user = connection.fetch_one("SELECT * FROM users WHERE email = :email", {"email": "jane@example.com"})
        assert user is not None
        assert user["name"] == "Jane Smith"
        
        # Test parameterized queries with different styles
        # Named parameters
        user_by_id = connection.fetch_one("SELECT * FROM users WHERE id = :id", {"id": 1})
        assert user_by_id is not None
        assert user_by_id["name"] == "John Doe"
        
        # Return connection to pool
        pool.return_connection(connection)
        
        # Clean up
        pool.close_all()
        engine.close()

    def test_transaction_handling(self) -> None:
        """Test transaction handling with actual database."""
        config = DatabaseConfig(url="sqlite:///:memory:")
        
        engine = UnifiedDatabaseEngine(config)
        connection = engine.create_connection()
        
        # Create table
        connection.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER)")
        connection.execute("INSERT INTO accounts (id, balance) VALUES (:id, :balance)", {"id": 1, "balance": 100})
        connection.commit()
        
        # Test rollback
        connection.execute("UPDATE accounts SET balance = balance - 50 WHERE id = :id", {"id": 1})
        connection.rollback()
        
        # Verify rollback worked
        account = connection.fetch_one("SELECT * FROM accounts WHERE id = :id", {"id": 1})
        assert account is not None
        assert account["balance"] == 100
        
        # Test commit
        connection.execute("UPDATE accounts SET balance = balance - 30 WHERE id = :id", {"id": 1})
        connection.commit()
        
        # Verify commit worked
        account = connection.fetch_one("SELECT * FROM accounts WHERE id = :id", {"id": 1})
        assert account is not None
        assert account["balance"] == 70
        
        connection.close()
        engine.close()


class TestProtocolCompliance:
    """Test that concrete implementations comply with protocols."""

    def test_database_connection_method_signatures(self) -> None:
        """Test DatabaseConnection method signatures with actual implementation."""
        # Create a test connection
        engine = create_engine("sqlite:///:memory:")
        connection = engine.connect()
        db_connection = SqlAlchemyConnection(connection)
        
        # Test that methods accept the expected parameters
        # execute(self, sql: str, parameters: Dict[str, Any] | None = None) -> Any
        result = db_connection.execute("SELECT 1 as test")
        assert result is not None
        
        result = db_connection.execute("SELECT :param as test", {"param": 1})
        assert result is not None
        
        # fetch_all(self, sql: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]
        results = db_connection.fetch_all("SELECT 1 as test")
        assert isinstance(results, list)
        assert len(results) == 1
        
        results = db_connection.fetch_all("SELECT :param as test", {"param": 1})
        assert isinstance(results, list)
        assert len(results) == 1
        
        # fetch_one(self, sql: str, parameters: Dict[str, Any] | None = None) -> Dict[str, Any] | None
        result = db_connection.fetch_one("SELECT 1 as test")
        assert isinstance(result, dict)
        
        result = db_connection.fetch_one("SELECT :param as test", {"param": 1})
        assert isinstance(result, dict)
        
        # commit, rollback, close return None
        db_connection.commit()
        db_connection.rollback()
        db_connection.close()

    def test_database_engine_method_signatures(self) -> None:
        """Test DatabaseEngine method signatures with actual implementation."""
        config = DatabaseConfig(url="sqlite:///:memory:")
        
        engine = UnifiedDatabaseEngine(config)
        
        # create_connection(self) -> DatabaseConnection
        connection = engine.create_connection()
        assert isinstance(connection, SqlAlchemyConnection)
        
        # create_connection_pool(self, pool_size: int = 5) -> ConnectionPool
        pool = engine.create_connection_pool(pool_size=3)
        assert isinstance(pool, SqlAlchemyConnectionPool)
        
        # test_connection(self) -> bool
        assert isinstance(engine.test_connection(), bool)
        
        # get_database_info(self) -> Dict[str, Any]
        info = engine.get_database_info()
        assert isinstance(info, dict)
        
        # close(self) -> None
        connection.close()
        pool.close_all()
        engine.close()

    def test_connection_pool_method_signatures(self) -> None:
        """Test ConnectionPool method signatures with actual implementation."""
        engine = create_engine("sqlite:///:memory:")
        pool = SqlAlchemyConnectionPool(engine, pool_size=2)
        
        # get_connection(self) -> DatabaseConnection
        connection = pool.get_connection()
        assert isinstance(connection, SqlAlchemyConnection)
        
        # return_connection(self, connection: DatabaseConnection) -> None
        pool.return_connection(connection)
        
        # health_check(self) -> bool
        assert isinstance(pool.health_check(), bool)
        
        # close_all(self) -> None
        pool.close_all()
