"""
Shared entry points for CLI and API consumers.

Provides process_sql (for raw SQL strings or lists of statements) and
process_sql_files (for file paths). Both functions perform configuration
and security validation then call into DatabaseClient.execute_sql.

These functions deliberately raise library exceptions on fatal errors so
API consumers can handle them programmatically. The CLI will catch and
translate to exit codes and user-friendly prints.
"""

from __future__ import annotations

from typing import Any

from splurge_safe_io import SafeTextFileReader

from splurge_sql_runner import load_config
from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.exceptions import (
    SecurityValidationError,
)
from splurge_sql_runner.logging import configure_module_logging
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.sql_helper import parse_sql_statements

logger = configure_module_logging("main")


def process_sql(
    sql_content: str,
    *,
    database_url: str,
    config: dict | None = None,
    security_level: str = "normal",
    max_statements_per_file: int = 100,
    stop_on_error: bool = True,
) -> list[dict[str, Any]]:
    """Process raw SQL content block, validate it, then execute it.

    Args:
        sql_content: Single SQL content block.
        database_url: Database connection string.
        config: Optional configuration dict. If None, load defaults via load_config(None).
        security_level: Security validation level.
        max_statements_per_file: Max statements allowed in this SQL blob.
        stop_on_error: Whether to stop on first statement error.

    Returns:
        List of result dicts from DatabaseClient.execute_sql

    Raises:
        SecurityValidationError, SecurityUrlError, FileError
    """
    logger.debug("process_sql: starting")

    if config is None:
        config = load_config(None)

    # Validate database URL first
    SecurityValidator.validate_database_url(database_url, security_level)

    sql_stmts = parse_sql_statements(sql_content, strip_semicolon=False)

    SecurityValidator.validate_sql_content("\n".join(sql_stmts), security_level, max_statements_per_file)

    db_client = DatabaseClient(database_url=database_url, connection_timeout=config.get("connection_timeout", 30.0))

    try:
        results = db_client.execute_sql(sql_stmts, stop_on_error=stop_on_error)
        return results
    finally:
        try:
            db_client.close()
        except Exception:
            pass


def process_sql_files(
    file_paths: list[str],
    *,
    database_url: str,
    config: dict | None = None,
    security_level: str = "normal",
    max_statements_per_file: int = 100,
    stop_on_error: bool = True,
) -> dict[str, Any]:
    """Process one or more SQL files and execute them.

    Returns a summary dict with per-file results and counts.
    This function raises FileError if any file is missing/unreadable, and
    may raise SecurityValidationError for invalid SQL content.
    """
    logger.debug("process_sql_files: starting")

    if config is None:
        config = load_config(None)

    summary: dict[str, Any] = {
        "files_processed": 0,
        "files_passed": 0,
        "files_failed": 0,
        "files_mixed": 0,
        "results": {},
    }

    for fp in file_paths:
        try:
            reader = SafeTextFileReader(fp)
            content = reader.read()
            results = process_sql(
                content,
                database_url=database_url,
                config=config,
                security_level=security_level,
                max_statements_per_file=max_statements_per_file,
                stop_on_error=stop_on_error,
            )
            summary["files_processed"] += 1
            # Count success if none of the statement results are error
            batch_passed = all(r.get("statement_type") != "error" for r in results)
            batch_failed = all(r.get("statement_type") == "error" for r in results)
            if batch_passed:
                summary["files_passed"] += 1
            elif batch_failed:
                summary["files_failed"] += 1
            else:
                summary["files_mixed"] += 1
            summary["results"][fp] = results
        except SecurityValidationError:
            # Re-raise; caller (CLI or API) can decide how to handle
            raise
        except Exception as e:
            # Capture unexpected per-file errors into results
            summary["results"][fp] = [
                {
                    "statement": "",
                    "statement_type": "error",
                    "result": None,
                    "error": f"Unexpected error processing file {fp}: {e}",
                }
            ]

    return summary
