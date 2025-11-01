# splurge-sql-runner API Reference

A comprehensive guide to the public APIs and error handling for `splurge-sql-runner`.

**Version**: 2025.7.0

---

## Table of Contents

1. [Core APIs](#core-apis)
2. [Configuration](#configuration)
3. [Error Handling](#error-handling)
4. [Exception Migration Guide](#exception-migration-guide)
5. [Security](#security)
6. [Database Operations](#database-operations)
7. [Logging](#logging)
8. [Utilities](#utilities)
9. [CLI Usage](#cli-usage)
10. [Example Usage](#example-usage)

---

## Core APIs

### `process_sql()`

Execute raw SQL content with validation and security checks.

**Location**: `splurge_sql_runner.main.process_sql`

```python
def process_sql(
    sql_content: str,
    *,
    database_url: str,
    config: dict | None = None,
    security_level: str = "normal",
    max_statements_per_file: int = 100,
    stop_on_error: bool = True,
) -> list[dict[str, Any]]:
```

**Parameters**:
- `sql_content` (str): Single SQL content block to execute
- `database_url` (str): Database connection string (required)
- `config` (dict, optional): Configuration dictionary. If None, loads defaults
- `security_level` (str): Security validation level - `"strict"`, `"normal"`, or `"permissive"` (default: `"normal"`)
- `max_statements_per_file` (int): Maximum statements allowed (default: 100)
- `stop_on_error` (bool): Whether to stop on first statement error (default: True)

**Returns**: List of result dictionaries from SQL execution. Each result contains:
- `statement` (str): The SQL statement text
- `statement_type` (str): One of `"fetch"`, `"execute"`, or `"error"`
- `result` (list[dict] | bool | None): Query results for fetch statements, True/None for execute statements, None for errors
- `row_count` (int | None): Number of rows returned/affected
- `error` (str | None): Error message if statement_type is "error"

**Raises**:
- `SplurgeSqlRunnerSecurityError`: If SQL content or database URL fails security validation
- `SplurgeSqlRunnerFileError`: If configuration file cannot be read
- `SplurgeSqlRunnerValueError`: If validation fails (invalid security level, URL format, etc.)

**Example**:
```python
from splurge_sql_runner import process_sql

results = process_sql(
    "SELECT * FROM users;",
    database_url="sqlite:///app.db",
    security_level="normal",
    max_statements_per_file=100
)
for result in results:
    if result["statement_type"] == "fetch":
        print(f"Rows returned: {result['row_count']}")
        for row in result["result"]:
            print(row)
    elif result["statement_type"] == "error":
        print(f"Error: {result['error']}")
```

---

### `process_sql_files()`

Execute SQL from files with validation and security checks.

**Location**: `splurge_sql_runner.main.process_sql_files`

```python
def process_sql_files(
    file_paths: list[str],
    *,
    database_url: str,
    config: dict | None = None,
    security_level: str = "normal",
    max_statements_per_file: int = 100,
    stop_on_error: bool = True,
) -> dict[str, Any]:
```

**Parameters**:
- `file_paths` (list[str]): List of SQL file paths to execute
- `database_url` (str): Database connection string (required)
- `config` (dict, optional): Configuration dictionary
- `security_level` (str): Security level - `"strict"`, `"normal"`, or `"permissive"`
- `max_statements_per_file` (int): Maximum statements per file
- `stop_on_error` (bool): Whether to stop on first statement error

**Returns**: Dictionary with:
- `files_processed` (int): Total number of files processed
- `files_passed` (int): Number of files with all statements successful
- `files_failed` (int): Number of files with all statements failed
- `files_mixed` (int): Number of files with mixed success/failure
- `results` (dict[str, list[dict]]): Mapping of file path to list of result dictionaries

**Raises**:
- `SplurgeSqlRunnerSecurityError`: If SQL content fails security validation
- `SplurgeSqlRunnerValueError`: If database URL validation fails or other validation errors
- `SplurgeSqlRunnerFileError`: If file cannot be read

**Example**:
```python
from splurge_sql_runner import process_sql_files

summary = process_sql_files(
    ["/path/to/schema.sql", "/path/to/data.sql"],
    database_url="postgresql://user:pass@localhost/db",
    security_level="strict",
    max_statements_per_file=50
)
print(f"Processed: {summary['files_processed']}")
print(f"Passed: {summary['files_passed']}")
for file_path, results in summary["results"].items():
    print(f"\n{file_path}:")
    for result in results:
        print(f"  {result['statement_type']}: {result.get('row_count', 'N/A')}")
```

---

### `DatabaseClient`

Low-level database client for direct SQL execution.

**Location**: `splurge_sql_runner.database.database_client.DatabaseClient`

```python
class DatabaseClient:
    def __init__(
        self,
        database_url: str,
        connection_timeout: float = 30.0,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
    ):
        """Initialize database client."""
```

**Methods**:

#### `connect() -> Connection`
Create a database connection.

```python
db_client = DatabaseClient("sqlite:///app.db")
connection = db_client.connect()
try:
    # Use connection
    pass
finally:
    db_client.close()
```

**Raises**: `SplurgeSqlRunnerDatabaseError` if connection cannot be established

#### `execute_sql(statements: list[str], stop_on_error: bool = True) -> list[dict[str, Any]]`
Execute a list of SQL statements.

```python
results = db_client.execute_sql([
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);",
    "INSERT INTO users (name) VALUES ('Alice');"
], stop_on_error=True)
```

**Parameters**:
- `statements` (list[str]): SQL statements to execute
- `stop_on_error` (bool): Stop on first error if True

**Returns**: List of result dicts with keys:
- `statement` (str): The executed statement
- `statement_type` (str): `"fetch"`, `"execute"`, or `"error"`
- `result` (list[dict] | bool | None): Query results for fetch, True/None for execute, None for error
- `row_count` (int | None): Number of rows returned/affected
- `error` (str | None): Error message if statement_type is "error"

**Note**: This method typically does not raise exceptions; errors are captured in result dictionaries. Connection failures may raise `SplurgeSqlRunnerDatabaseError`.

#### `close() -> None`
Close the database connection and dispose of connection pool.

```python
db_client.close()
```

---

## Configuration

### `load_config()`

Load application configuration from file and environment variables.

**Location**: `splurge_sql_runner.config.load_config`

```python
def load_config(config_file_path: str | None = None) -> dict[str, Any]:
```

**Parameters**:
- `config_file_path` (str, optional): Path to JSON configuration file

**Returns**: Configuration dictionary with keys:
- `database_url` (str): Database connection string
- `max_statements_per_file` (int): Maximum statements per file
- `connection_timeout` (float): Connection timeout in seconds
- `log_level` (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `security_level` (str): Security level (strict, normal, permissive)
- `enable_verbose` (bool): Verbose output enabled
- `enable_debug` (bool): Debug mode enabled

**Raises**:
- `SplurgeSqlRunnerFileError`: If configuration file cannot be read or parsed
- `SplurgeSqlRunnerValueError`: If configuration values are invalid

**Environment Variables**:
- `SPLURGE_SQL_RUNNER_DB_URL`: Database URL
- `SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE`: Max statements (int)
- `SPLURGE_SQL_RUNNER_CONNECTION_TIMEOUT`: Connection timeout (float)
- `SPLURGE_SQL_RUNNER_LOG_LEVEL`: Logging level
- `SPLURGE_SQL_RUNNER_VERBOSE`: Verbose output (true/1/yes/on)
- `SPLURGE_SQL_RUNNER_DEBUG`: Debug mode (true/1/yes/on)

**Example**:
```python
from splurge_sql_runner import load_config

# Load from file and environment
config = load_config("/etc/splurge-sql-runner/config.json")

# Load from environment only
config = load_config()

print(f"Database: {config['database_url']}")
print(f"Max statements: {config['max_statements_per_file']}")
```

**Configuration File Format** (JSON):
```json
{
  "database": {
    "url": "postgresql://localhost/mydb",
    "connection": {
      "timeout": 30
    }
  },
  "max_statements_per_file": 100,
  "enable_verbose_output": false,
  "enable_debug_mode": false,
  "logging": {
    "level": "INFO"
  },
  "security_level": "normal"
}
```

---

## Error Handling

All errors inherit from `SplurgeSqlRunnerError` which inherits from `SplurgeFrameworkError`.

### Simplified Exception Hierarchy

The package uses a simplified exception hierarchy for easier error handling:

```
SplurgeFrameworkError (from _vendor.splurge_safe_io)
└── SplurgeSqlRunnerError
    ├── SplurgeSqlRunnerOSError
    ├── SplurgeSqlRunnerRuntimeError
    ├── SplurgeSqlRunnerValueError
    ├── SplurgeSqlRunnerTypeError
    ├── SplurgeSqlRunnerConfigurationError
    ├── SplurgeSqlRunnerFileError
    ├── SplurgeSqlRunnerDatabaseError
    └── SplurgeSqlRunnerSecurityError
```

### Common Errors

#### `SplurgeSqlRunnerSecurityError`
Raised when security validation fails (SQL content, database URL patterns, etc.).

**Example**:
```python
from splurge_sql_runner import process_sql
from splurge_sql_runner.exceptions import SplurgeSqlRunnerSecurityError

try:
    results = process_sql(
        "DROP DATABASE production;",
        database_url="postgresql://localhost/db",
        security_level="strict"
    )
except SplurgeSqlRunnerSecurityError as e:
    print(f"Security check failed: {e}")
```

#### `SplurgeSqlRunnerFileError`
Raised when file operations fail (reading config files, SQL files, etc.).

**Example**:
```python
from splurge_sql_runner import process_sql_files
from splurge_sql_runner.exceptions import SplurgeSqlRunnerFileError

try:
    results = process_sql_files(
        ["/nonexistent/file.sql"],
        database_url="sqlite:///app.db"
    )
except SplurgeSqlRunnerFileError as e:
    print(f"File error: {e}")
```

#### `SplurgeSqlRunnerDatabaseError`
Raised when database operations fail (connection, execution, etc.).

**Example**:
```python
from splurge_sql_runner import DatabaseClient
from splurge_sql_runner.exceptions import SplurgeSqlRunnerDatabaseError

try:
    client = DatabaseClient("postgresql://invalid-host/db")
    client.connect()
except SplurgeSqlRunnerDatabaseError as e:
    print(f"Cannot connect to database: {e}")
```

#### `SplurgeSqlRunnerValueError`
Raised when validation fails (invalid security level, configuration values, etc.).

**Example**:
```python
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.exceptions import SplurgeSqlRunnerValueError

try:
    SecurityValidator.validate_database_url(
        "postgresql://localhost/db",
        security_level="invalid_level"
    )
except SplurgeSqlRunnerValueError as e:
    print(f"Invalid value: {e}")
```

---

## Exception Migration Guide

### Overview

As of version 2025.7.0, the exception hierarchy has been simplified. Specific exception types have been consolidated into more general categories to simplify error handling.

### Exception Mapping

| Old Exception (Deprecated) | New Exception | Notes |
|---------------------------|---------------|-------|
| `SplurgeSqlRunnerSecurityValidationError` | `SplurgeSqlRunnerSecurityError` | All security validation errors |
| `SplurgeSqlRunnerSecurityUrlError` | `SplurgeSqlRunnerSecurityError` or `SplurgeSqlRunnerValueError` | URL pattern errors → SecurityError, format errors → ValueError |
| `SplurgeSqlRunnerSecurityFileError` | `SplurgeSqlRunnerSecurityError` | File security validation errors |
| `SplurgeSqlRunnerConfigFileError` | `SplurgeSqlRunnerFileError` | Configuration file errors |
| `SplurgeSqlRunnerConfigValidationError` | `SplurgeSqlRunnerValueError` | Configuration validation errors |
| `SplurgeSqlRunnerSqlFileError` | `SplurgeSqlRunnerFileError` | SQL file reading errors |
| `SplurgeSqlRunnerCliSecurityError` | `SplurgeSqlRunnerSecurityError` | CLI security errors |

### Migration Examples

**Before**:
```python
from splurge_sql_runner.exceptions import (
    SplurgeSqlRunnerSecurityValidationError,
    SplurgeSqlRunnerSecurityUrlError,
    SplurgeSqlRunnerConfigFileError,
    SplurgeSqlRunnerSqlFileError,
)

try:
    results = process_sql_files(["schema.sql"], database_url="...")
except SplurgeSqlRunnerSecurityValidationError:
    # Handle SQL validation error
    pass
except SplurgeSqlRunnerSecurityUrlError:
    # Handle URL validation error
    pass
except SplurgeSqlRunnerConfigFileError:
    # Handle config file error
    pass
except SplurgeSqlRunnerSqlFileError:
    # Handle SQL file error
    pass
```

**After**:
```python
from splurge_sql_runner.exceptions import (
    SplurgeSqlRunnerSecurityError,
    SplurgeSqlRunnerFileError,
    SplurgeSqlRunnerValueError,
)

try:
    results = process_sql_files(["schema.sql"], database_url="...")
except SplurgeSqlRunnerSecurityError:
    # Handle all security validation errors (SQL, URL patterns)
    pass
except SplurgeSqlRunnerFileError:
    # Handle all file errors (config files, SQL files)
    pass
except SplurgeSqlRunnerValueError:
    # Handle validation errors (invalid security level, URL format, etc.)
    pass
```

### Benefits of Simplified Exceptions

1. **Easier Error Handling**: Fewer exception types to catch
2. **Clearer Intent**: Group related errors together
3. **Backward Compatible**: Old exception names still exist but are deprecated
4. **Simpler API**: Less to remember and document

---

## Security

### Security Levels

The system supports three security levels that apply different validation patterns:

#### `strict`
Most restrictive; rejects paths and SQL patterns that could be dangerous.

**Patterns Blocked**:
- Paths: `..`, `~`, `/etc`, `/var`, `/usr`, `/bin`, `/sbin`, `/dev`, `\windows\system32`, etc.
- SQL: `DROP DATABASE`, `TRUNCATE DATABASE`, `DELETE FROM INFORMATION_SCHEMA`, `EXEC`, `XP_`, `SP_`, etc.
- URLs: `--`, `/*`, `*/`, `xp_`, `sp_`, `exec`, `execute`, `script:`, `javascript:`, `data:`

#### `normal` (default)
Balanced security; blocks most dangerous patterns while allowing common operations.

**Patterns Blocked**:
- Paths: `..`, `~`, `/etc`, `/var`, `\windows\system32`
- SQL: `DROP DATABASE`, `EXEC `, `EXECUTE `, `XP_`, `SP_`
- URLs: `script:`, `javascript:`, `data:`

#### `permissive`
Minimal validation; only checks basic constraints.

**Patterns Blocked**:
- Paths: `..`
- SQL: (none)
- URLs: (none)

### SecurityValidator API

**Location**: `splurge_sql_runner.security.SecurityValidator`

#### `validate_database_url(database_url: str, security_level: str = "normal")`

Validate database URL for security concerns.

```python
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.exceptions import SplurgeSqlRunnerSecurityError, SplurgeSqlRunnerValueError

try:
    SecurityValidator.validate_database_url(
        "postgresql://user:pass@localhost/db",
        security_level="strict"
    )
except SplurgeSqlRunnerSecurityError as e:
    print(f"URL contains dangerous pattern: {e}")
except SplurgeSqlRunnerValueError as e:
    print(f"Invalid URL format: {e}")
```

**Raises**:
- `SplurgeSqlRunnerSecurityError`: If URL contains dangerous patterns
- `SplurgeSqlRunnerValueError`: If URL format is invalid or security level is unsupported

#### `validate_sql_content(sql: str, security_level: str, max_statements: int)`

Validate SQL content for security concerns.

```python
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.exceptions import SplurgeSqlRunnerSecurityError, SplurgeSqlRunnerValueError

try:
    SecurityValidator.validate_sql_content(
        "SELECT * FROM users;",
        security_level="normal",
        max_statements=100
    )
except SplurgeSqlRunnerSecurityError as e:
    print(f"SQL validation failed: {e}")
except SplurgeSqlRunnerValueError as e:
    print(f"Invalid security level: {e}")
```

**Raises**:
- `SplurgeSqlRunnerSecurityError`: If SQL contains dangerous patterns or exceeds statement limit
- `SplurgeSqlRunnerValueError`: If security level is unsupported

---

## Database Operations

### Supported Databases

The system uses SQLAlchemy and supports any database with a SQLAlchemy dialect:

- **SQLite**: `sqlite:///path/to/database.db` or `sqlite:///:memory:`
- **PostgreSQL**: `postgresql://user:password@localhost:5432/database`
- **MySQL**: `mysql+pymysql://user:password@localhost:3306/database`
- **SQL Server**: `mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+17+for+SQL+Server`
- **Oracle**: `oracle+cx_oracle://user:password@localhost:1521/database`
- **Others**: Any database with SQLAlchemy dialect support

### Result Format

Each result dictionary contains:

**For fetch statements (SELECT, VALUES, etc.)**:
```python
{
    "statement": "SELECT * FROM users;",
    "statement_type": "fetch",
    "result": [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ],
    "row_count": 2,
    "error": None
}
```

**For execute statements (INSERT, UPDATE, DELETE, DDL)**:
```python
{
    "statement": "INSERT INTO users (name) VALUES ('Charlie');",
    "statement_type": "execute",
    "result": True,
    "row_count": 1,
    "error": None
}
```

**For errors**:
```python
{
    "statement": "INVALID SQL SYNTAX;",
    "statement_type": "error",
    "result": None,
    "row_count": None,
    "error": "Syntax error: near 'INVALID'"
}
```

### Connection Management

For long-lived processes, manage connections properly:

```python
from splurge_sql_runner import DatabaseClient

client = DatabaseClient(
    "sqlite:///app.db",
    connection_timeout=30.0,
    pool_size=5,        # For non-SQLite databases
    max_overflow=10,    # For non-SQLite databases
    pool_pre_ping=True  # Verify connections before use
)

try:
    results = client.execute_sql(["SELECT 1;"])
    print(results)
finally:
    client.close()  # Always close to release connections
```

**Note**: SQLite does not use connection pooling and ignores `pool_size`, `max_overflow`, and `pool_pre_ping` parameters.

---

## Logging

### Setup Logging

Configure application logging.

**Location**: `splurge_sql_runner.logging.setup_logging`

```python
from splurge_sql_runner import setup_logging

setup_logging(
    log_level="INFO",
    log_file="/var/log/app.log",
    enable_console=True,
    backup_count=7
)
```

**Parameters**:
- `log_level` (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_file` (str | None): Specific log file path (optional)
- `log_dir` (str | None): Directory for log files (optional)
- `enable_console` (bool): Whether to enable console logging (default: True)
- `enable_json` (bool): Whether to use JSON formatting for file logs (default: False)
- `backup_count` (int): Number of backup files to keep (default: 7)

**Raises**:
- `SplurgeSqlRunnerValueError`: If log_level is invalid
- `SplurgeSqlRunnerOSError`: If log directory cannot be created

### Get Logger

Get a module-specific logger.

**Location**: `splurge_sql_runner.logging.get_logger`

```python
from splurge_sql_runner import get_logger

logger = get_logger("my_module")
logger.info("Application started")
```

### Contextual Logging

Track operations across distributed systems with correlation IDs.

**Location**: `splurge_sql_runner.logging`

```python
from splurge_sql_runner import (
    generate_correlation_id,
    set_correlation_id,
    get_contextual_logger,
    correlation_context
)

# Generate unique ID for this request
correlation_id = generate_correlation_id()
set_correlation_id(correlation_id)

# All logs from contextual logger include correlation ID
logger = get_contextual_logger("my_module")
logger.info("Processing request")

# Or use context manager
with correlation_context("new-request-id"):
    logger = get_contextual_logger("my_module")
    logger.info("Inside context")
```

---

## Utilities

### FileIoAdapter

Secure file I/O operations with error translation.

**Location**: `splurge_sql_runner.utils.file_io_adapter.FileIoAdapter`

```python
from splurge_sql_runner import FileIoAdapter

# Read file
content = FileIoAdapter.read_file(
    "/path/to/file.sql",
    context_type="sql"
)

# Read file in chunks (for large files)
for chunk in FileIoAdapter.read_file_chunked(
    "/path/to/large.sql",
    context_type="sql"
):
    for line in chunk:
        process_line(line)

# Validate file size
size_mb = FileIoAdapter.validate_file_size(
    "/path/to/file.sql",
    max_size_mb=500
)
```

**Raises**: `SplurgeSqlRunnerFileError` if file operations fail

---

## CLI Usage

### Command Line Interface

Execute SQL files from the command line.

**Location**: `splurge_sql_runner.cli.main`

```bash
# Run single SQL file
python -m splurge_sql_runner -c "sqlite:///app.db" -f "schema.sql"

# Run files matching pattern
python -m splurge_sql_runner -c "postgresql://localhost/db" -p "migrations/*.sql"

# With configuration file
python -m splurge_sql_runner -f "data.sql" --config config.json -c "sqlite:///app.db"

# Verbose output
python -m splurge_sql_runner -c "sqlite:///app.db" -f "schema.sql" -v

# Set max statements
python -m splurge_sql_runner -c "sqlite:///app.db" -f "large.sql" --max-statements 500

# Continue on error
python -m splurge_sql_runner -c "sqlite:///app.db" -f "script.sql" --continue-on-error

# JSON output
python -m splurge_sql_runner -c "sqlite:///app.db" -f "queries.sql" --json
```

### Exit Codes

- `0`: Success - all files processed successfully
- `1`: Failure - all files failed to process
- `2`: Partial success - some files succeeded, some failed
- `3`: Unknown error - configuration or setup error

### Environment Variables

- `SPLURGE_SQL_RUNNER_DB_URL`: Database URL (overrides CLI argument)
- `SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE`: Max statements
- `SPLURGE_SQL_RUNNER_CONNECTION_TIMEOUT`: Connection timeout
- `SPLURGE_SQL_RUNNER_LOG_LEVEL`: Logging level
- `SPLURGE_SQL_RUNNER_VERBOSE`: Verbose output
- `SPLURGE_SQL_RUNNER_DEBUG`: Debug mode

---

## Example Usage

### Basic Script Execution

```python
from splurge_sql_runner import process_sql_files, load_config
from splurge_sql_runner.exceptions import (
    SplurgeSqlRunnerError,
    SplurgeSqlRunnerSecurityError,
    SplurgeSqlRunnerFileError,
)

# Load configuration
config = load_config()

try:
    # Execute SQL files
    summary = process_sql_files(
        ["schema.sql", "data.sql"],
        database_url=config["database_url"],
        security_level=config.get("security_level", "normal"),
        max_statements_per_file=config["max_statements_per_file"],
        stop_on_error=False  # Continue even if one fails
    )
    
    # Process results
    print(f"Files processed: {summary['files_processed']}")
    print(f"Files passed: {summary['files_passed']}")
    
    for file_path, results in summary["results"].items():
        print(f"\n{file_path}:")
        for result in results:
            if result["statement_type"] == "error":
                print(f"  ERROR: {result['error']}")
            elif result["statement_type"] == "fetch":
                print(f"  Rows returned: {result['row_count']}")
            else:
                print(f"  Rows affected: {result.get('row_count', 'N/A')}")
            
except SplurgeSqlRunnerSecurityError as e:
    print(f"Security error: {e}")
except SplurgeSqlRunnerFileError as e:
    print(f"File error: {e}")
except SplurgeSqlRunnerError as e:
    print(f"Error: {e}")
```

### Direct Database Operations

```python
from splurge_sql_runner import DatabaseClient
from splurge_sql_runner.exceptions import SplurgeSqlRunnerDatabaseError

client = DatabaseClient("sqlite:///app.db")

try:
    # Create table
    results = client.execute_sql([
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT);"
    ])
    
    # Insert data
    results = client.execute_sql([
        "INSERT INTO users (name) VALUES ('Alice'), ('Bob'), ('Charlie');"
    ])
    if results and results[0]["statement_type"] == "execute":
        print(f"Inserted {results[0]['row_count']} rows")
    
    # Query data
    results = client.execute_sql([
        "SELECT * FROM users WHERE name LIKE 'A%';"
    ])
    if results and results[0]["statement_type"] == "fetch":
        for row in results[0]["result"]:
            print(f"User: {row['name']}")
            
except SplurgeSqlRunnerDatabaseError as e:
    print(f"Database error: {e}")
finally:
    client.close()
```

### Security-Aware Operations

```python
from splurge_sql_runner import process_sql
from splurge_sql_runner.exceptions import (
    SplurgeSqlRunnerSecurityError,
    SplurgeSqlRunnerValueError,
)

# Strict mode - only safe operations
try:
    results = process_sql(
        "SELECT COUNT(*) FROM audit_log;",
        database_url="postgresql://readonly@prod.example.com/analytics",
        security_level="strict",
        max_statements_per_file=10
    )
except SplurgeSqlRunnerSecurityError as e:
    print(f"Security validation failed: {e}")
except SplurgeSqlRunnerValueError as e:
    print(f"Validation error: {e}")
```

### Error Handling

```python
from splurge_sql_runner import process_sql_files
from splurge_sql_runner.exceptions import (
    SplurgeSqlRunnerError,
    SplurgeSqlRunnerSecurityError,
    SplurgeSqlRunnerFileError,
    SplurgeSqlRunnerDatabaseError,
    SplurgeSqlRunnerValueError,
)

try:
    summary = process_sql_files(
        ["schema.sql"],
        database_url="postgresql://localhost/db"
    )
except SplurgeSqlRunnerSecurityError as e:
    print(f"Security validation failed: {e}")
except SplurgeSqlRunnerFileError as e:
    print(f"File error: {e}")
except SplurgeSqlRunnerDatabaseError as e:
    print(f"Database error: {e}")
except SplurgeSqlRunnerValueError as e:
    print(f"Validation error: {e}")
except SplurgeSqlRunnerError as e:
    print(f"Unexpected error: {e}")
```

---

## Version Information

- **Current Version**: 2025.7.0
- **Python Support**: 3.10+
- **License**: MIT

See [CHANGELOG.md](../../CHANGELOG.md) for version history.

---

## Additional Resources

- [README](../../README.md) - Project overview and quick start
- [CLI Examples](../../examples/cli_examples.md) - Command-line usage examples
