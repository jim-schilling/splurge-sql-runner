#!/usr/bin/env python3
"""
Command-line interface for jpy-sql-runner.

Provides CLI functionality for executing SQL files against databases with
support for single files, file patterns, and verbose output modes.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

"""
CLI for jpy-sql-runner

Usage:
    python -m jpy_sql_runner -c "sqlite:///database.db" -f "script.sql"
    python -m jpy_sql_runner -c "sqlite:///database.db" -p "*.sql"
"""

import argparse
import glob
import sys
from pathlib import Path
from typing import List, Dict, Any


# Try to import tabulate, fallback to simple formatting if not available
try:
    from tabulate import tabulate

    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

from jpy_sql_runner.db_helper import DbEngine, DbOperationError
from jpy_sql_runner.sql_helper import split_sql_file


def simple_table_format(headers: List[str], rows: List[List]) -> str:
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

    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(str(header))
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)  # Add padding

    # Build table
    lines = []

    # Header
    header_line = "|"
    separator_line = "|"
    for header, width in zip(headers, col_widths):
        header_line += f" {str(header):<{width-1}}|"
        separator_line += "-" * width + "|"

    lines.append(header_line)
    lines.append(separator_line)

    # Rows
    for row in rows:
        row_line = "|"
        for i, value in enumerate(row):
            width = col_widths[i] if i < len(col_widths) else 10
            row_line += f" {str(value):<{width-1}}|"
        lines.append(row_line)

    return "\n".join(lines)


def pretty_print_results(results: List[Dict[str, Any]], file_path: str = None) -> None:
    """
    Pretty print the results of SQL execution.

    Args:
        results: List of result dictionaries from DbEngine.batch()
        file_path: Optional file path for context
    """
    if file_path:
        print(f"\n{'='*60}")
        print(f"Results for: {file_path}")
        print(f"{'='*60}")

    for result in results:
        print(f"\nStatement {result['statement_index'] + 1}:")
        print(f"Type: {result['type']}")
        print(f"SQL: {result['statement']}")

        if result["type"] == "error":
            print(f"❌ Error: {result['error']}")
        elif result["type"] == "fetch":
            print(f"✅ Rows returned: {result['row_count']}")
            if result["result"]:
                # Use tabulate for pretty table output if available, otherwise use simple formatting
                headers = list(result["result"][0].keys()) if result["result"] else []
                rows = [list(row.values()) for row in result["result"]]

                if HAS_TABULATE:
                    print(tabulate(rows, headers=headers, tablefmt="grid"))
                else:
                    print(simple_table_format(headers, rows))
            else:
                print("(No rows returned)")
        elif result["type"] == "execute":
            print(f"✅ Statement executed successfully")

        print("-" * 40)


def process_sql_file(
    db_engine: DbEngine, file_path: str, verbose: bool = False
) -> bool:
    """
    Process a single SQL file and execute its statements.

    Args:
        db_engine: Database engine instance
        file_path: Path to SQL file
        verbose: Whether to print verbose output

    Returns:
        True if successful, False otherwise
    """
    try:
        if verbose:
            print(f"Processing file: {file_path}")

        # Split file into individual statements
        statements = split_sql_file(file_path, strip_semicolon=False)

        if not statements:
            if verbose:
                print(f"No valid SQL statements found in {file_path}")
            return True

        # Join statements back together for batch processing
        sql_content = ";\n".join(statements) + ";"

        # Execute batch
        results = db_engine.batch(sql_content)

        # Pretty print results
        pretty_print_results(results, file_path)

        return True

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def main():
    """Main CLI entry point."""
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
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable SQLAlchemy debug mode"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.file and not args.pattern:
        parser.error("Either -f/--file or -p/--pattern must be specified")

    if args.file and args.pattern:
        parser.error("Cannot specify both -f/--file and -p/--pattern")

    try:
        # Initialize database engine
        if args.verbose:
            print(f"Connecting to database: {args.connection}")

        db_engine = DbEngine(args.connection, debug=args.debug)

        # Determine files to process
        files_to_process = []

        if args.file:
            if not Path(args.file).exists():
                print(f"❌ File not found: {args.file}")
                sys.exit(1)
            files_to_process = [args.file]
        elif args.pattern:
            files_to_process = glob.glob(args.pattern)
            if not files_to_process:
                print(f"❌ No files found matching pattern: {args.pattern}")
                sys.exit(1)
            files_to_process.sort()  # Process files in alphabetical order

        if args.verbose:
            print(f"Found {len(files_to_process)} file(s) to process")

        # Process each file
        success_count = 0
        for file_path in files_to_process:
            if process_sql_file(db_engine, file_path, args.verbose):
                success_count += 1

        # Summary
        print(f"\n{'='*60}")
        print(
            f"Summary: {success_count}/{len(files_to_process)} files processed successfully"
        )
        print(f"{'='*60}")

        if success_count < len(files_to_process):
            sys.exit(1)

    except DbOperationError as e:
        print(f"❌ Database operation error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Clean up
        if "db_engine" in locals():
            db_engine.shutdown()


if __name__ == "__main__":
    main() 