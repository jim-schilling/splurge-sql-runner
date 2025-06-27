"""
Database helper module for jpy-sql-runner.

Provides database connection management and batch SQL execution functionality
with support for multiple database backends through SQLAlchemy.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import Connection
from typing import List, Dict, Any
from jpy_sql_runner.sql_helper import parse_sql_statements, detect_statement_type, FETCH_STATEMENT, EXECUTE_STATEMENT, ERROR_STATEMENT


class DbOperationError(Exception):
    """
    Exception raised when a database operation fails.
    """
    pass


class DbEngine:
    def __init__(self, database_url: str, **kwargs) -> None:
        """
        Initialize the DbEngine with database connection configuration.
        
        Args:
            database_url: SQLAlchemy database URL (e.g., 'sqlite:///database.db')
            **kwargs: Additional configuration options:
                - debug: Enable SQLAlchemy echo mode (default: False)
        """
        # Performance-tuned engine configuration
        self._engine = create_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={
                'check_same_thread': False,
                'timeout': 30,
            },
            echo=kwargs.get('debug', False)
        )        

    def _fetch_with_connection(self, conn: Connection, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query using an existing connection.
        
        Args:
            conn: Database connection
            query: SQL SELECT query string
            
        Returns:
            List of dictionaries representing the query results
        """
        result = conn.execute(text(query))
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    
    def _execute_with_connection(self, conn: Connection, query: str) -> bool:
        """
        Execute a non-SELECT query using an existing connection.
        
        Args:
            conn: Database connection
            query: SQL query string
            
        Returns:
            True for successful execution
        """
        conn.execute(text(query))
        return True

    def _execute_batch_statements(self, conn: Connection, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a batch of SQL statements and return results for each.
        Stops and rolls back on the first error.
        
        Args:
            conn: Database connection
            sql_query: SQL string containing multiple statements
            
        Returns:
            List of results for each statement (up to and including the error)
        """
        statements = parse_sql_statements(sql_query)
        results = []
        try:
            for i, stmt in enumerate(statements):
                # Use sqlparse to determine if statement returns rows
                stmt_type = detect_statement_type(stmt)
                
                if stmt_type == FETCH_STATEMENT:
                    # Execute as fetch operation
                    rows = self._fetch_with_connection(conn, stmt)
                    results.append({
                        'statement_index': i,
                        'statement': stmt,
                        'statement_type': FETCH_STATEMENT,
                        'result': rows,
                        'row_count': len(rows)
                    })
                else:
                    # Execute as non-SELECT operation
                    result = self._execute_with_connection(conn, stmt)
                    results.append({
                        'statement_index': i,
                        'statement': stmt,
                        'statement_type': EXECUTE_STATEMENT,
                        'result': result,
                        'row_count': None
                    })
            conn.commit()
        except Exception as e:
            conn.rollback()
            results.append({
                'statement_index': i,
                'statement': stmt,
                'statement_type': ERROR_STATEMENT,
                'error': str(e)
            })
        return results
    
    def batch(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute multiple SQL statements in a batch.
        
        Args:
            sql_query: SQL string containing one or more statements separated by semicolons.
                      Supports both DDL (CREATE, ALTER, DROP) and DML (INSERT, UPDATE, DELETE) statements.
                      Comments (-- and /* */) are automatically removed.            
                      
        Returns:
            List of dictionaries containing results for each statement:
                - 'statement_index': Index of the statement in the batch
                - 'statement': The actual SQL statement executed
                - 'statement_type': 'fetch', 'execute', or 'error'
                - 'result': Query results (for SELECT) or True (for other operations)
                - 'row_count': Number of rows affected/returned
                - 'error': Error message (only for failed statements)
                
        Raises:
            DbOperationError: If the batch operation fails entirely
            
        Example:
            batch_sql = '''
                -- Create a table
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );
                
                -- Insert some data
                INSERT INTO users (name) VALUES ('John');
                INSERT INTO users (name) VALUES ('Jane');
               
                -- Query the data
                SELECT * FROM users;
            '''
            results = db.batch(batch_sql)
        """
        try:
            with self._engine.connect() as conn:
                return self._execute_batch_statements(conn, sql_query)
        except Exception as e:
            raise DbOperationError(f"Batch operation failed: {str(e)}")
    
    def shutdown(self) -> None:
        """
        Shutdown the database engine.
        """
        self._engine.dispose()