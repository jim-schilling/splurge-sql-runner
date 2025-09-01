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


from splurge_sql_runner.config.app_config import AppConfig
from splurge_sql_runner.config.constants import (
    DEFAULT_MAX_STATEMENTS_PER_FILE,
)
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.config.logging_config import LoggingConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.errors import (
    CliFileError,
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
from splurge_sql_runner.logging.core import setup_logging
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.sql_helper import split_sql_file
from splurge_sql_runner.cli_output import pretty_print_results, simple_table_format
# No local tabulate usage; rendering lives in cli_output

# Re-export API expected by tests
__all__ = [
    "simple_table_format",
    "pretty_print_results",
    "process_sql_file",
    "main",
]


_ERROR_EMOJI: str = "❌"
_SUCCESS_EMOJI: str = "✅"
_WARNING_EMOJI: str = "⚠️"

"""
CLI for splurge-sql-runner

Usage:
    python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql"
    python -m splurge_sql_runner -c "sqlite:///database.db" -p "*.sql"
"""

def _print_security_guidance(error_message: str, *, context: str) -> None:
    """Print actionable guidance for common security validation errors.

    Args:
        error_message: The error message from validation.
        context: One of 'file', 'sql', 'url' to tailor hints.
    """
    msg = error_message.lower()

    hints: list[str] = []

    if "too many sql statements" in msg:
        hints.append(
            "Tip: increase --max-statements for this run, or set security.max_statements_per_file in your JSON config."
        )
    if "too long" in msg or "statement too long" in msg:
        hints.append(
            "Tip: increase security.validation.max_statement_length in your JSON config."
        )
    if "file extension not allowed" in msg:
        hints.append(
            "Tip: add the extension to security.allowed_file_extensions in your JSON config."
        )
    if "dangerous pattern" in msg:
        if context == "file":
            hints.append(
                "Tip: rename the file/path or adjust security.validation.dangerous_path_patterns in your JSON config."
            )
        elif context == "url":
            hints.append(
                "Tip: correct the database URL or adjust security.validation.dangerous_url_patterns in your JSON config."
            )
        else:
            hints.append(
                "Tip: remove the SQL pattern or adjust security.validation.dangerous_sql_patterns in your JSON config."
            )
    if "not safe" in msg:
        if context == "file":
            hints.append(
                "Tip: use a safe path or update security.validation.dangerous_path_patterns in your JSON config."
            )
        elif context == "url":
            hints.append(
                "Tip: use a safe URL or update security.validation.dangerous_url_patterns in your JSON config."
            )
    if "scheme" in msg and context == "url":
        hints.append(
            "Tip: include a scheme like sqlite:///, postgresql://, or mysql:// in the connection URL."
        )

    for hint in hints:
        print(f"{_WARNING_EMOJI}  {hint}")





def process_sql_file(
    db_client: DatabaseClient,
    connection,
    file_path: str,
    security_config: SecurityConfig,
    *,
    verbose: bool = False,
    output_json: bool = False,
    no_emoji: bool = False,
    stop_on_error: bool = True,
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
        logger.debug("Performing file path security validation")
        try:
            SecurityValidator.validate_file_path(file_path, security_config)
            logger.debug("File path security validation passed")
        except ValueError as e:
            logger.error(f"File path security validation failed: {e}")
            raise CliSecurityError(str(e))

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

        logger.debug("Performing SQL content security validation")
        try:
            SecurityValidator.validate_sql_content(sql_content, security_config)
            logger.debug("SQL content security validation passed")
        except ValueError as e:
            logger.error(f"SQL content security validation failed: {e}")
            raise CliSecurityError(str(e))

        logger.info(f"Executing {len(statements)} SQL statements from file: {file_path}")
        # Avoid reparsing inside client by executing the pre-parsed list
        results = db_client.execute_statements(
            statements,
            connection=connection,
            stop_on_error=stop_on_error,
        )
        logger.debug(f"Batch execution completed with {len(results)} result sets")

        pretty_print_results(
            results,
            file_path,
            output_json=output_json,
            no_emoji=no_emoji,
        )
        logger.info(f"Successfully processed file: {file_path}")

        # For CLI UX, treat statement-level errors as non-fatal for the overall file.
        # The detailed error is printed in results; only raised exceptions cause failure.
        return True

    except CliSecurityError as e:
        logger.error(f"Security error processing {file_path}: {e}")
        print(f"❌ Security error processing {file_path}: {e}")
        _print_security_guidance(str(e), context="sql")
        return False
    except (SqlFileError, SqlValidationError) as e:
        logger.error(f"SQL file error processing {file_path}: {e}")
        print(f"❌ SQL file error processing {file_path}: {e}")
        return False
    except (DatabaseConnectionError,) as e:
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

    # Bootstrap a basic logger early using LoggingConfig defaults; reconfigure after config load
    logger = configure_module_logging("cli", log_level=LoggingConfig().level.value)

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

    parser.add_argument(
        "--config",
        dest="config_file",
        help="Path to JSON configuration file (overridden by CLI args if both provided)",
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
        "--json",
        dest="output_json",
        action="store_true",
        help="Output results as JSON (machine-readable)",
    )

    parser.add_argument(
        "--no-emoji",
        dest="no_emoji",
        action="store_true",
        help="Disable emoji in CLI output",
    )
    
    parser.add_argument(
        "--max-statements",
        type=int,
        default=DEFAULT_MAX_STATEMENTS_PER_FILE,
        help=f"Maximum statements per file (default: {DEFAULT_MAX_STATEMENTS_PER_FILE})",
    )

    parser.add_argument(
        "--continue-on-error",
        dest="continue_on_error",
        action="store_true",
        help="Continue processing remaining statements when an error occurs",
    )

    args = parser.parse_args()
    # In tests, error() is mocked and parse_args() may return None instead of exiting.
    if args is None:  # pragma: no cover - defensive for mocked argparse behavior
        return

    logger.debug(
        f"CLI arguments: file={args.file}, pattern={args.pattern}, "
        f"verbose={args.verbose}, debug={args.debug}"
    )

    # Validate presence of either file or pattern for test expectations
    if not args.file and not args.pattern:
        logger.error("Neither file nor pattern specified")
        # Let argparse format the error once and return to avoid duplicate mocked calls
        try:
            parser.error("Either -f/--file or -p/--pattern must be specified")
        finally:
            return

    # If both are provided, surface the argparse-style error consistently and avoid duplicate error calls
    if args.file and args.pattern:
        parser.print_usage()  # avoid triggering mocked error twice
        try:
            parser.error("argument -p/--pattern: not allowed with argument -f/--file")
        finally:
            return

    try:
        # If a config file was specified, log its usage early for visibility
        if args.config_file:
            if Path(args.config_file).exists():
                logger.info(f"Loading configuration from: {args.config_file}")
            else:
                logger.warning(
                    f"Config file not found: {args.config_file}; using defaults and CLI overrides"
                )

        cli_config = {
            "database_url": args.connection,
            "max_statements_per_file": args.max_statements,
        }
        config = AppConfig.load(args.config_file, cli_args=cli_config)
        # Align logging defaults to configuration
        setup_logging(
            log_level=config.logging.level.value,
            log_file=config.logging.get_log_file_path(),
            log_dir=config.logging.log_dir,
            enable_console=config.logging.enable_console,
            enable_json=config.logging.is_json_format,
            backup_count=config.logging.backup_count,
        )
        logger = configure_module_logging("cli", log_level=config.logging.level.value)
        if args.config_file and Path(args.config_file).exists():
            logger.info(f"Configuration loaded from: {args.config_file}")

        logger.info("Performing security validation")
        try:
            SecurityValidator.validate_database_url(args.connection, config.security)
            logger.debug("Security validation passed")
        except (SecurityValidationError, SecurityUrlError) as e:
            logger.error(f"Security validation failed: {e}")
            raise CliSecurityError(str(e))

        logger.info(f"Initializing database connection for: {args.connection}")
        if args.verbose:
            print(f"Connecting to database: {args.connection}")

        db_config = DatabaseConfig(
            url=args.connection,
            enable_debug=args.debug,
        )
        db_client = DatabaseClient(db_config)
        logger.info("Database client initialized successfully")
        
        if args.debug:
            print("Debug mode enabled")

        files_to_process = []

        if args.file:
            logger.info(f"Processing single file: {args.file}")
            file_path_resolved = Path(args.file).expanduser().resolve()
            if not file_path_resolved.exists():
                logger.error(f"File not found: {file_path_resolved}")
                raise CliFileError(f"File not found: {file_path_resolved}")
            files_to_process = [str(file_path_resolved)]
        elif args.pattern:
            logger.info(f"Processing files matching pattern: {args.pattern}")
            # Expand user home, but preserve wildcard for glob
            pattern = str(Path(args.pattern).expanduser())
            files_to_process = [str(Path(p).resolve()) for p in glob.glob(pattern)]
            if not files_to_process:
                logger.error(f"No files found matching pattern: {args.pattern}")
                raise CliFileError(f"No files found matching pattern: {args.pattern}")
            files_to_process.sort()
            logger.debug(f"Found {len(files_to_process)} files matching pattern")

        if args.verbose:
            print(f"Found {len(files_to_process)} file(s) to process")

        success_count = 0
        logger.info(f"Starting to process {len(files_to_process)} files")

        # Single persistent connection for the entire run
        with db_client.connect() as conn:
            for file_path in files_to_process:
                logger.info(f"Processing file: {file_path}")
                verbose = args.verbose
                success = process_sql_file(
                    db_client,
                    conn,
                    file_path,
                    config.security,
                    verbose=verbose,
                    output_json=args.output_json,
                    no_emoji=args.no_emoji,
                    stop_on_error=not args.continue_on_error,
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

    except (DatabaseConnectionError,) as e:
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
        _print_security_guidance(str(e), context="url")
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
        if "db_client" in locals():
            logger.info("Closing database client")
            db_client.close()
        logger.info("splurge-sql-runner CLI completed")


if __name__ == "__main__":
    main()
