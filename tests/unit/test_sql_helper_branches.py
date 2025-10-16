"""
Unit tests for uncommon branches in detect_statement_type.
"""

import pytest

from splurge_sql_runner.sql_helper import detect_statement_type


@pytest.mark.unit
def test_values_returns_fetch():
    assert detect_statement_type("VALUES (1, 'A'), (2, 'B')") == "fetch"


@pytest.mark.unit
def test_describe_and_desc_return_fetch():
    assert detect_statement_type("DESCRIBE users") == "fetch"
    assert detect_statement_type("DESC users") == "fetch"


@pytest.mark.unit
def test_explain_and_show_and_pragma_return_fetch():
    assert detect_statement_type("EXPLAIN SELECT 1") == "fetch"
    assert detect_statement_type("SHOW TABLES") == "fetch"
    assert detect_statement_type("PRAGMA table_info(t)") == "fetch"


@pytest.mark.unit
def test_with_insert_is_execute_and_with_select_is_fetch():
    with_insert = "WITH new_data AS (SELECT 1 AS id) INSERT INTO t(id) SELECT id FROM new_data"
    with_select = "WITH s AS (SELECT 1 AS id) SELECT * FROM s"
    assert detect_statement_type(with_insert) == "execute"
    assert detect_statement_type(with_select) == "fetch"
