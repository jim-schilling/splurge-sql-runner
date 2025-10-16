## API Reference

This document describes the public, programmatic API exposed by the `splurge_sql_runner` package.
The library is primarily centered around a small set of functions that make it easy to parse SQL files,
validate them against configured security policies, and execute SQL statements against supported databases.

Note: All functions below raise specific exceptions (see the Exceptions section) rather than calling
`sys.exit()`; the CLI wrapper calls `sys.exit(main())` and maps these outcomes to exit codes.

---

## process_sql

Signature:

```py
from typing import Any

def process_sql(
		sql_content: str,
		*,
		database_url: str,
		config: dict | None = None,
		security_level: str = "normal",
		max_statements_per_file: int = 100,
		stop_on_error: bool = True,
) -> list[dict[str, Any]]:
		...
```

Description:

- Parse and validate a single SQL content blob, then execute the parsed statements against the
	provided `database_url` using the `DatabaseClient` implementation.
- Returns statement-level result dictionaries in the same format used by the CLI output helpers.

Return value (list of dicts): each dict contains the following keys:

- `statement` (str): The SQL statement text (semicolon may be present depending on parsing options)
- `statement_type` (str): One of `"fetch"`, `"execute"`, or `"error"`
- `result` (varies): For `fetch` statements, a list of row mappings (list[dict]); for `execute` usually `True`.
- `row_count` (int | None): Number of rows returned for `fetch` or affected for `execute` when available.
- `error` (str | None): Error message when `statement_type` == `"error"`.

Exceptions:

- `SecurityValidationError` - raised when `SecurityValidator` rejects the SQL content or database URL.
- `SqlFileError` - not raised directly by `process_sql` but present in the module for related utilities.
- `DatabaseError` - propagated from `DatabaseClient` when database engine or connection fails.

Example:

```py
from splurge_sql_runner import main

results = main.process_sql("SELECT 1;", database_url="sqlite:///:memory:")
for r in results:
		print(r["statement_type"], r.get("row_count"))
```

---

## process_sql_files

Signature:

```py
def process_sql_files(
		file_paths: list[str],
		*,
		database_url: str,
		config: dict | None = None,
		security_level: str = "normal",
		max_statements_per_file: int = 100,
		stop_on_error: bool = True,
) -> dict[str, Any]:
		...
```

Description:

- Reads one or more SQL files, validates their content, executes each file as a batch of statements,
	and returns a summary describing per-file outcomes and counts.

Return value (summary dict):

- `files_processed` (int) - number of files successfully processed (attempted)
- `files_passed` (int) - files where all statements succeeded
- `files_failed` (int) - files where all statements failed
- `files_mixed` (int) - files with mixed success and failure among statements
- `results` (dict) - mapping of file path -> list of statement result dicts (same shape as `process_sql` output)

Error handling:

- Per-file unexpected exceptions are captured into the `results[file_path]` as a single `error`-typed statement
	result; `SecurityValidationError` is raised immediately for the offending content (to allow callers to handle
	policy failures specially).

Example:

```py
summary = main.process_sql_files(["migrations/001_init.sql"], database_url="sqlite:///db.sqlite")
print(summary["files_passed"], summary["files_failed"]) 
```

---

## parse_sql_file

Signature:

```py
def parse_sql_file(path: str | pathlib.Path, *, strip_semicolon: bool = False) -> list[str]:
		...
```

Description:

- Read a SQL file and return a list of individual SQL statements. The function removes single-line (`--`)
	and block (`/* ... */`) comments while preserving comment-like text inside string literals. It filters out
	empty or whitespace-only statements.

Parameters:

- `path` - file path or `pathlib.Path` to read from.
- `strip_semicolon` - if True, trailing semicolons will be removed from returned statements.

Exceptions:

- `SqlFileError` - when the file cannot be read, is missing, or contains invalid content.

Example:

```py
from splurge_sql_runner.sql_helper import parse_sql_file

statements = parse_sql_file("scripts/setup.sql", strip_semicolon=True)
```

---

## Exceptions

Key exception types used by the library (all located in `splurge_sql_runner.exceptions`):

- `SqlFileError` - file not found, unreadable, or invalid file path
- `SecurityValidationError` - SQL content or database URL failed security validation
- `DatabaseError` - database connection / execution failures

---

If you need examples of higher-level usage (CLI and API combined), see the `docs/cli/CLI-REFERENCE.md` and
the `examples/` folder in the repository for short usage snippets.

