# CLI Reference Guide

## Overview

`splurge-sql-runner` is a command-line utility for executing SQL files against databases. It provides a clean interface for running SQL scripts with comprehensive error handling, security validation, and formatted output.

### Migration note

In a recent release the CLI entrypoint behavior was made easier to test and integrate: the `main()` function
now returns an integer exit code instead of calling `sys.exit()` directly. The package's script wrapper still
calls `sys.exit(main())` when run as a program, so the process exit code is unchanged for end users. API
consumers and tests can import the exit-code constants from `splurge_sql_runner.cli`:

```py
from splurge_sql_runner import cli

cli.EXIT_CODE_SUCCESS  # 0
cli.EXIT_CODE_FAILURE  # 1
cli.EXIT_CODE_PARTIAL_SUCCESS  # 2
cli.EXIT_CODE_UNKNOWN  # 3
```

This change makes it easier to call `main()` directly in code and assert on return values without intercepting
`SystemExit`.

## Usage

```bash
splurge-sql-runner [OPTIONS] --connection DATABASE_URL (--file FILE | --pattern PATTERN)
```

## Command Line Options

### Required Arguments

#### `--connection, -c DATABASE_URL`
**Required.** Database connection string specifying the database to connect to.

**Examples:**
- `sqlite:///database.db` - SQLite database file
- `sqlite:///:memory:` - In-memory SQLite database
- `postgresql://user:password@localhost:5432/database` - PostgreSQL
- `mysql://user:password@localhost/database` - MySQL
- `oracle://user:password@host:1521/service` - Oracle

### File Selection (Choose One)

#### `--file, -f FILE`
Execute a single SQL file.

**Example:**
```bash
splurge-sql-runner -c "sqlite:///db.sqlite" -f "setup.sql"
```

#### `--pattern, -p PATTERN`
Execute multiple SQL files matching a glob pattern.

**Examples:**
```bash
# All SQL files in current directory
splurge-sql-runner -c "sqlite:///db.sqlite" -p "*.sql"

# Specific pattern
splurge-sql-runner -c "sqlite:///db.sqlite" -p "migrations/*.sql"

# Recursive search
splurge-sql-runner -c "sqlite:///db.sqlite" -p "**/*.sql"
```

### Configuration Options

#### `--config CONFIG_FILE`
Path to a JSON configuration file containing default settings.

**Example:**
```bash
splurge-sql-runner --config config.json -c "sqlite:///db.sqlite" -f "script.sql"
```

**Config file format:**
```json
{
  "database_url": "sqlite:///database.db",
  "max_statements_per_file": 100,
  "connection_timeout": 30.0,
  "log_level": "INFO",
  "security_level": "normal",
  "enable_verbose": false,
  "enable_debug": false
}
```

### Security Options

#### `--security-level {strict,normal,permissive}`
Security validation level for SQL content and database URLs.

**Levels:**
- `strict` - Maximum security validation, blocks potentially dangerous patterns
- `normal` - Balanced security (default)
- `permissive` - Minimal validation, allows more patterns

**Examples:**
```bash
# Strict security (blocks DROP, dangerous URLs)
splurge-sql-runner --security-level strict -c "sqlite:///db.sqlite" -f "script.sql"

# Normal security (recommended for most use cases)
splurge-sql-runner --security-level normal -c "sqlite:///db.sqlite" -f "script.sql"

# Permissive (minimal validation)
splurge-sql-runner --security-level permissive -c "sqlite:///db.sqlite" -f "script.sql"
```

### Output Options

#### `--verbose, -v`
Enable verbose output showing detailed progress information.

**Example:**
```bash
splurge-sql-runner -c "sqlite:///db.sqlite" -f "script.sql" -v
```

**Verbose output includes:**
- File processing progress
- Statement execution details
- Row counts for SELECT statements
- Processing summary

#### `--json`
Output results in JSON format instead of human-readable tables.

**Example:**
```bash
splurge-sql-runner -c "sqlite:///db.sqlite" -f "script.sql" --json
```

**JSON output format:**
```json
[
  {
    "statement": "SELECT * FROM users",
    "statement_type": "fetch",
    "result": [
      {"id": 1, "name": "Alice"},
      {"id": 2, "name": "Bob"}
    ],
    "row_count": 2
  }
]
```

#### `--debug`
Enable SQLAlchemy debug logging for detailed database interaction information.

**Example:**
```bash
splurge-sql-runner -c "sqlite:///db.sqlite" -f "script.sql" --debug
```

### Execution Control

#### `--max-statements MAX`
Maximum number of SQL statements allowed per file (default: 100).

**Example:**
```bash
# Allow up to 500 statements per file
splurge-sql-runner -c "sqlite:///db.sqlite" -f "large_script.sql" --max-statements 500
```

#### `--continue-on-error`
Continue processing remaining statements when an error occurs, instead of stopping. This flag maps to the
`stop_on_error` parameter passed to the underlying API; when present, the CLI will attempt to run all statements
in each file and include statement-level errors in the per-file results.

**Example:**
```bash
# Process all files even if some statements fail
splurge-sql-runner -c "sqlite:///db.sqlite" -p "*.sql" --continue-on-error
```

## Exit Codes

The CLI `main()` function now returns structured exit codes (the module also exposes
constants for programmatic use). The executable script wrapper calls `sys.exit(main())`
so these codes are propagated to the process exit status when you run the tool.

