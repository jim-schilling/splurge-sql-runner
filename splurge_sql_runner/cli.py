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

from splurge_sql_runner import load_config
from splurge_sql_runner.cli_output import pretty_print_results, simple_table_format
from splurge_sql_runner.config.constants import DEFAULT_MAX_STATEMENTS_PER_FILE
from splurge_sql_runner.exceptions import (
    CliSecurityError,
    DatabaseError,
    FileError,
    SecurityUrlError,
    SecurityValidationError,
)
from splurge_sql_runner.logging import configure_module_logging
from splurge_sql_runner.logging.core import setup_logging
from splurge_sql_runner.main import process_sql_files

# No local tabulate usage; rendering lives in cli_output

# Re-export public API
__all__ = [
    "simple_table_format",
    "pretty_print_results",
    "main",
]


_ERROR_PREFIX: str = "ERROR:"
_SUCCESS_PREFIX: str = "SUCCESS:"
_WARNING_PREFIX: str = "WARNING:"

# Public return code constants
EXIT_CODE_SUCCESS = 0
EXIT_CODE_FAILURE = 1
EXIT_CODE_PARTIAL_SUCCESS = 2
EXIT_CODE_UNKNOWN = 3


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
        hints.append("Tip: increase security.validation.max_statement_length in your JSON config.")
    if "file extension not allowed" in msg:
        hints.append("Tip: add the extension to security.allowed_file_extensions in your JSON config.")
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
        hints.append("Tip: include a scheme like sqlite:///, postgresql://, or mysql:// in the connection URL.")

    for hint in hints:
        print(f"{_WARNING_PREFIX}  {hint}")


