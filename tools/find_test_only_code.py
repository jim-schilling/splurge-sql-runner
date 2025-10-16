"""
Simple script to scan the codebase for common test-only patterns.

Usage:
    python tools/find_test_only_code.py

It scans the `splurge_sql_runner/` package and reports lines that match patterns that often indicate test-only code
(like references to mocking, special-case guards for tests, or comments that mention tests).

This is intentionally conservative: it only reports potential occurrences for human review.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "splurge_sql_runner"

# Patterns to flag (case-insensitive by default)
PATTERNS = [
    r"\bIn tests\b",
    r"\bIn tests,\b",
    r"\bargs is None\b",
    r"\bmock(?:ed|ing)?\b",
    r"\bmonkeypatch\b",
    r"\bpytest-mock\b",
    r"\bpatch\(",
    r"#\s*pragma:\s*no cover - defensive",
    r"expected by tests",
]

compiled = [re.compile(pat, re.IGNORECASE) for pat in PATTERNS]


def scan(path: Path, patterns: Iterable[re.Pattern]) -> list[str]:
    results: list[str] = []
    for p in path.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for pat in patterns:
                if pat.search(line):
                    results.append(f"{p}:{i}: {line.strip()}")
    return results


if __name__ == "__main__":
    matches = scan(SRC_DIR, compiled)
    if not matches:
        print("No suspicious test-only patterns found in splurge_sql_runner/")
    else:
        print("Potential test-only code occurrences:")
        for m in matches:
            print(m)
        raise SystemExit(2)
