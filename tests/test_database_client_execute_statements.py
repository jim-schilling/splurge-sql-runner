"""
Unit tests for DatabaseClient.execute_statements API.
"""

import pytest

from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.config.database_config import DatabaseConfig


@pytest.fixture
def client() -> DatabaseClient:
    return DatabaseClient(DatabaseConfig(url="sqlite:///:memory:"))


def setup_simple_table(db: DatabaseClient) -> None:
    db.execute_batch("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT);")


@pytest.mark.unit
def test_execute_statements_stop_on_error_true(client: DatabaseClient):
    setup_simple_table(client)

    stmts = [
        "INSERT INTO t(v) VALUES ('ok1')",
        "INSERT INTO t(v, no_col) VALUES ('bad', 'x')",
        "INSERT INTO t(v) VALUES ('ok2')",
    ]

    results = client.execute_statements(stmts, stop_on_error=True)

    # one success then error, early return
    assert len(results) == 2
    assert results[0]["statement_type"] == "execute"
    assert results[1]["statement_type"] == "error"

    # verify rollback of the first insert
    count = client.execute_batch("SELECT COUNT(*) AS c FROM t;")
    assert count[0]["result"][0]["c"] == 0


@pytest.mark.unit
def test_execute_statements_continue_on_error(client: DatabaseClient):
    setup_simple_table(client)

    stmts = [
        "INSERT INTO t(v) VALUES ('ok1')",
        "INSERT INTO t(v, no_col) VALUES ('bad', 'x')",
        "INSERT INTO t(v) VALUES ('ok2')",
        "SELECT COUNT(*) AS c FROM t",
    ]

    results = client.execute_statements(stmts, stop_on_error=False)

    # expect: execute, error, execute, fetch
    assert len(results) == 4
    assert [r["statement_type"] for r in results] == [
        "execute",
        "error",
        "execute",
        "fetch",
    ]

    # two successful inserts should be committed
    assert results[-1]["result"][0]["c"] == 2


