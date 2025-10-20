"""
CLI output helpers for splurge-sql-runner.

Contains text and JSON rendering utilities used by the CLI.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from tabulate import tabulate  # type: ignore
except Exception:  # pragma: no cover - fallback when tabulate unavailable
    tabulate = None

# Module domains
DOMAINS = ["cli", "output", "formatting"]

__all__ = ["simple_table_format", "pretty_print_results"]


# Private constants for rendering
_DEFAULT_COLUMN_WIDTH: int = 10
_SEPARATOR_LENGTH: int = 60
_DASH_SEPARATOR_LENGTH: int = 40
_STATEMENT_TYPE_ERROR: str = "error"
_STATEMENT_TYPE_FETCH: str = "fetch"
_STATEMENT_TYPE_EXECUTE: str = "execute"
_ERROR_PREFIX: str = "ERROR:"
_SUCCESS_PREFIX: str = "SUCCESS:"
_NO_ROWS_MESSAGE: str = "(No rows returned)"
_SUCCESS_MESSAGE: str = "Statement executed successfully"


def simple_table_format(
    headers: list[str],
    rows: list[list[Any]],
) -> str:
    """Simple table formatting when tabulate is not available.

    Args:
        headers: List of column headers.
        rows: List of rows (each row is a list of values).

    Returns:
        Formatted table string.
    """
    if not headers or not rows:
        return "(No data)"

    col_widths: list[int] = []
    for i, header in enumerate(headers):
        max_width = len(str(header))
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)

    lines: list[str] = []

    header_line = "|"
    separator_line = "|"
    for header, width in zip(headers, col_widths, strict=False):
        header_line += f" {str(header):<{width - 1}}|"
        separator_line += "-" * width + "|"

    lines.append(header_line)
    lines.append(separator_line)

    for row in rows:
        row_line = "|"
        for i, value in enumerate(row):
            width = col_widths[i] if i < len(col_widths) else _DEFAULT_COLUMN_WIDTH
            row_line += f" {str(value):<{width - 1}}|"
        lines.append(row_line)

    return "\n".join(lines)


def pretty_print_results(
    results: list[dict[str, Any]],
    file_path: str | None = None,
    *,
    output_json: bool = False,
) -> None:
    """Pretty print the results of SQL execution.

    Args:
        results: List of result dictionaries from execution.
        file_path: Optional file path for context.
        output_json: If True, print JSON instead of human-readable table.
    """
    if output_json:
        payload = []
        for result in results:
            entry = dict(result)
            if file_path and "file_path" not in entry:
                entry["file_path"] = file_path
            payload.append(entry)

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if file_path:
        print(f"\n{'=' * _SEPARATOR_LENGTH}")
        print(f"Results for: {file_path}")
        print(f"{'=' * _SEPARATOR_LENGTH}")

    for i, result in enumerate(results):
        print(f"\nStatement {i + 1}:")

        result_file_path = result.get("file_path") or file_path
        if result_file_path:
            print(f"File: {result_file_path}")

        print(f"Type: {result['statement_type']}")
        print(f"SQL: {result['statement']}")

        if result["statement_type"] == _STATEMENT_TYPE_ERROR:
            print(f"{_ERROR_PREFIX} Error: {result['error']}")
        elif result["statement_type"] == _STATEMENT_TYPE_FETCH:
            print(f"{_SUCCESS_PREFIX} Rows returned: {result['row_count']}")
            if result["result"]:
                headers = list(result["result"][0].keys()) if result["result"] else []
                rows = [list(row.values()) for row in result["result"]]

                if tabulate is not None:
                    print(tabulate(rows, headers=headers, tablefmt="grid"))
                else:
                    print(simple_table_format(headers, rows))
            else:
                print(_NO_ROWS_MESSAGE)
        elif result["statement_type"] == _STATEMENT_TYPE_EXECUTE:
            if "row_count" in result and result["row_count"] is not None:
                print(f"{_SUCCESS_PREFIX} Rows affected: {result['row_count']}")
            else:
                print(f"{_SUCCESS_PREFIX} {_SUCCESS_MESSAGE}")

        print("-" * _DASH_SEPARATOR_LENGTH)
