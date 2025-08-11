#!/usr/bin/env python3
"""
Command-line interface for splurge-sql-runner.

Provides CLI functionality for executing SQL files against databases with
support for single files, file patterns, and verbose output modes.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import argparse
import glob
import sys
from pathlib import Path
from typing import List, Dict, Any

from splurge_sql_runner.config import ConfigManager
from splurge_sql_runner.config.constants import (
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_MAX_STATEMENTS_PER_FILE,
)
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.database.engines import UnifiedDatabaseEngine
from splurge_sql_runner.errors import (
    CliError,
    CliArgumentError,
    CliFileError,
    CliExecutionError,
    CliSecurityError,
    SqlFileError,
    SqlValidationError,
    DatabaseConnectionError,
    DatabaseBatchError,
    DatabaseEngineError,
    SecurityValidationError,
    SecurityUrlError,
)
from splurge_sql_runner.logging import configure_module_logging
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.sql_helper import split_sql_file
from tabulate import tabulate


# Private constants
_DEFAULT_COLUMN_WIDTH: int = 10
_SEPARATOR_LENGTH: int = 60
_DASH_SEPARATOR_LENGTH: int = 40
_STATEMENT_TYPE_ERROR: str = "error"
_STATEMENT_TYPE_FETCH: str = "fetch"
_STATEMENT_TYPE_EXECUTE: str = "execute"
_DEFAULT_LOG_LEVEL: str = "DEBUG"
_ERROR_EMOJI: str = "❌"
_SUCCESS_EMOJI: str = "✅"
_WARNING_EMOJI: str = "⚠️"
_NO_ROWS_MESSAGE: str = "(No rows returned)"
_SUCCESS_MESSAGE: str = "Statement executed successfully"


"""
CLI for splurge-sql-runner

Usage:
    python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql"
    python -m splurge_sql_runner -c "sqlite:///database.db" -p "*.sql"
