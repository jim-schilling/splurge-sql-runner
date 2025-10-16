## Changelog

### 2025.5.0 (10-15-2025)

- **Migration (CLI)**
  - The CLI `main()` function now returns integer exit codes instead of calling `sys.exit()` directly.
    The distribution entrypoint still calls `sys.exit(main())`, so behavior for end users is unchanged.
  - New public constants are available from `splurge_sql_runner.cli`: `EXIT_CODE_SUCCESS`,
    `EXIT_CODE_FAILURE`, `EXIT_CODE_PARTIAL_SUCCESS`, `EXIT_CODE_UNKNOWN`.
  - Rationale: makes the CLI easier to call from tests and embedding programs without intercepting
    `SystemExit`.

- **CLI implementation and wiring**
  - `splurge_sql_runner.__main__` updated to propagate `main()` return codes via `sys.exit(main())`.
  - `cli_output.pretty_print_results` expectations clarified; tests aligned with the expected
    per-statement result dict shape.

- **Tests & coverage**
  - Added extensive unit tests for CLI behavior, flags, and edge cases (security guidance, partial-success
    path, flag parsing and variations).
  - Added and hardened tests for `sql_helper` (parsing, comment handling, CTEs) and for the
    `DatabaseClient` (mocked execution, row/rowcount handling, error/rollback behavior).
  - Reworked tests to be more robust: use `monkeypatch.setattr(sys, "argv", ...)`, tolerant assertions,
    and deterministic fixtures. Fixed a failing assertion in `tests/unit/test_result_models.py`.

- **Docs**
  - Updated `docs/cli/CLI-REFERENCE.md` with the exit-code migration note and clarified several flags
    (including `--continue-on-error` semantics).
  - Added `docs/api/API-REFERENCE.md` documenting `process_sql`, `process_sql_files`, and
    `parse_sql_file` (signatures, return shapes, exceptions, examples).

- **Tooling & quality**
  - Applied `ruff` formatting and fixes across tests and source where necessary.
  - Ran and validated `mypy` for the package (no typing errors reported after fixes).

- **Minor fixes**
  - Re-exported `parse_sql_file` from `splurge_sql_runner.main` to support tests and API consumers
    that import it from the `main` module.
  - Fixed several brittle test patterns and import-order issues revealed by `ruff`.

This release focuses on testability and maintenance: the behavior visible to CLI users is unchanged,
but the program is easier to integrate and assert against from programmatic callers and test suites.

### 2025.4.2 (09-03-2025)

- **Test Coverage**
  - Added focused unit tests for `utils.security_utils` covering `sanitize_shell_arguments` and `is_safe_shell_argument`
  - Exercises success and error branches; improves module coverage and overall suite fidelity

- **Typing Modernization**
  - Migrated `typing.List`/`typing.Dict`/`Optional` usage to built-in generics and `|` unions across source and tests
  - Aligns with Python 3.10+ standards and repository preferences

- **E2E/Test Decoupling**
  - Inlined shell argument sanitization in `tests/run_tests.py` to avoid importing application code in E2E paths
  - Ensures E2E tests remain focused on public interfaces only

- **Tooling & CI**
  - Added `ruff` configuration and dependency; enabled checks (E, F, I, B, UP)
  - Enabled parallel test execution via `pytest-xdist` and default `-n auto`
  - Kept line length at 120; retained Black, Flake8, MyPy

- **Documentation**
  - Created `docs/README.md` with quickstart, testing, and security notes

- **CLI**
  - Clarified `process_sql_file` docstring and removed outdated references; security enforcement remains always-on

- **Compatibility**
  - No breaking changes; public APIs remain stable

### 2025.4.1 (09-01-2025)

- **Enhanced Security Validation and Testing Framework**
  - **Comprehensive Security Test Suite**: Added extensive unit tests for `SecurityValidator` class covering file path, database URL, and SQL content validation
  - **Security Error Handling**: Implemented proper catching of `SecurityFileError` and `SecurityValidationError` in CLI with enhanced error context and user guidance
  - **File Extension Validation**: Added CLI tests for security validation of disallowed file extensions
  - **Pattern Matching**: Enhanced case-insensitive pattern matching for dangerous path and SQL patterns
  - **Edge Case Coverage**: Added tests for empty/None values, large files, and complex validation scenarios

- **Improved Database Client and Transaction Handling**
  - **Enhanced Error Handling Modes**: Added comprehensive unit tests for `DatabaseClient.execute_statements` API with both `stop_on_error=True` and `stop_on_error=False` modes
  - **Transaction Safety**: Verified rollback behavior in batch operations when errors occur
  - **Statement Type Detection**: Enhanced detection of uncommon SQL statement types (VALUES, DESC/DESCRIBE, EXPLAIN, SHOW, PRAGMA, WITH ... INSERT/UPDATE/DELETE CTE patterns)

- **SQL Parser Robustness**
  - **String Literal Handling**: Added integration tests for semicolons inside string literals to ensure proper parsing
  - **Edge Case Testing**: Enhanced parsing of complex SQL with comments, whitespace, and special characters
  - **Statement Classification**: Improved accuracy of SQL statement type detection across various database dialects

