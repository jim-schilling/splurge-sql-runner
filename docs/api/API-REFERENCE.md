# splurge-sql-runner API Reference

A comprehensive guide to the public APIs and error handling for `splurge-sql-runner`.

**Version**: 2025.6.0

---

## Table of Contents

1. [Core APIs](#core-apis)
2. [Configuration](#configuration)
3. [Error Handling](#error-handling)
4. [Security](#security)
5. [Database Operations](#database-operations)
6. [Logging](#logging)
7. [Utilities](#utilities)
8. [CLI Usage](#cli-usage)
9. [Example Usage](#example-usage)

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

**Returns**: List of result dictionaries from SQL execution

**Raises**:
- `SecurityValidationError`: If SQL content fails security validation
- `SecurityUrlError`: If database URL fails security validation
- `DatabaseError`: If database connection or execution fails

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
    print(f"Statement: {result['statement']}, Rows: {result.get('row_count', 0)}")
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
) -> list[dict[str, Any]]:
```

**Parameters**:
- `file_paths` (list[str]): List of SQL file paths to execute
- `database_url` (str): Database connection string (required)
- `config` (dict, optional): Configuration dictionary
- `security_level` (str): Security level - `"strict"`, `"normal"`, or `"permissive"`
- `max_statements_per_file` (int): Maximum statements per file
- `stop_on_error` (bool): Whether to stop on first statement error

**Returns**: List of result dictionaries

**Raises**:
- `SecurityValidationError`: If file path or content fails security validation
- `SecurityFileError`: If file access is blocked by security policy
- `FileError`: If file cannot be read
- `DatabaseError`: If database operation fails

**Example**:
```python
from splurge_sql_runner import process_sql_files

results = process_sql_files(
    ["/path/to/schema.sql", "/path/to/data.sql"],
    database_url="postgresql://user:pass@localhost/db",
    security_level="strict",
    max_statements_per_file=50
)
```

---

### `DatabaseClient`

Low-level database client for direct SQL execution.

**Location**: `splurge_sql_runner.DatabaseClient`

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

**Raises**: `DatabaseConnectionError` if connection cannot be established

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
- `success` (bool): Whether execution succeeded
- `row_count` (int): For DML, rows affected; for SELECT, rows returned
- `error` (str, optional): Error message if execution failed
- `error_type` (str, optional): Type of error if execution failed

#### `execute_select(query: str) -> list[dict[str, Any]]`
Execute a SELECT query and return rows.

```python
rows = db_client.execute_select("SELECT * FROM users WHERE active = true")
for row in rows:
    print(row)
```

#### `close() -> None`
Close the database connection.

```python
db_client.close()
```

---

## Configuration

### `load_config()`

Load application configuration from file and environment variables.

**Location**: `splurge_sql_runner.load_config`

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

### Exception Hierarchy

```
SplurgeFrameworkError (from _vendor.splurge_safe_io)
└── SplurgeSqlRunnerError
    ├── ConfigurationError
    │   ├── ConfigValidationError
    │   └── ConfigFileError
    ├── ValidationError
    │   └── SecurityError
    │       ├── SecurityValidationError
    │       ├── SecurityFileError
    │       └── SecurityUrlError
    ├── OperationError
    │   ├── FileError
    │   ├── DatabaseError
    │   │   ├── DatabaseConnectionError
    │   │   ├── DatabaseOperationError
    │   │   ├── DatabaseBatchError
    │   │   ├── DatabaseEngineError
    │   │   ├── DatabaseTimeoutError
    │   │   └── DatabaseAuthenticationError
    │   ├── CliError
    │   │   ├── CliArgumentError
    │   │   ├── CliFileError
    │   │   ├── CliExecutionError
    │   │   └── CliSecurityError
    │   └── SqlError
    │       ├── SqlParseError
    │       ├── SqlFileError
    │       ├── SqlValidationError
    │       └── SqlExecutionError
```

### Common Errors

#### `SecurityValidationError`
Raised when SQL content fails security validation.

**Attributes**:
- `message` (str): Description of the security violation
- `details` (dict): Additional context

**Example**:
```python
from splurge_sql_runner import process_sql, SecurityValidationError

try:
    results = process_sql(
        "DROP DATABASE production;",
        database_url="postgresql://localhost/db",
        security_level="strict"
    )
except SecurityValidationError as e:
    print(f"Security check failed: {e}")
    print(f"Details: {e.details}")
```

#### `SecurityUrlError`
Raised when database URL fails security validation.

**Example**:
```python
from splurge_sql_runner import process_sql, SecurityUrlError

try:
    results = process_sql(
        "SELECT 1;",
        database_url="invalid://url",
        security_level="strict"
    )
except SecurityUrlError as e:
    print(f"Invalid database URL: {e}")
```

#### `SecurityFileError`
Raised when file path fails security checks.

**Example**:
```python
from splurge_sql_runner import process_sql_files, SecurityFileError

try:
    results = process_sql_files(
        ["/etc/passwd"],  # Blocked path
        database_url="sqlite:///app.db",
        security_level="strict"
    )
except SecurityFileError as e:
    print(f"File access denied: {e}")
```

#### `DatabaseConnectionError`
Raised when database connection fails.

**Example**:
```python
from splurge_sql_runner import DatabaseClient, DatabaseConnectionError

try:
    client = DatabaseClient("postgresql://invalid-host/db")
    client.connect()
except DatabaseConnectionError as e:
    print(f"Cannot connect to database: {e}")
```

#### `FileError`
Raised when file operations fail.

**Example**:
```python
from splurge_sql_runner import process_sql_files, FileError

try:
    results = process_sql_files(
        ["/nonexistent/file.sql"],
        database_url="sqlite:///app.db"
    )
except FileError as e:
    print(f"File not found: {e}")
```

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
from splurge_sql_runner.exceptions import SecurityUrlError

try:
    SecurityValidator.validate_database_url(
        "postgresql://user:pass@localhost/db",
        security_level="strict"
    )
except SecurityUrlError as e:
    print(f"Invalid URL: {e}")
```

**Raises**: `SecurityUrlError` if URL contains dangerous patterns

#### `validate_sql_content(sql: str, security_level: str, max_statements: int)`
Validate SQL content for security concerns.

```python
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.exceptions import SecurityValidationError

try:
    SecurityValidator.validate_sql_content(
        "SELECT * FROM users;",
        security_level="normal",
        max_statements=100
    )
except SecurityValidationError as e:
    print(f"SQL validation failed: {e}")
```

**Raises**: `SecurityValidationError` if SQL fails validation

#### `validate_file_path(file_path: str, security_level: str)`
Validate file path for security concerns.

```python
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.exceptions import SecurityFileError

try:
    SecurityValidator.validate_file_path(
        "/app/scripts/schema.sql",
        security_level="strict"
    )
except SecurityFileError as e:
    print(f"File path rejected: {e}")
```

**Raises**: `SecurityFileError` if file path fails validation

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

```python
{
    "statement": "SELECT * FROM users;",
    "success": True,
    "row_count": 5,  # For SELECT, number of rows; for INSERT/UPDATE/DELETE, rows affected
    "error": None,
    "error_type": None
}
```

Or on error:

```python
{
    "statement": "INVALID SQL SYNTAX;",
    "success": False,
    "row_count": 0,
    "error": "Syntax error at offset 0",
    "error_type": "ProgrammingError"
}
```

### Connection Management

For long-lived processes, manage connections properly:

```python
from splurge_sql_runner import DatabaseClient

client = DatabaseClient(
    "sqlite:///app.db",
    connection_timeout=30.0,
    pool_size=5,        # For non-SQLite
    max_overflow=10,    # For non-SQLite
    pool_pre_ping=True  # Verify connections before use
)

try:
    results = client.execute_sql(["SELECT 1;"])
    print(results)
finally:
    client.close()  # Always close to release connections
```

---

## Logging

### Setup Logging

Configure application logging.

**Location**: `splurge_sql_runner.setup_logging`

```python
from splurge_sql_runner import setup_logging

setup_logging(
    level="INFO",
    format="json",  # or "text"
    file="/var/log/app.log"
)
```

### Get Logger

Get a module-specific logger.

**Location**: `splurge_sql_runner.get_logger`

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
    logger.info("Inside context")
```

---

## Utilities

### FileIoAdapter

Secure file I/O operations.

**Location**: `splurge_sql_runner.FileIoAdapter`

```python
from splurge_sql_runner import FileIoAdapter

# Read file
content = FileIoAdapter.read_file(
    "/path/to/file.sql",
    context_type="sql"
)

# Write file
FileIoAdapter.write_file(
    "/path/to/output.txt",
    "content",
    context_type="output"
)
```

---

## CLI Usage

### Command Line Interface

Execute SQL files from the command line.

**Location**: `splurge_sql_runner/__main__.py`

```bash
# Run single SQL file
python -m splurge_sql_runner --file schema.sql --database-url "sqlite:///app.db"

# Run files matching pattern
python -m splurge_sql_runner --pattern "migrations/*.sql" --database-url "postgresql://localhost/db"

# With configuration file
python -m splurge_sql_runner --file data.sql --config config.json

# Verbose output
python -m splurge_sql_runner --file schema.sql --database-url "sqlite:///app.db" --verbose

# Set max statements
python -m splurge_sql_runner --file large.sql --database-url "sqlite:///app.db" --max-statements 500
```

### Exit Codes

- `0`: Success - all statements executed
- `1`: Failure - one or more statements failed
- `2`: Partial success - some statements succeeded, some failed
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
from splurge_sql_runner.exceptions import SplurgeSqlRunnerError

# Load configuration
config = load_config()

try:
    # Execute SQL files
    results = process_sql_files(
        ["schema.sql", "data.sql"],
        database_url=config["database_url"],
        security_level=config.get("security_level", "normal"),
        max_statements_per_file=config["max_statements_per_file"],
        stop_on_error=False  # Continue even if one fails
    )
    
    # Process results
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"{status} {result['statement'][:50]}")
        if result["error"]:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Rows: {result['row_count']}")
            
except SplurgeSqlRunnerError as e:
    print(f"Error: {e}")
    exit(1)
```

### Direct Database Operations

```python
from splurge_sql_runner import DatabaseClient
from splurge_sql_runner.exceptions import DatabaseError

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
    print(f"Inserted {results[0]['row_count']} rows")
    
    # Query data
    rows = client.execute_select("SELECT * FROM users WHERE name LIKE 'A%'")
    for row in rows:
        print(f"User: {row['name']}")
        
finally:
    client.close()
```

### Security-Aware Operations

```python
from splurge_sql_runner import process_sql
from splurge_sql_runner.exceptions import SecurityValidationError, SecurityUrlError

# Strict mode - only safe operations
try:
    results = process_sql(
        "SELECT COUNT(*) FROM audit_log;",
        database_url="postgresql://readonly@prod.example.com/analytics",
        security_level="strict",
        max_statements_per_file=10
    )
except SecurityValidationError as e:
    print(f"SQL blocked by security policy: {e}")
except SecurityUrlError as e:
    print(f"Database URL rejected: {e}")
```

### Error Handling

```python
from splurge_sql_runner import process_sql_files
from splurge_sql_runner.exceptions import (
    SplurgeSqlRunnerError,
    SecurityFileError,
    DatabaseConnectionError,
    SqlExecutionError
)

try:
    results = process_sql_files(
        ["schema.sql"],
        database_url="postgresql://localhost/db"
    )
except SecurityFileError as e:
    print(f"File security check failed: {e.details}")
except DatabaseConnectionError as e:
    print(f"Cannot connect to database: {e}")
except SqlExecutionError as e:
    print(f"SQL execution failed: {e}")
except SplurgeSqlRunnerError as e:
    print(f"Unexpected error: {e}")
```

---

## Version Information

- **Current Version**: 2025.6.0
- **Python Support**: 3.10+
- **License**: MIT

See [CHANGELOG.md](../../CHANGELOG.md) for version history.

---

## Additional Resources

- [README](../../README.md) - Project overview and quick start
- [CONTRIBUTING](../../docs/CONTRIBUTING.md) - Development guidelines
- [CLI Examples](../../examples/cli_examples.md) - Command-line usage examples
- [Architecture Decision Records](../../docs/ADR.md) - Design decisions