"""


def simple_table_format(
    headers: List[str],
    rows: List[List],
) -> str:
    """
    Simple table formatting when tabulate is not available.

    Args:
        headers: List of column headers
        rows: List of rows (each row is a list of values)

    Returns:
        Formatted table string
    """
    if not headers or not rows:
        return "(No data)"

    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(str(header))
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)

    lines = []

    header_line = "|"
    separator_line = "|"
    for header, width in zip(headers, col_widths):
        header_line += f" {str(header):<{width-1}}|"
        separator_line += "-" * width + "|"

    lines.append(header_line)
    lines.append(separator_line)

    for row in rows:
        row_line = "|"
        for i, value in enumerate(row):
            width = col_widths[i] if i < len(col_widths) else _DEFAULT_COLUMN_WIDTH
            row_line += f" {str(value):<{width-1}}|"
        lines.append(row_line)

    return "\n".join(lines)


def pretty_print_results(
    results: List[Dict[str, Any]],
    file_path: str | None = None,
) -> None:
    """
    Pretty print the results of SQL execution.

    Args:
        results: List of result dictionaries from UnifiedDatabaseEngine.batch()
        file_path: Optional file path for context
    """
    if file_path:
        print(f"\n{'='*_SEPARATOR_LENGTH}")
        print(f"Results for: {file_path}")
        print(f"{'='*_SEPARATOR_LENGTH}")

    for i, result in enumerate(results):
        print(f"\nStatement {i + 1}:")
        print(f"Type: {result['statement_type']}")
        print(f"SQL: {result['statement']}")

        if result["statement_type"] == _STATEMENT_TYPE_ERROR:
            print(f"{_ERROR_EMOJI} Error: {result['error']}")
        elif result["statement_type"] == _STATEMENT_TYPE_FETCH:
            print(f"{_SUCCESS_EMOJI} Rows returned: {result['row_count']}")
            if result["result"]:
                headers = list(result["result"][0].keys()) if result["result"] else []
                rows = [list(row.values()) for row in result["result"]]

                print(tabulate(rows, headers=headers, tablefmt="grid"))
            else:
                print(_NO_ROWS_MESSAGE)
        elif result["statement_type"] == _STATEMENT_TYPE_EXECUTE:
            print(f"{_SUCCESS_EMOJI} {_SUCCESS_MESSAGE}")

        print("-" * _DASH_SEPARATOR_LENGTH)


def process_sql_file(
    db_engine: UnifiedDatabaseEngine,
    file_path: str,
    security_config: SecurityConfig,
    *,
    verbose: bool = False,
    disable_security: bool = False,
) -> bool:
    """
    Process a single SQL file and execute its statements.

    Args:
        db_engine: Database engine instance
        file_path: Path to SQL file
        security_config: Security configuration
        verbose: Whether to print verbose output
        disable_security: Whether to disable security validation

    Returns:
        True if successful, False otherwise
    """
    logger = configure_module_logging("cli.process_sql_file")

    try:
        logger.debug(f"Starting to process SQL file: {file_path}")
        if not disable_security:
            logger.debug("Performing file path security validation")
            try:
                SecurityValidator.validate_file_path(file_path, security_config)
                logger.debug("File path security validation passed")
            except ValueError as e:
                logger.error(f"File path security validation failed: {e}")
                raise CliSecurityError(str(e))
        else:
            logger.warning(f"Security validation disabled for file: {file_path}")
            if verbose:
                print(f"{_WARNING_EMOJI}  Security validation disabled for file: {file_path}")

        if verbose:
            print(f"Processing file: {file_path}")

        logger.debug("Splitting SQL file into statements")
        statements = split_sql_file(file_path, strip_semicolon=False)
        logger.debug(f"Found {len(statements)} SQL statements")

        if not statements:
            logger.warning(f"No valid SQL statements found in {file_path}")
            if verbose:
                print(f"No valid SQL statements found in {file_path}")
            return True

        sql_content = ";\n".join(statements) + ";"
        logger.debug(f"Combined SQL content length: {len(sql_content)} characters")

        if not disable_security:
            logger.debug("Performing SQL content security validation")
            try:
                SecurityValidator.validate_sql_content(sql_content, security_config)
                logger.debug("SQL content security validation passed")
            except ValueError as e:
                logger.error(f"SQL content security validation failed: {e}")
                raise CliSecurityError(str(e))
        else:
            logger.warning(f"SQL content validation disabled for file: {file_path}")
            if verbose:
                print(f"⚠️  SQL content validation disabled for file: {file_path}")

        logger.info(f"Executing {len(statements)} SQL statements from file: {file_path}")
        results = db_engine.batch(sql_content)
        logger.debug(f"Batch execution completed with {len(results)} result sets")

        pretty_print_results(results, file_path)
        logger.info(f"Successfully processed file: {file_path}")

        return True

    except CliSecurityError as e:
        logger.error(f"Security error processing {file_path}: {e}")
        print(f"❌ Security error processing {file_path}: {e}")
        return False
    except (SqlFileError, SqlValidationError) as e:
        logger.error(f"SQL file error processing {file_path}: {e}")
        print(f"❌ SQL file error processing {file_path}: {e}")
        return False
    except (DatabaseConnectionError, DatabaseBatchError) as e:
        logger.error(f"Database error processing {file_path}: {e}")
        print(f"❌ Database error processing {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
        print(f"❌ Unexpected error processing {file_path}: {e}")
        return False


def main() -> None:
    """Main CLI entry point."""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    
    log_level = _DEFAULT_LOG_LEVEL
    logger = configure_module_logging("cli", log_level=log_level)

    logger.info("Starting splurge-sql-runner CLI")
    parser = argparse.ArgumentParser(
        description="Execute SQL files against a database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c "sqlite:///test.db" -f "script.sql"
  %(prog)s -c "postgresql://user:pass@localhost/db" -p "*.sql"
  %(prog)s -c "mysql://user:pass@localhost/db" -f "setup.sql" -v
        """,
    )

    parser.add_argument(
        "-c",
        "--connection",
        required=True,
        help="Database connection string (e.g., sqlite:///database.db)",
    )

    parser.add_argument("-f", "--file", help="Single SQL file to execute")

    parser.add_argument(
        "-p",
        "--pattern",
        help='File pattern to match multiple SQL files (e.g., "*.sql")',
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable SQLAlchemy debug mode",
    )

    parser.add_argument(
        "--disable-security",
        action="store_true",
        help="Disable security validation (not recommended)",
    )

    parser.add_argument(
        "--max-file-size",
        type=int,
        default=DEFAULT_MAX_FILE_SIZE_MB,
        help=f"Maximum file size in MB (default: {DEFAULT_MAX_FILE_SIZE_MB})",
    )

    parser.add_argument(
        "--max-statements",
        type=int,
        default=DEFAULT_MAX_STATEMENTS_PER_FILE,
        help=f"Maximum statements per file (default: {DEFAULT_MAX_STATEMENTS_PER_FILE})",
    )

    args = parser.parse_args()

    logger.debug(
        f"CLI arguments: file={args.file}, pattern={args.pattern}, "
        f"verbose={args.verbose}, debug={args.debug}"
    )

    if not args.file and not args.pattern:
        logger.error("Neither file nor pattern specified")
        parser.error("Either -f/--file or -p/--pattern must be specified")

    if args.file and args.pattern:
        logger.error("Both file and pattern specified")
        parser.error("Cannot specify both -f/--file and -p/--pattern")

    try:
        config_manager = ConfigManager()
        cli_config = {
            "database_url": args.connection,
            "max_file_size": args.max_file_size,
            "max_statements_per_file": args.max_statements,
        }
        config = config_manager.load_config(cli_config)
        
        if not args.disable_security:
            logger.info("Performing security validation")
            try:
                SecurityValidator.validate_database_url(args.connection, config.security)
                logger.debug("Security validation passed")
            except (SecurityValidationError, SecurityUrlError) as e:
                logger.error(f"Security validation failed: {e}")
                raise CliSecurityError(str(e))
        else:
            logger.warning(
                "Security validation disabled - this is not recommended for production use"
            )
            print("⚠️  Security validation disabled - this is not recommended for production use")

        logger.info(f"Initializing database engine for connection: {args.connection}")
        if args.verbose:
            print(f"Connecting to database: {args.connection}")

        db_config = DatabaseConfig(
            url=args.connection,
            enable_debug=args.debug,
        )
        db_engine = UnifiedDatabaseEngine(db_config)
        logger.info("Database engine initialized successfully")

        files_to_process = []

        if args.file:
            logger.info(f"Processing single file: {args.file}")
            if not Path(args.file).exists():
                logger.error(f"File not found: {args.file}")
                raise CliFileError(f"File not found: {args.file}")
            files_to_process = [args.file]
        elif args.pattern:
            logger.info(f"Processing files matching pattern: {args.pattern}")
            files_to_process = glob.glob(args.pattern)
            if not files_to_process:
                logger.error(f"No files found matching pattern: {args.pattern}")
                raise CliFileError(f"No files found matching pattern: {args.pattern}")
            files_to_process.sort()
            logger.debug(f"Found {len(files_to_process)} files matching pattern")

        if args.verbose:
            print(f"Found {len(files_to_process)} file(s) to process")

        success_count = 0
        logger.info(f"Starting to process {len(files_to_process)} files")

        for file_path in files_to_process:
            logger.info(f"Processing file: {file_path}")
            verbose = args.verbose
            disable_security = args.disable_security
            success = process_sql_file(
                db_engine,
                file_path,
                config.security,
                verbose=verbose,
                disable_security=disable_security,
            )
            if success:
                success_count += 1
                logger.info(f"Successfully processed file: {file_path}")
            else:
                logger.error(f"Failed to process file: {file_path}")

        logger.info(
            f"Processing complete: {success_count}/{len(files_to_process)} files processed successfully"
        )
        print(f"\n{'='*60}")
        print(f"Summary: {success_count}/{len(files_to_process)} files processed successfully")
        print(f"{'='*60}")

        if success_count < len(files_to_process):
            logger.error("Some files failed to process. Exiting with error code 1")
            sys.exit(1)

    except (DatabaseEngineError, DatabaseConnectionError, DatabaseBatchError) as e:
        logger.error(f"Database error: {e}")
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except (SqlFileError, SqlValidationError) as e:
        logger.error(f"SQL file error: {e}")
        print(f"❌ SQL file error: {e}")
        sys.exit(1)
    except CliSecurityError as e:
        logger.error(f"Security error: {e}")
        print(f"❌ Security error: {e}")
        sys.exit(1)
    except CliFileError as e:
        logger.error(f"CLI file error: {e}")
        print(f"❌ CLI file error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        if "db_engine" in locals():
            logger.info("Closing database engine")
            db_engine.close()
        logger.info("splurge-sql-runner CLI completed")


if __name__ == "__main__":
    main()