- **Code Quality & Refactoring**: Comprehensive code cleanup and optimization across the entire codebase
  - **Removed unused variables**: Cleaned up unused variable declarations in `database_client.py` and other modules
  - **Fixed import organization**: Moved all import statements to top of modules where possible for better maintainability
  - **Enhanced code structure**: Refactored code for improved readability and consistency across multiple modules
  - **Type hint improvements**: Updated and refined type hints in configuration and database modules
  - **CLI output optimization**: Fixed fallback assignment for `tabulate` in `cli_output.py` to ensure clarity in code structure
  - **Import cleanup**: Refactored imports and cleaned up code across multiple modules for better organization

- **Documentation**: Added comprehensive coding standards documentation files
  - Added `.cursor/rules/` directory with detailed coding standards for the project
  - Included standards for code design, style, development approach, documentation, methods, naming conventions, project organization, Python standards, and testing

- **Version Update**: Updated version to 2025.4.1 in `pyproject.toml`
- **Backward Compatibility**: All changes maintain backward compatibility with existing APIs and functionality
- **Test Coverage**: Maintained existing test coverage with all tests passing after refactoring

### 2025.4.0 (08-24-2025)

- **Performance & Code Quality**: Optimized and simplified `sql_helper.py` module
  - **Reduced complexity**: Eliminated 5 helper functions and consolidated keyword sets
  - **Better performance**: Implemented O(1) set membership checks and unified CTE scanner
  - **Cleaner code**: Single token normalization and simplified control flow
  - **Accurate documentation**: Removed misleading caching claims from docstrings
  - **Reduced maintenance burden**: Removed unused `ERROR_STATEMENT` constant and helpers
  - **Bug fix**: Enhanced comment filtering in `parse_sql_statements` for edge cases
- **Backward Compatibility**: All public APIs remain unchanged, no breaking changes
- **Test Coverage**: Maintained 93% test coverage with all existing functionality preserved
- **Documentation**: Created comprehensive optimization plan in `plans/sql_helper_optimization_plan.md`
- **Verification**: All examples and tests continue to work correctly after optimization

### 2025.3.1 (08-20-2025)

- **Test Coverage**: Improved test coverage to 85% target across core modules
  - `sql_helper.py`: Reached 85% coverage with comprehensive edge case testing
  - `database_client.py`: Improved from ~71% to 77% coverage with additional test scenarios
  - `cli.py`: Reached 84% coverage with enhanced CLI functionality testing
- **Test Quality**: Added behavior-driven tests focusing on public APIs and real functionality
  - Enhanced CTE (Common Table Expressions) parsing edge cases
  - Added DCL (Data Control Language) statement type detection
  - Improved error handling and rollback behavior testing
  - Added config file handling and security guidance output tests
  - Enhanced pattern matching and multi-file processing scenarios
- **Code Quality**: Moved all import statements to top of modules where possible
  - Cleaned up inline imports in test files (`test_cli.py`, `conftest.py`, `test_logging_performance.py`)
  - Removed duplicate test functions that were accidentally created
  - Maintained appropriate inline imports for test setup methods where needed
- **Documentation**: Created comprehensive test improvement plan in `plans/improve-code-coverage.md`
- **Testing**: Verified all examples work correctly with enhanced test suite
  - Interactive demo functionality confirmed working
  - CLI automation tests passing
  - Database deployment script execution verified
  - Pattern matching and JSON output features tested

### 2025.3.0 (08-11-2025)

- **Documentation**: Updated Programmatic Usage section to clarify that the library is primarily designed for CLI usage
- **Documentation**: Added note explaining that programmatic API is for advanced use cases and integration scenarios
- **Documentation**: Emphasized that CLI offers the most comprehensive features and best user experience
- **Breaking Changes**: Unified engine abstraction replaced by `DatabaseClient`
- **New**: Centralized configuration constants in `splurge_sql_runner.config.constants`
- **Improved**: Security validation now uses centralized `SecurityConfig` from `splurge_sql_runner.config.security_config`
- **Code Quality**: Eliminated code duplication across the codebase
- **Breaking Changes**: Environment variables now use `SPLURGE_SQL_RUNNER_` prefix instead of `JPY_`
  - `JPY_DB_URL` → `SPLURGE_SQL_RUNNER_DB_URL`
  - `JPY_DB_TIMEOUT` → `SPLURGE_SQL_RUNNER_DB_TIMEOUT`
  - `JPY_SECURITY_ENABLED` → `SPLURGE_SQL_RUNNER_SECURITY_ENABLED`
  - `JPY_MAX_FILE_SIZE_MB` → `SPLURGE_SQL_RUNNER_MAX_FILE_SIZE_MB`
  - `JPY_MAX_STATEMENTS_PER_FILE` → `SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE`
  - `JPY_VERBOSE` → `SPLURGE_SQL_RUNNER_VERBOSE`
  - `JPY_LOG_LEVEL` → `SPLURGE_SQL_RUNNER_LOG_LEVEL`
  - `JPY_LOG_FORMAT` → `SPLURGE_SQL_RUNNER_LOG_FORMAT`
