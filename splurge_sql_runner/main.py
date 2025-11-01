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

from . import load_config
from .database.database_client import DatabaseClient
from .exceptions import (
    SplurgeSqlRunnerSecurityError,
)
from .logging import configure_module_logging
from .security import SecurityValidator
from .sql_helper import parse_sql_statements
from .utils.file_io_adapter import FileIoAdapter

# Module domains
DOMAINS = ["api", "execution", "orchestration"]

__all__ = ["process_sql", "process_sql_files"]

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
        SplurgeSqlRunnerSecurityError
        SplurgeSqlRunnerFileError
        SplurgeSqlRunnerValueError
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

    Args:
        file_paths: List of file paths to process
        database_url: Database connection string
        config: Optional configuration dict. If None, load defaults via load_config(None).
        security_level: Security validation level.
        max_statements_per_file: Max statements allowed in this SQL blob.
        stop_on_error: Whether to stop on first statement error.

    Returns:
        Dictionary with per-file results and counts.

    Raises:
        SplurgeSqlRunnerSecurityError: If SQL content or database URL fails security validation
        SplurgeSqlRunnerFileError: If file cannot be read
        SplurgeSqlRunnerValueError: If validation fails (invalid security level, URL format, etc.)
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
            content = FileIoAdapter.read_file(fp, context_type="sql")
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
        except SplurgeSqlRunnerSecurityError:
            # Re-raise; caller (CLI or API) can decide how to handle
            raise
        except Exception as e:
            # Capture unexpected per-file errors into results
            logger.error(f"Processing failed for {fp}", exc_info=True)
            summary["results"][fp] = [
                {
                    "statement": "",
                    "statement_type": "error",
                    "result": None,
                    "error": f"Unexpected error processing file {fp}: {e}",
                }
            ]

    return summary
