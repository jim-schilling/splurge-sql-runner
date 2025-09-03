# splurge-sql-runner
Splurge Python SQL Runner

A Python utility for executing SQL files against databases with support for multiple statements, comments, and pretty-printed results.

## Features

- Execute SQL files with multiple statements
- Support for various database backends (SQLite, PostgreSQL, MySQL, etc.)
- Automatic comment removal and statement parsing
- Pretty-printed results with tabulated output
- Batch processing of multiple files
- Batch SQL execution with error handling
- Clean CLI interface with comprehensive error handling
- Security validation for database URLs and file operations
- Configuration management with JSON-based config files
- Configurable logging for CLI usage (level, format, console/file output)

## Installation

```bash
pip install splurge-sql-runner
```

## CLI Usage

The main interface is through the command-line tool:

### Basic Usage

```bash
# Execute a single SQL file
python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql"

# Execute multiple SQL files using a pattern
python -m splurge_sql_runner -c "sqlite:///database.db" -p "*.sql"

# With verbose output
python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql" -v

# Using the installed script (after pip install)
splurge-sql-runner -c "sqlite:///database.db" -f "script.sql"

# Load with a JSON config file
python -m splurge_sql_runner --config config.json -c "sqlite:///database.db" -f "script.sql"

# Output as JSON (for scripting)
python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql" --json

# Disable emoji (useful on limited consoles)
python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql" --no-emoji

# Continue executing statements after an error (per-file)
python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql" --continue-on-error
```

### Command Line Options

- `-c, --connection`: Database connection string (required)
  - SQLite: `sqlite:///database.db`
  - PostgreSQL: `postgresql://user:pass@localhost/db`
  - MySQL: `mysql://user:pass@localhost/db`
  
- `-f, --file`: Single SQL file to execute
  
- `-p, --pattern`: File pattern to match multiple SQL files (e.g., "*.sql")
  
- `-v, --verbose`: Enable verbose output
  
- `--debug`: Enable SQLAlchemy debug mode (SQLAlchemy echo)

- `--config FILE`: Path to JSON config file. Values from the file are merged with defaults and overridden
  by any CLI arguments.

- `--json`: Output results as JSON (machine-readable).

- `--no-emoji`: Replace emoji glyphs with ASCII tags in output.

- `--continue-on-error`: Continue processing remaining statements after an error (default is stop on first error).

Security validation cannot be disabled. If stricter defaults block your use case, adjust `SecurityConfig` in your JSON config (e.g., `security.max_statements_per_file`, `security.allowed_file_extensions`, or dangerous pattern lists) and rerun.

- `--max-statements`: Maximum statements per file (default: 100)

### Examples

```bash
# SQLite example
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql"

# PostgreSQL example
python -m splurge_sql_runner -c "postgresql://user:pass@localhost/mydb" -p "migrations/*.sql"

# MySQL example with verbose output
python -m splurge_sql_runner -c "mysql://user:pass@localhost/mydb" -f "data.sql" -v

# Process all SQL files in current directory
python -m splurge_sql_runner -c "sqlite:///database.db" -p "*.sql"

# Adjust security via config (example)
# config.json
#{
#  "security": {
#    "max_statements_per_file": 500,
#    "allowed_file_extensions": [".sql", ".ddl"]
#  }
#}
python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql"
```

## Security Tuning

Security is enforced by default. If your workflow requires broader allowances, tune these fields in your
JSON configuration file:

- `security.max_statements_per_file` (int): Maximum SQL statements allowed per file. Increase if you run
  bulk scripts. CLI also accepts `--max-statements` to override per run.
- `security.validation.max_statement_length` (int): Maximum size in characters for a single statement.
- `security.allowed_file_extensions` (list[str]): Allowed extensions for SQL files (e.g., `[".sql", ".ddl"]`).
- `security.validation.dangerous_sql_patterns` (list[str]): Substrings considered dangerous in SQL. Remove
  or modify with caution.
