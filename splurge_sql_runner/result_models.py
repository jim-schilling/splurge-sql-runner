"""
Result models for SQL execution results.

Provides strong-typed structures for representing statement execution results while
allowing easy conversion to legacy dict structures for backward compatibility.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class StatementType(str, Enum):
    """Enumerates supported statement result types."""

    FETCH = "fetch"
    EXECUTE = "execute"
    ERROR = "error"


@dataclass
class StatementResult:
    """Typed representation of a single statement execution result.

    Attributes:
        statement: The SQL text of the executed statement.
        statement_type: Type of the statement result.
        result: Rows for FETCH, True/None for EXECUTE, None for ERROR.
        row_count: Number of rows returned/affected when available.
        error: Error message when ``statement_type`` is ERROR.
        file_path: Optional file path context for this statement.
    """

    statement: str
    statement_type: StatementType
    result: list[dict[str, Any]] | bool | None
    row_count: int | None = None
    error: str | None = None
    file_path: str | None = None


def statement_result_to_dict(result: StatementResult) -> dict[str, Any]:
    """Convert a ``StatementResult`` to the legacy dict structure."""

    data = asdict(result)
    # Map enum to its value for JSON/legacy compatibility
    data["statement_type"] = result.statement_type.value
    # Keep keys order similar to legacy for readability
    ordered = {
        "statement": data["statement"],
        "statement_type": data["statement_type"],
    }
    if result.statement_type == StatementType.ERROR:
        ordered["error"] = data.get("error")
    else:
        ordered["result"] = data.get("result")
        ordered["row_count"] = data.get("row_count")
    if result.file_path:
        ordered["file_path"] = result.file_path
    return ordered


def results_to_dicts(
    results: Sequence[StatementResult | dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize a list of mixed typed results or dicts to dicts."""

    normalized: list[dict[str, Any]] = []
    for item in results:
        if isinstance(item, StatementResult):
            normalized.append(statement_result_to_dict(item))
        else:
            normalized.append(item)
    return normalized
