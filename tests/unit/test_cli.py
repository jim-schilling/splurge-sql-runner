"""Clean, deterministic unit tests for the CLI.

These tests mock out configuration loading and the SQL processing function
so they run quickly and deterministically without touching a real database.
"""

import os
import tempfile

import pytest

import splurge_sql_runner.cli as cli_mod


def test_simple_table_format_empty():
    assert cli_mod.simple_table_format([], []) == "(No data)"


def test_simple_table_format_basic():
    headers = ["Name", "Age"]
    rows = [["Alice", "25"], ["Bob", "30"]]
    out = cli_mod.simple_table_format(headers, rows)
    assert "Alice" in out and "Bob" in out


def test_pretty_print_results_empty(mocker):
    mock_print = mocker.patch("builtins.print")
    cli_mod.pretty_print_results([])
    mock_print.assert_not_called()


def test_pretty_print_results_fetch(mocker):
    results = [
        {
            "statement_type": "fetch",
            "statement": "SELECT name FROM users;",
            "row_count": 2,
            "result": [{"name": "Alice"}, {"name": "Bob"}],
        }
    ]
    mock_print = mocker.patch("builtins.print")
    cli_mod.pretty_print_results(results)
    calls = [c[0][0] for c in mock_print.call_args_list]
    assert any("Rows returned" in str(c) for c in calls)


class TestCliMain:
    @pytest.fixture
    def temp_sql_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("SELECT 1;")
            fname = f.name

        yield fname

        try:
            os.unlink(fname)
        except OSError:
            pass

    @pytest.fixture
    def sqlite_db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_main_with_file_argument(self, temp_sql_file, sqlite_db_path, mocker):
        # Arrange: patch argv, load_config and process_sql_files to avoid DB work
        mocker.patch("sys.argv", new=["splurge_sql_runner", "-c", f"sqlite:///{sqlite_db_path}", "-f", temp_sql_file])
        mocker.patch.object(cli_mod, "load_config", return_value={})
        summary = {
            "results": {
                temp_sql_file: [{"statement_type": "noop", "statement": "SELECT 1;", "row_count": 0, "result": None}]
            },
            "files_processed": 1,
            "files_passed": 1,
            "files_failed": 0,
            "files_mixed": 0,
        }
        mocker.patch.object(cli_mod, "process_sql_files", return_value=summary)

        # Act / Assert
        assert cli_mod.main() == cli_mod.EXIT_CODE_SUCCESS

    def test_main_with_pattern_argument(self, temp_sql_file, sqlite_db_path, mocker):
        pattern = os.path.join(os.path.dirname(temp_sql_file), "*.sql")
        mocker.patch("sys.argv", new=["splurge_sql_runner", "-c", f"sqlite:///{sqlite_db_path}", "-p", pattern])
        mocker.patch.object(cli_mod, "load_config", return_value={})
        # Let process_sql_files report two files processed successfully
        summary = {
            "results": {"a": [], "b": []},
            "files_processed": 2,
            "files_passed": 2,
            "files_failed": 0,
            "files_mixed": 0,
        }
        mocker.patch.object(cli_mod, "process_sql_files", return_value=summary)
        assert cli_mod.main() == cli_mod.EXIT_CODE_SUCCESS

    def test_main_missing_file_and_pattern_raises_argparse(self, sqlite_db_path, mocker):
        mocker.patch("sys.argv", new=["splurge_sql_runner", "-c", f"sqlite:///{sqlite_db_path}"])
        with pytest.raises(SystemExit):
            # argparse.error will raise SystemExit
            cli_mod.main()

    def test_main_both_file_and_pattern_raises_argparse(self, temp_sql_file, sqlite_db_path, mocker):
        mocker.patch(
            "sys.argv",
            new=["splurge_sql_runner", "-c", f"sqlite:///{sqlite_db_path}", "-f", temp_sql_file, "-p", "*.sql"],
        )
        with pytest.raises(SystemExit):
            cli_mod.main()

    def test_main_nonexistent_file_returns_failure(self, sqlite_db_path, mocker):
        mocker.patch(
            "sys.argv", new=["splurge_sql_runner", "-c", f"sqlite:///{sqlite_db_path}", "-f", "nonexistent.sql"]
        )
        mocker.patch.object(cli_mod, "load_config", return_value={})
        # process_sql_files should not be called because file doesn't exist
        ret = cli_mod.main()
        assert ret == cli_mod.EXIT_CODE_FAILURE

    def test_main_security_validation_error_returns_failure(self, temp_sql_file, sqlite_db_path, mocker):
        mocker.patch("sys.argv", new=["splurge_sql_runner", "-c", f"sqlite:///{sqlite_db_path}", "-f", temp_sql_file])
        mocker.patch.object(cli_mod, "load_config", return_value={})
        from splurge_sql_runner.exceptions import SplurgeSqlRunnerSecurityError

        mocker.patch.object(
            cli_mod, "process_sql_files", side_effect=SplurgeSqlRunnerSecurityError("Too many sql statements")
        )
        ret = cli_mod.main()
        assert ret == cli_mod.EXIT_CODE_FAILURE