- `security.validation.dangerous_path_patterns` (list[str]): Path substrings that are blocked for file safety.
- `security.validation.dangerous_url_patterns` (list[str]): Connection URL substrings that are blocked.

Example minimal config to relax limits:

```json
{
  "security": {
    "max_statements_per_file": 500,
    "allowed_file_extensions": [".sql", ".ddl"],
    "validation": {
      "max_statement_length": 200000
    }
  }
}
```

## Logging Behavior

Logging is configured via the `logging` section in your JSON config and is applied automatically on startup:

- `logging.level`: One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- `logging.format`: `TEXT` (human-readable) or `JSON`.
- `logging.enable_console`: Whether to log to console.
- `logging.enable_file`: Whether to log to a file.
- `logging.log_file`/`logging.log_dir`: Exact file or directory to write logs. If only `log_dir` is provided, a default filename is used.
- `logging.backup_count`: Number of daily-rotated log files to keep.

CLI will bootstrap minimal logging with default values and then reconfigure using your JSON config (if provided) before running.

## Notes on paths and patterns

- The `--file` path is expanded with `~` (home) and resolved to an absolute path before use.
- The `--pattern` is expanded for `~` and matched with glob; matched files are resolved to absolute paths.

## Programmatic Usage

**Note**: This library is primarily designed to be used via the CLI interface. The programmatic API is provided for advanced use cases and integration scenarios, but the CLI offers the most comprehensive features and best user experience.

### Basic Usage

```python
from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.config.database_config import DatabaseConfig

client = DatabaseClient(DatabaseConfig(url="sqlite:///database.db"))

try:
    results = client.execute_batch("SELECT 1;")
    for r in results:
        print(r)
finally:
    client.close()
```

### Advanced Usage

```python
from splurge_sql_runner.config import AppConfig
from splurge_sql_runner.database import DatabaseClient

config = AppConfig.load("config.json")

client = DatabaseClient(config.database)

try:
    results = client.execute_batch("SELECT 1; INSERT INTO test VALUES (1);")
    for result in results:
        print(f"Statement type: {result['statement_type']}")
        if result['statement_type'] == 'fetch':
            print(f"Rows returned: {result['row_count']}")
finally:
    client.close()
```



## Configuration

The library supports JSON-based configuration files for advanced usage:

```json
{
    "database": {
        "url": "sqlite:///database.db",
        "connection": {
            "timeout": 30
        },
        "enable_debug": false
    },
    "security": {
        "enable_validation": true,
        "max_statements_per_file": 100
    },
    "logging": {
        "level": "INFO",
        "format": "TEXT",
        "enable_console": true,
        "enable_file": false
    }
}
```

## SQL File Format

The tool supports SQL files with:
- Multiple statements separated by semicolons
- Single-line comments (`-- comment`)
- Multi-line comments (`/* comment */`)
- Comments within string literals are preserved

Example SQL file:
```sql
-- Create table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- Insert data
INSERT INTO users (name) VALUES ('John');
INSERT INTO users (name) VALUES ('Jane');

-- Query data
SELECT * FROM users;
```

## Output Format

The CLI provides formatted output showing:
- File being processed
- Each statement executed
- Results in tabulated format for SELECT queries
- Success/error status for each statement
- Summary of files processed

## Error Handling

- Individual statement errors don't stop the entire batch
- Failed statements are reported with error details
- Database connections are properly cleaned up
- Exit codes indicate success/failure
- (Removed) Circuit breaker/retry error-recovery layers in favor of simple CLI errors
- Security validation with configurable thresholds

## License

MIT License - see LICENSE file for details.

## Development

### Installation for Development

