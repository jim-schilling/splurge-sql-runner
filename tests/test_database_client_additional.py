"""
Additional tests for DatabaseClient behaviors.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.database.database_client import DatabaseClient


@pytest.mark.unit
def test_execute_batch_continue_on_error_persists_successes() -> None:
    client = DatabaseClient(DatabaseConfig(url="sqlite:///:memory:"))

    # First, create the table successfully
    client.execute_batch("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT);")

    # Now, attempt valid insert, invalid SQL, then valid insert with continue_on_error
    sql = (
        "INSERT INTO t (id, name) VALUES (1, 'a');"
        "INVALID SQL;"
        "INSERT INTO t (id, name) VALUES (2, 'b');"
    )
    results = client.execute_batch(sql, stop_on_error=False)

    # Expect three entries: execute, error, execute
    assert len(results) == 3
    assert results[0]["statement_type"] == "execute"
    assert results[1]["statement_type"] == "error"
    assert results[2]["statement_type"] == "execute"

    # Verify that both rows exist despite the middle failure
    select_results = client.execute_batch("SELECT * FROM t ORDER BY id;")
    assert len(select_results) == 1
    assert select_results[0]["statement_type"] == "fetch"
    assert select_results[0]["result"] == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]

    client.close()


@pytest.mark.unit
def test_execute_batch_stop_on_error_rolls_back_transaction() -> None:
    client = DatabaseClient(DatabaseConfig(url="sqlite:///:memory:"))

    # Attempt to create table then fail, then verify nothing committed
    sql = (
        "CREATE TABLE r (id INTEGER PRIMARY KEY);"
        "INVALID SQL;"
        "INSERT INTO r (id) VALUES (1);"
    )
    results = client.execute_batch(sql, stop_on_error=True)

    # Should stop at first error and return two entries
    assert len(results) == 2
    assert results[0]["statement_type"] == "execute"
    assert results[1]["statement_type"] == "error"

    # Table should not exist due to rollback
    introspect = client.execute_batch("SELECT name FROM sqlite_master WHERE type='table' AND name='r';")
    # Fetch with zero rows
    assert len(introspect) == 1
    assert introspect[0]["statement_type"] == "fetch"
    assert introspect[0]["row_count"] == 0
    assert introspect[0]["result"] == []

    client.close()


@pytest.mark.unit
def test_rowcount_populated_for_dml() -> None:
    client = DatabaseClient(DatabaseConfig(url="sqlite:///:memory:"))
    client.execute_batch("CREATE TABLE m (id INTEGER PRIMARY KEY, v INT);")
    res = client.execute_batch(
        "INSERT INTO m (id, v) VALUES (1, 10); UPDATE m SET v = 11 WHERE id = 1;"
    )
    # First execute (INSERT) may have rowcount -1 in some drivers; we allow None
    assert res[0]["statement_type"] == "execute"
    assert "row_count" in res[0]
    # UPDATE should report affected rows when available (SQLite returns 1)
    assert res[1]["statement_type"] == "execute"
    assert res[1]["row_count"] in (1, None)
    client.close()


@pytest.mark.unit
def test_execute_statements_list_and_semicolon_trimming(tmp_path: Path) -> None:
    client = DatabaseClient(DatabaseConfig(url=f"sqlite:///{tmp_path / 'db.sqlite'}"))
    stmts = [
        "CREATE TABLE s (id INT);",
        "INSERT INTO s (id) VALUES (1);",
        "SELECT * FROM s;",
    ]
    results = client.execute_statements(stmts)
    assert len(results) == 3
    assert results[0]["statement_type"] == "execute"
    assert results[1]["statement_type"] == "execute"
    assert results[2]["statement_type"] == "fetch"
    assert results[2]["result"] == [{"id": 1}]
    client.close()


@pytest.mark.unit
def test_database_client_context_manager(tmp_path: Path) -> None:
    # Ensure context manager works and closes engine on exit
    with DatabaseClient(DatabaseConfig(url=f"sqlite:///{tmp_path / 'ctx.sqlite'}")) as client:
        res = client.execute_batch("SELECT 1 as x;")
        assert res and res[0]["result"] == [{"x": 1}]
    # Exiting context should dispose engine; explicit close is idempotent
    client.close()  # idempotent