- `0` - Success: All files/statements executed without any statement-level errors
- `1` - Failure: One or more files had only statement-level errors or a fatal error occurred
- `2` - Partial success: At least one file had mixed results (some statements succeeded and some failed)
- `3` - Unknown/internal error: Unexpected error that the CLI could not classify

Note: tests and API consumers should import the constants from `splurge_sql_runner.cli`:

```py
from splurge_sql_runner import cli

EXIT_OK = cli.EXIT_CODE_SUCCESS
EXIT_FAIL = cli.EXIT_CODE_FAILURE
EXIT_PARTIAL = cli.EXIT_CODE_PARTIAL_SUCCESS
EXIT_UNKNOWN = cli.EXIT_CODE_UNKNOWN
```

## Error Messages

### File Errors

#### `SQL file not found: PATH`
The specified SQL file does not exist or is not readable.

**Resolution:** Check the file path and permissions.

#### `Invalid file path: PATH`
The file path contains invalid characters or is malformed.

**Resolution:** Use a valid file path.

#### `Permission denied reading SQL file: PATH`
Cannot read the SQL file due to insufficient permissions.

**Resolution:** Check file permissions or run with appropriate user privileges.

#### `Decoding error reading SQL file (not UTF-8?): PATH`
The SQL file is not encoded in UTF-8 or contains invalid characters.

**Resolution:** Ensure the file is saved as UTF-8 encoded text.

### Database Errors

#### `Failed to create database engine: ERROR`
Cannot establish connection to the database.

**Resolution:** Check the database URL format and ensure the database server is running.

#### `Failed to connect to database: ERROR`
Connection to database failed.

**Resolution:** Verify database credentials, network connectivity, and server status.

### Security Errors

#### `SQL content security validation failed: ERROR`
SQL content contains patterns blocked by the current security level.

**Resolution:** Review the SQL content for dangerous patterns, or use `--security-level permissive`.

#### `Database URL contains dangerous pattern: PATTERN`
Database URL contains potentially unsafe patterns.

**Resolution:** Use a safe database URL format or adjust security level.

### Validation Errors

#### `file_path cannot be None`
No file or pattern was specified.

**Resolution:** Use `-f FILE` or `-p PATTERN`.

#### `Maximum statements per file exceeded: N > LIMIT`
SQL file contains more statements than the configured limit.

**Resolution:** Increase `--max-statements` limit or split the file.

## Examples

### Basic Single File Execution
```bash
splurge-sql-runner -c "sqlite:///database.db" -f "setup.sql"
```

### Multiple Files with Pattern
```bash
splurge-sql-runner -c "postgresql://user:pass@localhost/db" -p "migrations/*.sql"
```

### Verbose Output
```bash
splurge-sql-runner -c "sqlite:///database.db" -f "script.sql" -v
```

### JSON Output for Scripting
```bash
splurge-sql-runner -c "sqlite:///database.db" -f "query.sql" --json > results.json
```

### Error Recovery
```bash
splurge-sql-runner -c "sqlite:///database.db" -p "*.sql" --continue-on-error
```

### Strict Security
```bash
splurge-sql-runner --security-level strict -c "sqlite:///database.db" -f "script.sql"
```

### Configuration File
```bash
splurge-sql-runner --config production.json -c "postgresql://..." -p "scripts/*.sql"
```

## Environment Variables

Configuration can also be set via environment variables (overridden by CLI options):

- `SPLURGE_SQL_RUNNER_DB_URL` - Database URL
- `SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE` - Max statements per file
- `SPLURGE_SQL_RUNNER_CONNECTION_TIMEOUT` - Connection timeout in seconds
- `SPLURGE_SQL_RUNNER_LOG_LEVEL` - Logging level
- `SPLURGE_SQL_RUNNER_VERBOSE` - Enable verbose output (true/1/yes/on)
- `SPLURGE_SQL_RUNNER_DEBUG` - Enable debug mode (true/1/yes/on)

## File Format Support

### SQL Files
- **Encoding:** UTF-8 required
- **Statements:** Separated by semicolons (`;`)
- **Comments:**
  - Single line: `-- comment`
  - Multi-line: `/* comment */`
- **Newlines:** Automatic normalization to `\n`

### Supported SQL Features
- Standard DDL: `CREATE`, `ALTER`, `DROP`
- DML: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
- Transactions: `BEGIN`, `COMMIT`, `ROLLBACK`
- Complex queries with joins, subqueries, etc.

## Performance Considerations

- **File Size:** Large files are processed in memory
- **Connection Pooling:** Enabled for non-SQLite databases
- **Statement Limits:** Default 100 statements per file (configurable)
- **Batch Processing:** Multiple files processed sequentially

## Troubleshooting

### Common Issues

1. **"No files found matching pattern"**
   - Check glob pattern syntax
   - Verify files exist in the specified directory
   - Use absolute paths if needed

2. **"Maximum statements per file exceeded"**
   - Split large SQL files
   - Increase `--max-statements` limit

3. **"SQL content security validation failed"**
   - Review SQL for blocked keywords (DROP, etc.)
   - Use `--security-level permissive` for trusted scripts

4. **Connection timeouts**
   - Increase connection timeout in config
   - Check network connectivity
   - Verify database server is running
