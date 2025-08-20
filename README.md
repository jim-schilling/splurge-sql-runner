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

# Run linting
flake8 splurge_sql_runner/
black splurge_sql_runner/
mypy splurge_sql_runner/
```

## Changelog

### 2025.3.1 (08-20-2025)

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

