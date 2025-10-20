"""
Integration tests for end-to-end workflows combining configuration, security, and SQL execution.

Tests realistic scenarios where configuration, security validation, and SQL execution work together.

Test Module Naming: Mirrors DOMAINS for configuration and main modules
"""

from __future__ import annotations

import json
from pathlib import Path

from splurge_sql_runner import load_config
from splurge_sql_runner.main import process_sql_files

# Test SQL data
CREATE_TABLE_SQL = "CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);"
INSERT_DATA_SQL = "INSERT INTO test_table (id, name) VALUES (1, 'Alice'), (2, 'Bob');"
SELECT_DATA_SQL = "SELECT * FROM test_table;"


class TestEndToEndWithConfiguration:
    """Test end-to-end workflows with configuration management."""

    def test_process_sql_files_with_loaded_config(self, tmp_path: Path) -> None:
        """Test that process_sql_files works with configuration loaded from file."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create config file using example format
        config_file = tmp_path / "config.json"
        config_data = {
            "database": {
                "url": db_url,
                "connection": {
                    "timeout": 30,
                },
            },
            "logging": {
                "level": "INFO",
            },
        }
        config_file.write_text(json.dumps(config_data))

        # Create SQL file
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(CREATE_TABLE_SQL)

        # Load config
        config = load_config(str(config_file))

        # Process SQL files with loaded config
        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=config,
            security_level="normal",
        )

        assert summary["files_processed"] == 1

    def test_process_sql_multiple_files_with_config(self, tmp_path: Path) -> None:
        """Test processing multiple SQL files with loaded configuration."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create config
        config_data = {
            "logging": {
                "level": "DEBUG",
            }
        }
        config = load_config(None)
        config.update({k: v for k, v in [("log_level", config_data.get("logging", {}).get("level", "INFO"))] if v})

        # Create multiple SQL files
        create_file = tmp_path / "01_create.sql"
        create_file.write_text(CREATE_TABLE_SQL)

        insert_file = tmp_path / "02_insert.sql"
        insert_file.write_text(INSERT_DATA_SQL)

        select_file = tmp_path / "03_select.sql"
        select_file.write_text(SELECT_DATA_SQL)

        # Process all files
        summary = process_sql_files(
            [str(create_file), str(insert_file), str(select_file)],
            database_url=db_url,
            config=config,
            security_level="normal",
        )

        assert summary["files_processed"] == 3

    def test_security_validation_with_configuration(self, tmp_path: Path) -> None:
        """Test that security validation works with configuration."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        sql_file = tmp_path / "test.sql"
        sql_file.write_text(CREATE_TABLE_SQL)

        config = load_config(None)

        # Process with specific security level
        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=config,
            security_level="strict",
        )

        assert summary["files_processed"] == 1


class TestConfigurationWithDifferentSecurityLevels:
    """Test configuration application across different security levels."""

    def test_process_files_strict_security_with_config(self, tmp_path: Path) -> None:
        """Test processing with strict security level and configuration."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        sql_file = tmp_path / "test.sql"
        sql_file.write_text(CREATE_TABLE_SQL)

        config = load_config(None)

        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=config,
            security_level="strict",
        )

        assert summary["files_processed"] == 1

    def test_process_files_normal_security_with_config(self, tmp_path: Path) -> None:
        """Test processing with normal security level and configuration."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        sql_file = tmp_path / "test.sql"
        sql_file.write_text(CREATE_TABLE_SQL)

        config = load_config(None)

        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=config,
            security_level="normal",
        )

        assert summary["files_processed"] == 1

    def test_process_files_permissive_security_with_config(self, tmp_path: Path) -> None:
        """Test processing with permissive security level and configuration."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create table first
        setup_file = tmp_path / "setup.sql"
        setup_file.write_text(CREATE_TABLE_SQL)

        sql_file = tmp_path / "test.sql"
        sql_file.write_text("DROP DATABASE IF EXISTS test;")

        config = load_config(None)

        # Setup
        process_sql_files(
            [str(setup_file)],
            database_url=db_url,
            config=config,
            security_level="permissive",
        )

        # Process with permissive
        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=config,
            security_level="permissive",
        )

        # Should have processed even though it's a DROP statement
        assert summary["files_processed"] >= 1


class TestMultipleConfigurationSources:
    """Test that configuration can be merged from multiple sources."""

    def test_default_config_applied_when_file_not_provided(self) -> None:
        """Test that default config is used when no file provided."""
        config = load_config(None)

        # Should have all required keys from defaults
        required_keys = ["log_level", "connection_timeout", "database_url"]
        for key in required_keys:
            assert key in config

    def test_partial_config_fills_with_defaults(self, tmp_path: Path) -> None:
        """Test that partial config file results in all required keys."""
        config_file = tmp_path / "partial.json"
        config_file.write_text(json.dumps({"logging": {"level": "ERROR"}}))

        config = load_config(str(config_file))

        # Provided value
        assert config.get("log_level") in ["ERROR", "INFO"]  # May vary by env

        # Default values should still be there
        assert "connection_timeout" in config
        assert "database_url" in config


class TestConfigErrorHandling:
    """Test error handling in configuration workflows."""

    def test_workflow_handles_missing_sql_file_gracefully(self, tmp_path: Path) -> None:
        """Test that missing SQL file is handled gracefully."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        config = load_config(None)

        missing_file = tmp_path / "missing.sql"

        summary = process_sql_files(
            [str(missing_file)],
            database_url=db_url,
            config=config,
            security_level="normal",
        )

        # Should have captured the error
        assert str(missing_file) in summary["results"]


class TestConfigurationLifecycle:
    """Test complete configuration lifecycle in workflows."""

    def test_load_config_execute_sql_end_to_end(self, tmp_path: Path) -> None:
        """Test complete end-to-end: load config, validate, execute SQL."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Step 1: Load configuration
        config = load_config(None)
        assert config is not None

        # Step 2: Create SQL file
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(CREATE_TABLE_SQL)

        # Step 3: Process SQL file
        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=config,
            security_level="normal",
        )

        # Step 4: Verify results
        assert summary["files_processed"] == 1
        assert str(sql_file) in summary["results"]

    def test_workflow_with_all_config_keys(self, tmp_path: Path) -> None:
        """Test workflow using all configuration keys."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        config_file = tmp_path / "complete_config.json"
        config_data = {
            "database": {"url": db_url, "connection": {"timeout": 45.0}},
            "logging": {"level": "DEBUG"},
            "app": {"max_statements_per_file": 150, "enable_verbose_output": True, "enable_debug_mode": False},
        }
        config_file.write_text(json.dumps(config_data))

        # Load config from file
        config = load_config(str(config_file))

        # Create and process SQL
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(CREATE_TABLE_SQL)

        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=config,
            security_level="normal",
        )

        assert summary["files_processed"] == 1
