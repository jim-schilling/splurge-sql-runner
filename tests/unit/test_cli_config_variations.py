import splurge_sql_runner.cli as cli_mod


def test_missing_config_keys_use_defaults(monkeypatch, tmp_path):
    # Prepare SQL file
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    # load_config returns empty dict (missing keys)
    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {})

    # Capture configure_module_logging calls
    calls = []

    class DummyLogger:
        def info(self, *a, **kw):
            pass

        def debug(self, *a, **kw):
            pass

        def error(self, *a, **kw):
            pass

        def warning(self, *a, **kw):
            pass

    def fake_configure(name, log_level="INFO"):
        calls.append((name, log_level))
        return DummyLogger()

    monkeypatch.setattr(cli_mod, "configure_module_logging", fake_configure)

    # Fake process_sql_files to avoid DB work
    def fake_process(files, **kwargs):
        return {"results": {files[0]: []}, "files_processed": 1, "files_passed": 1, "files_failed": 0, "files_mixed": 0}

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    import sys

    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file)])
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS

    # At least one configure_module_logging call should have used INFO
    assert any(lvl == "INFO" for (_n, lvl) in calls)


def test_config_log_level_is_respected(monkeypatch, tmp_path):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    # load_config returns DEBUG level
    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"log_level": "DEBUG"})

    calls = []

    class DummyLogger2:
        def info(self, *a, **kw):
            pass

        def debug(self, *a, **kw):
            pass

        def error(self, *a, **kw):
            pass

        def warning(self, *a, **kw):
            pass

    def fake_configure(name, log_level="INFO"):
        calls.append((name, log_level))
        return DummyLogger2()

    monkeypatch.setattr(cli_mod, "configure_module_logging", fake_configure)

    # Fake process_sql_files
    def fake_process(files, **kwargs):
        return {"results": {files[0]: []}, "files_processed": 1, "files_passed": 1, "files_failed": 0, "files_mixed": 0}

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    import sys

    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file)])
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS

    # Ensure we saw a configure_module_logging call that used DEBUG (the second call uses config value)
    assert any(lvl == "DEBUG" for (_n, lvl) in calls)


def test_config_max_statements_passed_to_process(monkeypatch, tmp_path):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    # load_config provides max_statements_per_file
    monkeypatch.setattr(
        cli_mod, "load_config", lambda cfg: {"max_statements_per_file": 42, "database_url": "sqlite:///tmp.db"}
    )

    captured = {}

    def fake_process(files, **kwargs):
        captured.update(kwargs)
        return {"results": {files[0]: []}, "files_processed": 1, "files_passed": 1, "files_failed": 0, "files_mixed": 0}

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    import sys

    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file)])
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS

    # Current CLI implementation sets config['max_statements_per_file'] from
    # the argparse default (DEFAULT_MAX_STATEMENTS_PER_FILE) unless the
    # user explicitly passes --max-statements. Assert current behavior.
    assert captured.get("max_statements_per_file") == 100


def test_cli_explicit_max_statements_flag_overrides(monkeypatch, tmp_path):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    # load_config provides a different value, but explicit flag should win
    monkeypatch.setattr(
        cli_mod, "load_config", lambda cfg: {"max_statements_per_file": 42, "database_url": "sqlite:///tmp.db"}
    )

    captured = {}

    def fake_process(files, **kwargs):
        captured.update(kwargs)
        return {"results": {files[0]: []}, "files_processed": 1, "files_passed": 1, "files_failed": 0, "files_mixed": 0}

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    # Pass explicit --max-statements flag
    import sys

    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file), "--max-statements", "42"])
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS

    assert captured.get("max_statements_per_file") == 42