```bash
# Clone the repository
git clone https://github.com/jim-schilling/splurge-sql-runner.git
cd splurge-sql-runner

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Run tests
pytest -x -v

# Run specific test types
python tests/run_tests.py unit              # Run unit tests only
python tests/run_tests.py integration       # Run integration tests only
python tests/run_tests.py e2e               # Run end-to-end tests only
python tests/run_tests.py all --coverage    # Run all tests with coverage
python tests/run_tests.py coverage          # Generate coverage report

# Run linting
flake8 splurge_sql_runner/
black splurge_sql_runner/
mypy splurge_sql_runner/
```

## Testing

This project uses a comprehensive multi-layered testing approach to ensure quality and reliability:

### Test Structure

```
tests/
├── conftest.py              # Shared test fixtures and configuration
├── run_tests.py             # Test runner script for different test types
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_database_operations.py
│   ├── test_config_integration.py
│   └── test_sql_processing.py
├── e2e/                     # End-to-end tests
│   ├── __init__.py
│   └── test_cli_workflow.py
└── [existing unit tests]    # Unit tests for individual components
```

### Test Types

#### Unit Tests (`tests/test_*.py`)
- Test individual components in isolation
- Focus on specific functions, classes, and methods
- Use mocks for external dependencies where appropriate
- Fast execution, high coverage of edge cases

#### Integration Tests (`tests/integration/`)
- Test component interactions and data flow
- Use real database connections (SQLite for testing)
- Verify that components work together correctly
- Focus on realistic usage scenarios

#### End-to-End Tests (`tests/e2e/`)
- Test complete workflows from CLI to database
- Use actual command-line invocations
- Verify the full application lifecycle
- Include error handling and recovery scenarios

### Test Markers

The project uses pytest markers to categorize tests:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.database` - Database-dependent tests
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.performance` - Performance tests

### Running Tests

#### Using the Test Runner Script
```bash
# Run all tests
python tests/run_tests.py all

# Run specific test types
python tests/run_tests.py unit
python tests/run_tests.py integration
python tests/run_tests.py e2e

# Run with coverage
python tests/run_tests.py all --coverage
python tests/run_tests.py coverage  # Generate HTML coverage report
```

#### Using Pytest Directly
```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m e2e

# Run with coverage
pytest --cov=splurge_sql_runner --cov-report=html --cov-report=term-missing

# Run specific test files
pytest tests/integration/test_database_operations.py
pytest tests/e2e/test_cli_workflow.py
```

### Test Coverage

The project maintains high test coverage with a target of 85% across all modules:

- **Current Coverage**: 30% (baseline before recent improvements)
- **Target Coverage**: 85% for all public interfaces
- **Coverage Reports**: Generated in `htmlcov/` directory

### Test Data and Fixtures

The testing framework provides comprehensive fixtures for common testing scenarios:

- **Database fixtures**: SQLite in-memory and file-based databases
- **Configuration fixtures**: Valid and invalid configuration data
- **SQL fixtures**: Sample SQL files with various constructs
- **CLI fixtures**: Simulated command-line arguments and outputs

### Continuous Integration

Tests are designed to run in CI/CD environments with:

- Parallel test execution support (`pytest-xdist`)
- Proper isolation between test runs
- Comprehensive error reporting
- Coverage reporting integration

### Writing Tests

When adding new tests:

1. **Unit Tests**: Place in `tests/` directory with descriptive names
2. **Integration Tests**: Place in `tests/integration/` directory
3. **E2E Tests**: Place in `tests/e2e/` directory
4. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
5. **Follow naming conventions**: `test_*` for functions, `Test*` for classes
6. **Use fixtures**: Leverage existing fixtures from `conftest.py`
7. **Test real behavior**: Prefer real objects over mocks where possible

### Test Quality Standards

- **Public API focus**: Test observable behavior, not implementation details
- **Real data**: Use actual data and realistic scenarios
- **Error handling**: Test both success and failure paths
- **Performance awareness**: Mark slow tests appropriately
- **Documentation**: Include docstrings explaining test purpose

## Changelog

### 2025.4.2 (09-03-2025)

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