def main() -> int:
    """Main CLI entry point."""
    # Some Python runtimes expose reconfigure on TextIO; narrow before calling
    try:
        from io import TextIOWrapper

        if isinstance(sys.stdout, TextIOWrapper):
            sys.stdout.reconfigure(encoding="utf-8")
        if isinstance(sys.stderr, TextIOWrapper):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        # Be permissive: if reconfigure isn't available or an unexpected error occurs, continue
        pass

    # Bootstrap a basic logger early
    logger = configure_module_logging("cli", log_level="INFO")

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
        help="Path to JSON configuration file",
    )

    parser.add_argument(
        "--security-level",
        choices=["strict", "normal", "permissive"],
        default="normal",
        help="Security validation level (default: normal)",
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
    # parse_args() will exit via SystemExit for invalid args; proceed assuming args is valid

    logger.debug(f"CLI arguments: file={args.file}, pattern={args.pattern}, verbose={args.verbose}, debug={args.debug}")

    # Validate presence of either file or pattern
    if not args.file and not args.pattern:
        logger.error("Neither file nor pattern specified")
        # Let argparse format the error for consistency
        parser.error("Either -f/--file or -p/--pattern must be specified")
        return EXIT_CODE_FAILURE

    # If both are provided, surface the argparse-style error consistently
    if args.file and args.pattern:
        parser.error("argument -p/--pattern: not allowed with argument -f/--file")
        return EXIT_CODE_FAILURE

    try:
        exit_code = EXIT_CODE_UNKNOWN
        # If a config file was specified, log its usage early for visibility
        if args.config_file:
            if Path(args.config_file).exists():
                logger.info(f"Loading configuration from: {args.config_file}")
            else:
                logger.warning(f"Config file not found: {args.config_file}; using defaults and CLI overrides")

        # Load configuration
        config = load_config(args.config_file)
        # Override database URL from CLI
        config["database_url"] = args.connection
        config["security_level"] = args.security_level
        if hasattr(args, "max_statements") and args.max_statements:
            config["max_statements_per_file"] = args.max_statements

        # Setup logging
        setup_logging(
            log_level=config.get("log_level", "INFO"),
            enable_console=True,
        )
        logger = configure_module_logging("cli", log_level=config.get("log_level", "INFO"))

        if args.config_file and Path(args.config_file).exists():
            logger.info(f"Configuration loaded from: {args.config_file}")

        # Build list of files to process
        files_to_process = []

        if args.file:
            logger.info(f"Processing single file: {args.file}")
            file_path_resolved = Path(args.file).expanduser().resolve()
            if not file_path_resolved.exists():
                logger.error(f"File not found: {file_path_resolved}")
                raise FileError(f"File not found: {file_path_resolved}")
            files_to_process = [str(file_path_resolved)]
        elif args.pattern:
            logger.info(f"Processing files matching pattern: {args.pattern}")
            # Expand user home, but preserve wildcard for glob
            pattern = str(Path(args.pattern).expanduser())
            files_to_process = [str(Path(p).resolve()) for p in glob.glob(pattern)]
            if not files_to_process:
                logger.error(f"No files found matching pattern: {args.pattern}")
                raise FileError(f"No files found matching pattern: {args.pattern}")
            files_to_process.sort()
            logger.debug(f"Found {len(files_to_process)} files matching pattern")

        if args.verbose:
            print(f"Found {len(files_to_process)} file(s) to process")

        try:
            summary = process_sql_files(
                files_to_process,
                database_url=config["database_url"],
                config=config,
                security_level=config.get("security_level", "normal"),
                max_statements_per_file=config.get("max_statements_per_file", 100),
                stop_on_error=not args.continue_on_error,
            )

            # Print results similar to previous behavior
            for fp, results in summary.get("results", {}).items():
                pretty_print_results(results, fp, output_json=args.output_json)

            print(f"\n{'=' * 60}")
            print(
                f"Summary: {summary.get('success_count', 0)}/{summary.get('files_processed', 0)} files processed successfully"
            )
            print(f"{'=' * 60}")

            files_processed = summary.get("files_processed", 0)
            files_passed = summary.get("files_passed", 0)
            files_failed = summary.get("files_failed", 0)
            files_mixed = summary.get("files_mixed", 0)
            if files_processed > 0:
                if files_mixed > 0:
                    logger.error(f"Some files failed to process. Exiting with error code {EXIT_CODE_PARTIAL_SUCCESS}")
                    exit_code = EXIT_CODE_PARTIAL_SUCCESS
                elif files_failed == files_processed:
                    logger.error(f"All files failed to process. Exiting with error code {EXIT_CODE_FAILURE}")
                    exit_code = EXIT_CODE_FAILURE
                elif files_passed == files_processed:
                    logger.info(f"All files processed successfully. Exiting with success code {EXIT_CODE_SUCCESS}")
                    exit_code = EXIT_CODE_SUCCESS
                else:
                    # this should be unreachable due to prior checks
                    logger.error(f"Unexpected summary state. Exiting with error code {EXIT_CODE_UNKNOWN}")
                    exit_code = EXIT_CODE_UNKNOWN
            else:
                # this should be unreachable due to prior checks
                logger.error(f"Unexpected summary state. Exiting with error code {EXIT_CODE_UNKNOWN}")
                exit_code = EXIT_CODE_UNKNOWN

        except (SecurityValidationError, SecurityUrlError) as e:
            logger.error(f"Security validation failed: {e}")
            print(f"{_ERROR_PREFIX} Security validation failed: {e}")
            _print_security_guidance(str(e), context="file")
            exit_code = EXIT_CODE_FAILURE

    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        print(f"{_ERROR_PREFIX} Database error: {e}")
        exit_code = EXIT_CODE_FAILURE
    except FileError as e:
        logger.error(f"File error: {e}")
        print(f"{_ERROR_PREFIX} File error: {e}")
        exit_code = EXIT_CODE_FAILURE
    except CliSecurityError as e:
        logger.error(f"Security error: {e}")
        print(f"{_ERROR_PREFIX} Security error: {e}")
        _print_security_guidance(str(e), context="url")
        exit_code = EXIT_CODE_FAILURE
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"{_ERROR_PREFIX} Unexpected error: {e}")
        exit_code = EXIT_CODE_FAILURE
    finally:
        logger.info("splurge-sql-runner CLI completed")
    return exit_code


if __name__ == "__main__":
    code = main()
    # Explicitly exit with returned code for script callers
    sys.exit(code)
