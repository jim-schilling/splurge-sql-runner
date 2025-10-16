import sys

import pytest

import splurge_sql_runner.cli as cli_mod


def _make_summary_for_files(files):
    return {
        "results": {f: [] for f in files},
        "files_processed": len(files),
        "files_passed": len(files),
        "files_failed": 0,
        "files_mixed": 0,
    }


def test_verbose_flag_prints_found(monkeypatch, tmp_path, capsys):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})

    def fake_process(files, **kwargs):
        return _make_summary_for_files(files)

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)

    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file), "-v"])
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS
    captured = capsys.readouterr()
    assert "Found 1 file(s) to process" in captured.out


def test_json_flag_outputs_json(monkeypatch, tmp_path):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})

    def fake_process(files, **kwargs):
        # Return a fetch-style result to be serialized
        return {
            "results": {
                files[0]: [
                    {"statement_type": "fetch", "statement": "SELECT 1;", "row_count": 1, "result": [{"col": 1}]}
                ]
            },
            "files_processed": 1,
            "files_passed": 1,
            "files_failed": 0,
            "files_mixed": 0,
        }

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)
    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file), "--json"])
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS


def test_max_statements_and_continue_on_error_passed(monkeypatch, tmp_path):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    monkeypatch.setattr(cli_mod, "load_config", lambda cfg: {"database_url": "sqlite:///tmp.db"})

    captured = {}

    def fake_process(files, **kwargs):
        captured.update(kwargs)
        return _make_summary_for_files(files)

    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file), "--max-statements", "5", "--continue-on-error"],
    )
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS
    assert captured.get("max_statements_per_file") == 5
    # stop_on_error should be False when --continue-on-error is passed
    assert captured.get("stop_on_error") is False


@pytest.mark.parametrize("level", ["strict", "normal", "permissive"])
def test_security_level_passed_to_process(monkeypatch, tmp_path, level):
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    captured = {}

    def fake_load(cfg):
        return {"database_url": "sqlite:///tmp.db"}

    def fake_process(files, **kwargs):
        captured.update(kwargs)
        return _make_summary_for_files(files)

    monkeypatch.setattr(cli_mod, "load_config", fake_load)
    monkeypatch.setattr(cli_mod, "process_sql_files", fake_process)
    monkeypatch.setattr(sys, "argv", ["prog", "-c", "sqlite:///tmp.db", "-f", str(sql_file), "--security-level", level])
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS
    assert captured.get("security_level") == level


def test_config_file_argument_is_passed_to_load_config(monkeypatch, tmp_path):
    # Create a real config file path and ensure load_config receives it
    config_file = tmp_path / "cfg.json"
    config_file.write_text("{}")

    seen = {"arg": None}

    def fake_load(cfg):
        seen["arg"] = cfg
        return {"database_url": "sqlite:///tmp.db"}

    monkeypatch.setattr(cli_mod, "load_config", fake_load)
    sql_file = tmp_path / "one.sql"
    sql_file.write_text("SELECT 1;")

    monkeypatch.setattr(
        sys, "argv", ["prog", "--config", str(config_file), "-c", "sqlite:///tmp.db", "-f", str(sql_file)]
    )
    ret = cli_mod.main()
    assert ret == cli_mod.EXIT_CODE_SUCCESS
    assert seen["arg"] == str(config_file)
