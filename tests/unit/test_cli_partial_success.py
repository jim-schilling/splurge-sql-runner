import splurge_sql_runner.cli as cli_mod


def test_cli_partial_success_exit_code(monkeypatch, tmp_path, capsys):
    # Create two sql files
    f1 = tmp_path / "a.sql"
    f1.write_text("SELECT 1;")
    f2 = tmp_path / "b.sql"
    f2.write_text("SELECT 2;")

    # Make load_config return basic config
    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})

    # Fake process_sql_files returns mixed results (one error, one success)
    def fake_process(files, **kwargs):
        results = {
            str(files[0]): [{"statement": "SELECT 1;", "statement_type": "execute", "row_count": 1}],
            str(files[1]): [{"statement": "SELECT 2;", "statement_type": "error", "error": "boom"}],
        }
        return {"results": results, "files_processed": 2, "files_passed": 1, "files_failed": 0, "files_mixed": 1}

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)
    import sys

    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-p", str(tmp_path / "*.sql")])

    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_PARTIAL_SUCCESS
    out = capsys.readouterr().out
    assert "Summary:" in out
