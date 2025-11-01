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
from typing import Any

from . import load_config
from .cli_output import pretty_print_results, simple_table_format
from .config.constants import DEFAULT_MAX_STATEMENTS_PER_FILE
from .exceptions import SplurgeSqlRunnerDatabaseError, SplurgeSqlRunnerFileError, SplurgeSqlRunnerSecurityError
from .logging import configure_module_logging
from .logging.core import setup_logging
from .main import process_sql_files

# Module domains
DOMAINS = ["cli", "interface"]

# No local tabulate usage; rendering lives in cli_output

# Re-export public API
__all__ = [
    "simple_table_format",
    "pretty_print_results",
    "main",
]

# Output formatting constants
ERROR_PREFIX = "ERROR:"
WARNING_PREFIX = "WARNING:"
SUCCESS_PREFIX = "SUCCESS:"

# Public return code constants
EXIT_CODE_SUCCESS = 0
EXIT_CODE_FAILURE = 1
EXIT_CODE_PARTIAL_SUCCESS = 2
EXIT_CODE_UNKNOWN = 3

# Security guidance messages
SECURITY_GUIDANCE = {
    "too_many_statements": "Tip: increase --max-statements for this run",
    "too_long": "Tip: increase max_statement_length in your JSON config",
    "file_extension": "Tip: add the extension to allowed_file_extensions in config",
    "dangerous_pattern_file": "Tip: rename the file/path or adjust dangerous_path_patterns in config",
    "dangerous_pattern_url": "Tip: correct the database URL or adjust dangerous_url_patterns in config",
    "dangerous_pattern_sql": "Tip: remove the SQL pattern or adjust dangerous_sql_patterns in config",
    "missing_scheme": "Tip: include a scheme like sqlite://, postgresql://, or mysql:// in the connection URL",
}


def print_security_guidance(error_message: str, context: str = "file") -> None:
    """Print actionable guidance for security validation errors.

    Args:
        error_message: The error message from validation.
        context: One of 'file', 'sql', 'url' to tailor hints.
    """
    msg = error_message.lower()
    hints: list[str] = []

    if "too many" in msg:
        hints.append(SECURITY_GUIDANCE["too_many_statements"])
    if "too long" in msg:
        hints.append(SECURITY_GUIDANCE["too_long"])
    if "dangerous pattern" in msg:
        if context == "file":
            hints.append(SECURITY_GUIDANCE["dangerous_pattern_file"])
        elif context == "url":
            hints.append(SECURITY_GUIDANCE["dangerous_pattern_url"])
        else:
            hints.append(SECURITY_GUIDANCE["dangerous_pattern_sql"])
    if "scheme" in msg and context == "url":
        hints.append(SECURITY_GUIDANCE["missing_scheme"])

    for hint in hints:
        print(f"{WARNING_PREFIX}  {hint}")


def discover_files(
    file_path: str | None,
    pattern: str | None,
) -> list[str]:
    """Discover SQL files to process.

    Args:
        file_path: Single file to process
        pattern: Glob pattern to match multiple files

    Returns:
        Sorted list of absolute file paths

    Raises:
        SplurgeSqlRunnerFileError: If no files found or paths invalid
    """
    if file_path:
        path_obj = Path(file_path).expanduser().resolve()
        if not path_obj.exists():
            raise SplurgeSqlRunnerFileError(f"File not found: {path_obj}")
        return [str(path_obj)]

    if pattern:
        expanded = str(Path(pattern).expanduser())
        files = [str(Path(p).resolve()) for p in glob.glob(expanded)]
        if not files:
            raise SplurgeSqlRunnerFileError(f"No files found matching pattern: {pattern}")
        return sorted(files)

    return []


def report_execution_summary(summary: dict[str, Any], output_json: bool = False) -> None:
    """Display execution summary and results.

    Args:
        summary: Processing summary from process_sql_files()
        output_json: Whether to output JSON format
    """
    for fp, results in summary.get("results", {}).items():
        pretty_print_results(results, fp, output_json=output_json)

    files_processed = summary.get("files_processed", 0)
    files_passed = summary.get("files_passed", 0)

    print(f"\n{'=' * 60}")
    print(f"Summary: {files_passed}/{files_processed} files processed successfully")
    print(f"{'=' * 60}")


def main() -> int:
    """Main CLI entry point.

    Parses command-line arguments, loads configuration, discovers SQL files,
    executes them against the specified database, and prints results.

    Returns:
        Exit code: 0 for success, 1 for failure, 2 for partial success,
        3 for unknown/unexpected state
    """
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

    # If both are provided, surface the argparse-style error consistently
    if args.file and args.pattern:
        parser.error("argument -p/--pattern: not allowed with argument -f/--file")

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

        # Discover files to process
        files_to_process = discover_files(args.file, args.pattern)
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

            # Print results using helper function
            report_execution_summary(summary, output_json=args.output_json)

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
                    logger.error(f"Unexpected summary state. Exiting with error code {EXIT_CODE_UNKNOWN}")
                    exit_code = EXIT_CODE_UNKNOWN
            else:
                logger.error(f"Unexpected summary state. Exiting with error code {EXIT_CODE_UNKNOWN}")
                exit_code = EXIT_CODE_UNKNOWN

        except SplurgeSqlRunnerSecurityError as e:
            logger.error(f"Security validation failed: {e}")
            print(f"{ERROR_PREFIX} Security validation failed: {e}")
            print_security_guidance(str(e), context="file")
            exit_code = EXIT_CODE_FAILURE

    except SplurgeSqlRunnerDatabaseError as e:
        logger.error(f"Database error: {e}")
        print(f"{ERROR_PREFIX} Database error: {e}")
        exit_code = EXIT_CODE_FAILURE
    except SplurgeSqlRunnerFileError as e:
        logger.error(f"File error: {e}")
        print(f"{ERROR_PREFIX} File error: {e}")
        exit_code = EXIT_CODE_FAILURE
    except SplurgeSqlRunnerSecurityError as e:
        logger.error(f"Security error: {e}")
        print(f"{ERROR_PREFIX} Security error: {e}")
        print_security_guidance(str(e), context="url")
        exit_code = EXIT_CODE_FAILURE
    except Exception as e:
        logger.error(f"Runtimeerror: {e}", exc_info=True)
        print(f"{ERROR_PREFIX} Runtime error: {e}")
        exit_code = EXIT_CODE_FAILURE
    finally:
        logger.info("splurge-sql-runner CLI completed")
    return exit_code


if __name__ == "__main__":
    code = main()
    # Explicitly exit with returned code for script callers
    sys.exit(code)
