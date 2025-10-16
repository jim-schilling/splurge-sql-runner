## Improve Test Coverage to 85%: database_client.py, sql_helper.py, cli.py

### Goal
- Raise per-file coverage to at least 85% while testing behavior only, validating public APIs, using minimal or no mocks, and asserting on text patterns rather than exact strings.

### Baseline (from recent run)
- database_client.py: ~71%
- sql_helper.py: ~83%
- cli.py: ~81%

### Principles
- Only test public APIs:
  - database_client: `DatabaseClient.connect`, `execute_batch`, `execute_statements`, `close`, and context manager semantics.
  - sql_helper: `remove_sql_comments`, `detect_statement_type`, `parse_sql_statements`, `split_sql_file`.
  - cli: `process_sql_file`, `main`.
- Prefer real SQLite databases (file-based or in-memory). Avoid mocking DB connections unless a behavior cannot be reached otherwise.
- Validate text output via patterns/substrings, not exact/fragile phrases.
- Avoid inspecting private helpers or internal implementation details.

### Step-by-step Plan

#### 1) sql_helper.py (quick wins to reach ≥85%)
Add tests that exercise uncovered branches around CTE parsing, edge token flows, and file I/O errors.

1.1 detect_statement_type: WITH without parentheses after AS
- Input: a CTE using `WITH c AS SELECT 1 SELECT 2` (intentionally malformed missing `( )`).
- Expected: falls back to finding the first main statement; returns `FETCH_STATEMENT` (pattern-match `'fetch'`).

1.2 detect_statement_type: DCL/other statements
- Input: statements like `GRANT SELECT ON t TO u`, `REVOKE ...`, `TRUNCATE TABLE t`.
- Expected: treated as execute; returns `EXECUTE_STATEMENT` (pattern-match `'execute'`).

1.3 parse_sql_statements: only semicolons
- Input: string consisting of just `;` and whitespace separated semicolons.
- Expected: returns empty list.

1.4 split_sql_file: general OSError path (non-existent vs not-readable)
- Setup: create a temporary directory and pass its path (opening a directory should raise an OSError/PermissionError on most platforms).
- Call: `split_sql_file(dir_path)`
- Expected: raises `SqlFileError` with a message containing a generic pattern like `"Error reading SQL file"`.

1.5 detect_statement_type: multiple CTEs followed by non-fetch top-level statement
- Input: `WITH a AS (...), b AS (...) INSERT INTO t SELECT * FROM a`.
- Expected: `EXECUTE_STATEMENT`.

Notes
- Use pattern assertions for returned type constants (`'fetch'`/`'execute'`).
- Keep inputs minimal; no reliance on sqlparse internals.

#### 2) database_client.py (transaction/error paths and list execution)
Focus on `execute_statements` continue-on-error branch, connection failure handling, normalization, and reusing an external connection.

2.1 connect() failure wraps as DatabaseConnectionError
- Input: `DatabaseClient(DatabaseConfig(url='invalid://url'))` then `client.connect()`.
- Expected: raises `DatabaseConnectionError`. No mocks; SQLAlchemy will fail to create the engine.

2.2 execute_batch: empty/whitespace/comment-only SQL
- Inputs: `""`, whitespace-only, and comment-only strings.
- Expected: returns empty list.

2.3 execute_statements: continue-on-error branch
- Setup: SQLite file DB; create table; pass list: valid insert, invalid SQL, valid insert; set `stop_on_error=False`.
- Expected: three results with pattern-based checks: first execute, second error, third execute. Verify final select returns the successful rows.

2.4 execute_statements: stop-on-error True rollback behavior
- Setup: list with `CREATE TABLE`, invalid SQL, `INSERT` and `stop_on_error=True`.
- Expected: returns two results (execute, error). A follow-up introspection `SELECT` shows the table was not created (zero rows from sqlite_master lookup).

