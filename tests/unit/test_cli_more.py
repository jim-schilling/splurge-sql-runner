import sys

import splurge_sql_runner.cli as cli_mod
from splurge_sql_runner.exceptions import (
    DatabaseError,
    SecurityValidationError,
)


def run_with_argv(argv, monkeypatch):
    """Helper to run cli.main() with a temporary argv and capture SystemExit."""
    monkeypatch.setattr(sys, "argv", argv)
    # main() now returns an int code; argparse may still raise SystemExit for invalid args
    try:
        return cli_mod.main()
    except SystemExit as exc:
        # argparse or other code may raise SystemExit; surface the code
        return int(exc.code) if exc.code is not None else 1


def test_no_file_or_pattern_causes_argparse_error(monkeypatch, capsys):
    code = run_with_argv(["prog", "-c", "sqlite:///tmp.db"], monkeypatch)
    # argparse will call SystemExit with non-zero code
    assert code != 0
    captured = capsys.readouterr()
    assert "Either -f/--file or -p/--pattern must be specified" in captured.err


def test_both_file_and_pattern_error(monkeypatch, capsys):
    code = run_with_argv(["prog", "-c", "sqlite:///tmp.db", "-f", "a.sql", "-p", "*.sql"], monkeypatch)
    assert code != 0
    captured = capsys.readouterr()
    # argparse prints a specific error
    assert "not allowed with argument -f/--file" in captured.err


def test_file_does_not_exist_raises_fileerror(monkeypatch, tmp_path, capsys):
    # Ensure the file path does not exist
    fake_file = tmp_path / "nope.sql"
    # Patch load_config to return a basic config
    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})

    code = run_with_argv(["prog", "-c", "sqlite:///tmp.db", "-f", str(fake_file)], monkeypatch)
    # Our CLI returns RETCODE_FAILED (1) on file errors
    assert code == cli_mod.EXIT_CODE_FAILURE
    captured = capsys.readouterr()
    assert "ERROR: File error" in captured.out or "File error" in captured.err


def test_pattern_no_matches_raises_fileerror(monkeypatch, tmp_path):
    # Create a pattern that matches nothing
    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})
    code = run_with_argv(["prog", "-c", "sqlite:///tmp.db", "-p", str(tmp_path / "*.nope")], monkeypatch)
    assert code == cli_mod.EXIT_CODE_FAILURE


def test_successful_processing_exits_zero(monkeypatch, tmp_path, capsys):
    # Create a dummy SQL file
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    # Patch load_config to return config
    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db", "log_level": "INFO"})

    # Patch process_sql_files to return a successful summary
    def fake_process(files, database_url, config, security_level, max_statements_per_file, stop_on_error):
        # Return a single statement result in the shape expected by pretty_print_results
        per_file_results = [
            {
                "file_path": str(files[0]),
                "statement_type": "execute",
                "statement": "SELECT 1;",
                "row_count": None,
            }
        ]

        return {
            "results": {files[0]: per_file_results},
            "files_processed": 1,
            "files_passed": 1,
            "files_failed": 0,
            "files_mixed": 0,
            "success_count": 1,
        }

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    code = run_with_argv(["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file)], monkeypatch)
    assert code == cli_mod.EXIT_CODE_SUCCESS
    captured = capsys.readouterr()
    assert "Summary:" in captured.out


def test_security_validation_error_prints_guidance_and_exits(monkeypatch, tmp_path, capsys):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("DROP DATABASE;")

    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})

    def fake_process(*_args, **_kwargs):
        raise SecurityValidationError("Too many SQL statements in file")

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    code = run_with_argv(["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file)], monkeypatch)
    assert code == cli_mod.EXIT_CODE_FAILURE
    captured = capsys.readouterr()
    assert "Security validation failed" in captured.out or "Security validation failed" in captured.err


def test_database_error_exits_one(monkeypatch, tmp_path, capsys):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT BAD;")

    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})

    def fake_process(*_args, **_kwargs):
        raise DatabaseError("connection failed")

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    code = run_with_argv(["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file)], monkeypatch)
    assert code == cli_mod.EXIT_CODE_FAILURE
    captured = capsys.readouterr()
    assert "ERROR: Database error" in captured.out or "Database error" in captured.err
