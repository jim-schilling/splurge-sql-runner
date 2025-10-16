"""
Unit tests for result_models.py module.

Tests the typed result models and conversion utilities.
"""

from splurge_sql_runner.result_models import (
    StatementResult,
    StatementType,
    results_to_dicts,
    statement_result_to_dict,
)


class TestStatementType:
    """Test StatementType enum."""

    def test_statement_type_values(self):
        """Test that StatementType has correct values."""
        assert StatementType.FETCH == "fetch"
        assert StatementType.EXECUTE == "execute"
        assert StatementType.ERROR == "error"

    def test_statement_type_str_values(self):
        """Test that StatementType enum values are strings."""
        assert isinstance(StatementType.FETCH.value, str)
        assert isinstance(StatementType.EXECUTE.value, str)
        assert isinstance(StatementType.ERROR.value, str)


class TestStatementResult:
    """Test StatementResult dataclass."""

    def test_statement_result_creation(self):
        """Test creating a StatementResult instance."""
        result = StatementResult(
            statement="SELECT * FROM users",
            statement_type=StatementType.FETCH,
            result=[{"id": 1, "name": "Alice"}],
            row_count=1,
            file_path="test.sql",
        )

        assert result.statement == "SELECT * FROM users"
        assert result.statement_type == StatementType.FETCH
        assert result.result == [{"id": 1, "name": "Alice"}]
        assert result.row_count == 1
        assert result.file_path == "test.sql"
        assert result.error is None

    def test_statement_result_defaults(self):
        """Test StatementResult default values."""
        result = StatementResult(
            statement="INSERT INTO users VALUES (1, 'Bob')", statement_type=StatementType.EXECUTE, result=True
        )

        assert result.row_count is None
        assert result.error is None
        assert result.file_path is None

    def test_statement_result_error_case(self):
        """Test StatementResult for error cases."""
        result = StatementResult(
            statement="INVALID SQL", statement_type=StatementType.ERROR, result=None, error="Syntax error"
        )

        assert result.result is None
        assert result.row_count is None
        assert "Syntax error" in result.error


class TestStatementResultToDict:
    """Test statement_result_to_dict conversion function."""

    def test_fetch_result_conversion(self):
        """Test converting FETCH result to dict."""
        result = StatementResult(
            statement="SELECT * FROM users",
            statement_type=StatementType.FETCH,
            result=[{"id": 1, "name": "Alice"}],
            row_count=1,
        )

        dict_result = statement_result_to_dict(result)

        expected = {
            "statement": "SELECT * FROM users",
            "statement_type": "fetch",
            "result": [{"id": 1, "name": "Alice"}],
            "row_count": 1,
        }
        assert dict_result == expected

    def test_execute_result_conversion(self):
        """Test converting EXECUTE result to dict."""
        result = StatementResult(
            statement="INSERT INTO users VALUES (1, 'Bob')",
            statement_type=StatementType.EXECUTE,
            result=True,
            row_count=1,
        )

        dict_result = statement_result_to_dict(result)

        expected = {
            "statement": "INSERT INTO users VALUES (1, 'Bob')",
            "statement_type": "execute",
            "result": True,
            "row_count": 1,
        }
        assert dict_result == expected

    def test_error_result_conversion(self):
        """Test converting ERROR result to dict."""
        result = StatementResult(
            statement="INVALID SQL", statement_type=StatementType.ERROR, result=None, error="Syntax error near INVALID"
        )

        dict_result = statement_result_to_dict(result)

        expected = {"statement": "INVALID SQL", "statement_type": "error", "error": "Syntax error near INVALID"}
        assert dict_result == expected

    def test_result_with_file_path(self):
        """Test conversion includes file_path when present."""
        result = StatementResult(
            statement="SELECT 1",
            statement_type=StatementType.FETCH,
            result=[{"1": 1}],
            row_count=1,
            file_path="queries.sql",
        )

        dict_result = statement_result_to_dict(result)
        assert dict_result["file_path"] == "queries.sql"


class TestResultsToDicts:
    """Test results_to_dicts conversion function."""

    def test_converts_mixed_results(self):
        """Test converting mixed StatementResult and dict results."""
        typed_result = StatementResult(
            statement="SELECT 1", statement_type=StatementType.FETCH, result=[{"1": 1}], row_count=1
        )

        dict_result = {
            "statement": "INSERT INTO test VALUES (1)",
            "statement_type": "execute",
            "result": True,
            "row_count": 1,
        }

        results = results_to_dicts([typed_result, dict_result])

        assert len(results) == 2
        assert results[0]["statement"] == "SELECT 1"
        assert results[0]["statement_type"] == "fetch"
        assert results[1]["statement"] == "INSERT INTO test VALUES (1)"
        assert results[1]["statement_type"] == "execute"

    def test_converts_all_typed_results(self):
        """Test converting list of all StatementResult objects."""
        results = [
            StatementResult(
                statement="SELECT * FROM users", statement_type=StatementType.FETCH, result=[{"id": 1}], row_count=1
            ),
            StatementResult(
                statement="INSERT INTO users VALUES (2, 'Bob')",
                statement_type=StatementType.EXECUTE,
                result=True,
                row_count=1,
            ),
        ]

        dict_results = results_to_dicts(results)

        assert len(dict_results) == 2
        assert dict_results[0]["statement_type"] == "fetch"
        assert dict_results[1]["statement_type"] == "execute"

    def test_converts_all_dict_results(self):
        """Test converting list of all dict results."""
        results = [{"statement": "SELECT 1", "statement_type": "fetch", "result": [{"1": 1}], "row_count": 1}]

        dict_results = results_to_dicts(results)
        assert dict_results == results

    def test_empty_results_list(self):
        """Test converting empty results list."""
        results = results_to_dicts([])
        assert results == []