2.5 execute_statements: normalization trims trailing semicolons and ignores empty items
- Inputs: list including statements with and without trailing `;`, plus whitespace-only entries.
- Expected: whitespace-only entries are ignored; behavior of others matches their type.

2.6 external connection usage
- Setup: open one persistent connection with `with client.connect() as conn:`.
- Call: `execute_statements([...], connection=conn)` and `execute_batch(sql, connection=conn)`.
- Expected: success with results as usual. Ensures the code path where the client does not own the connection is executed.

2.7 idempotent close()
- Call `client.close()` twice.
- Expected: no exception, engine reference cleared. Behavioral check only (no engine internals).

Notes
- Favor file-based SQLite where persistence across calls is needed; otherwise use in-memory.
- Keep assertions to result structure and type patterns, not exact messages.

#### 3) cli.py (argument branches, guidance hints, multi-file summary)
Cover gaps around JSON/config handling, security guidance hints, and multi-file summary with partial failures.

3.1 main: `--config` provided but file missing
- Args: `--connection sqlite:///<tmp.db> --file <tmp.sql> --config <missing.json>`
- Expected: program proceeds using defaults; no exit; code path logs a warning (no need to assert logs; executing path improves coverage).

3.2 main: `--config` provided and exists
- Use a minimal JSON config (can start from `examples/config.json` or create temporary JSON aligning with current schema).
- Expected: program runs and completes successfully.

3.3 main: security guidance hint for too many statements
- Create SQL file with 2 statements; run with `--max-statements 1`.
- Expected: exit code 1; printed output contains guidance pattern like `Tip:` and `max_statements` related hint. Do not assert the exact full sentence, just substrings such as `Tip:` and `max`/`statements`.

3.4 process_sql_file: output_json and no_emoji switches through CLI
- Args: include `--json` and `--no-emoji` on a simple `SELECT 1` file.
- Expected: output contains JSON-like array for results and OK lines without emoji. Use substring checks (e.g., output starting with `[` and `[OK]`).

3.5 main: pattern matching multiple files with partial failure → non-zero exit and summary
- Setup: two temp files; one safe SQL file; one file renamed to include a known dangerous path pattern.
- Run: with `-p` targeting both files.
- Expected: process both; summary is printed; exit with code 1. Pattern-check `"Summary:"` and a `"/"` count, not exact numbers.

3.6 main: early validation errors already covered (neither file nor pattern, both specified)
- Already present; no changes needed. Ensure tests remain pattern-based and do not depend on argparse internals beyond one error call path.

Notes
- Continue to avoid direct testing of private helper `_print_security_guidance`; instead, trigger it via `process_sql_file`/`main` and assert on presence of generic `Tip:` lines with context keywords.

### Execution Order
1. Implement sql_helper tests (1.x). Re-run coverage; sql_helper should exceed 85%.
2. Implement database_client tests (2.x). Re-run coverage; target ≥85%.
3. Implement cli tests (3.x). Re-run coverage; target ≥85%.
4. Iterate only if any file remains below target; prioritize adding realistic scenarios rather than mocking internals.

### Tooling & Commands
- Run tests with coverage:
  - `pytest -x -v -n auto --cov=splurge_sql_runner --cov-report=term-missing`
- Prefer SQLite for DB interactions.

### Risks & Mitigations
- Platform-specific I/O exceptions for `split_sql_file` when opening directories: assert on broad `SqlFileError` and a generic `"Error reading SQL file"` pattern rather than OS-specific error text.
- SQLAlchemy/dialect differences in `rowcount`: assert membership in a small set (e.g., `in (None, 0, 1)`), not exact values across engines.
- Flaky path matching with glob: keep test patterns narrowly targeted to created temp files.

### Definition of Done
- Each of the three files reports ≥85% coverage locally.
- All new tests validate only public APIs and observable behavior.
- Assertions use stable patterns/substrings rather than exact full messages.
- Tests pass on Windows and Unix-like environments using SQLite.


