# Splurge SQL Runner - Detailed Documentation

## Overview

Splurge SQL Runner is a robust, secure, and user-friendly Python utility for executing SQL files against databases. It provides comprehensive support for multiple database backends, advanced security validation, and flexible output formatting.

## Key Features

### 🔧 Core Functionality
- **Multi-Statement Execution**: Process SQL files containing multiple statements
- **Database Agnostic**: Support for SQLite, PostgreSQL, MySQL, Oracle, and more
- **Smart Parsing**: Automatic statement splitting and comment removal
- **Transaction Management**: Proper transaction handling with rollback on errors
- **Batch Processing**: Execute multiple files with glob patterns

### 🔒 Security Features
- **SQL Content Validation**: Detects and blocks dangerous SQL patterns
- **Database URL Validation**: Prevents connection to suspicious database URLs
- **File Path Security**: Validates file paths for directory traversal attempts
- **Configurable Security Levels**: `strict`, `normal`, `permissive` modes
- **Safe File Reading**: Uses secure file I/O with path validation

### 📊 Output & Formatting
- **Pretty Tables**: Human-readable tabulated output for SELECT results
- **JSON Output**: Machine-readable format for scripting and automation
- **Verbose Logging**: Detailed execution progress and diagnostics
- **Error Reporting**: Comprehensive error messages with suggestions

### ⚙️ Configuration Management
- **JSON Configuration Files**: External configuration for complex setups
- **Environment Variables**: Runtime configuration via environment
- **CLI Arguments**: Command-line overrides for all settings
- **Default Values**: Sensible defaults for quick start

### 🛠️ Developer Experience
- **Type Safety**: Full mypy type checking
- **Comprehensive Testing**: 500+ tests covering all functionality, including extensive end-to-end tests with real databases
- **Clean Architecture**: Modular design with clear separation of concerns
- **Error Handling**: Robust error recovery and informative messages with simplified exception hierarchy

## Quick Start Guide

### Installation

```bash
pip install splurge-sql-runner
```

### Basic Usage

```bash
# Execute a single SQL file
splurge-sql-runner -c "sqlite:///database.db" -f "setup.sql"

# Execute multiple files with a pattern
splurge-sql-runner -c "sqlite:///database.db" -p "*.sql"

# Verbose output
splurge-sql-runner -c "sqlite:///database.db" -f "script.sql" -v
```

## CLI Options Summary

### Essential Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--connection` | `-c` | **Required.** Database connection string | `sqlite:///db.sqlite` |
| `--file` | `-f` | Single SQL file to execute | `setup.sql` |
| `--pattern` | `-p` | Glob pattern for multiple files | `*.sql` |

### Configuration Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--config` | JSON configuration file | None | `config.json` |
| `--security-level` | Security validation level | `normal` | `strict` |
| `--max-statements` | Max statements per file | `100` | `500` |
| `--continue-on-error` | Continue on statement errors | `false` | (flag) |

### Output Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--verbose` | `-v` | Enable verbose output | (flag) |
| `--json` | | JSON output format | (flag) |
| `--debug` | | Enable debug logging | (flag) |

### Complete Examples

#### SQLite Database
```bash
# Create and populate a database
splurge-sql-runner -c "sqlite:///example.db" -f "schema.sql"
splurge-sql-runner -c "sqlite:///example.db" -f "data.sql"

# Query with results
splurge-sql-runner -c "sqlite:///example.db" -f "queries.sql" -v
```

#### PostgreSQL Database
```bash
# With connection details
splurge-sql-runner -c "postgresql://user:password@localhost:5432/database" -p "migrations/*.sql"

# Using environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/database"
splurge-sql-runner -c "$DATABASE_URL" -f "script.sql"
```

#### MySQL Database
```bash
splurge-sql-runner -c "mysql://user:password@localhost/database" -f "setup.sql" -v
```

#### JSON Output for Automation
```bash
# Machine-readable output
splurge-sql-runner -c "sqlite:///db.sqlite" -f "query.sql" --json > results.json

# Process results in scripts
python -c "
import json
with open('results.json') as f:
    results = json.load(f)
    for result in results:
        print(f\"Rows affected: {result.get('row_count', 0)}\")
"
```

#### Configuration File Usage
```bash
# config.json
{
  "database_url": "sqlite:///production.db",
  "max_statements_per_file": 200,
  "connection_timeout": 60.0,
  "log_level": "WARNING",
  "security_level": "strict"
}

# Use configuration file
splurge-sql-runner --config config.json -f "script.sql"
```

#### Error Recovery
```bash
# Continue processing even if some statements fail
splurge-sql-runner -c "sqlite:///db.sqlite" -p "*.sql" --continue-on-error

# Check exit code in scripts
if splurge-sql-runner -c "sqlite:///db.sqlite" -f "script.sql"; then
    echo "All statements executed successfully"
else
    echo "Some statements failed"
fi
```

## Security Levels

### Strict Mode (`--security-level strict`)
- Blocks all potentially dangerous SQL patterns
- Validates file extensions (.sql only)
- Prevents directory traversal in file paths
- Maximum security for untrusted input

### Normal Mode (`--security-level normal`) - Default
- Balanced security validation
- Blocks common dangerous patterns
- Allows most legitimate SQL operations
- Recommended for most use cases

### Permissive Mode (`--security-level permissive`)
- Minimal security validation
- Allows all SQL patterns except obvious exploits
- For trusted scripts and development
- Not recommended for production

## File Format Specifications

### SQL File Requirements
- **Encoding**: UTF-8 (required)
- **Statements**: Separated by semicolons (`;`)
- **Comments**:
  - Single-line: `-- comment text`
  - Multi-line: `/* comment text */`
- **Empty Lines**: Automatically filtered out
- **Statement Limit**: 100 per file (configurable)

### Supported SQL Syntax
- **DDL**: `CREATE`, `ALTER`, `DROP`
- **DML**: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
- **DCL**: `GRANT`, `REVOKE`
- **TCL**: `BEGIN`, `COMMIT`, `ROLLBACK`
- **Complex Queries**: Joins, subqueries, CTEs, window functions

### Example SQL File
```sql
-- Create users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

/* Insert sample data */
INSERT INTO users (username, email) VALUES
    ('alice', 'alice@example.com'),
    ('bob', 'bob@example.com');

-- Query users
SELECT id, username, email, created_at
FROM users
WHERE created_at >= date('now', '-30 days')
ORDER BY created_at DESC;
```

## Configuration Options

### JSON Configuration File Format
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

### Environment Variables
- `SPLURGE_SQL_RUNNER_DB_URL`: Database connection string
- `SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE`: Max statements per file
- `SPLURGE_SQL_RUNNER_CONNECTION_TIMEOUT`: Connection timeout (seconds)
- `SPLURGE_SQL_RUNNER_LOG_LEVEL`: Logging level
- `SPLURGE_SQL_RUNNER_VERBOSE`: Enable verbose output (true/1/yes/on)
- `SPLURGE_SQL_RUNNER_DEBUG`: Enable debug mode (true/1/yes/on)

### Precedence Order
1. CLI arguments (highest priority)
2. Environment variables
3. JSON configuration file
4. Built-in defaults (lowest priority)

## Error Handling

All errors inherit from `SplurgeSqlRunnerError` which provides structured error information with context details. The exception hierarchy was simplified in version 2025.7.0 for easier error handling.

### Exception Types

- **`SplurgeSqlRunnerFileError`**: File I/O operations, reading files, file validation
- **`SplurgeSqlRunnerDatabaseError`**: Database connection and operation failures
- **`SplurgeSqlRunnerSecurityError`**: Security validation failures (SQL content, URLs, paths)
- **`SplurgeSqlRunnerValueError`**: Invalid configuration values, validation errors
- **`SplurgeSqlRunnerConfigurationError`**: Configuration loading and parsing errors
- **`SplurgeSqlRunnerOSError`**: Operating system level errors
- **`SplurgeSqlRunnerRuntimeError`**: Runtime errors and unexpected conditions

### Common Errors and Solutions

#### File Errors (`SplurgeSqlRunnerFileError`)
- **"File not found"**: Check file path and permissions
- **"Permission denied reading [file type]"**: Ensure read access to file
- **"Invalid encoding in file"**: Save file as UTF-8 encoding

#### Database Errors (`SplurgeSqlRunnerDatabaseError`)
- **"Failed to create database engine"**: Check database URL format
- **"Failed to connect to database"**: Verify credentials and connectivity

#### Security Errors (`SplurgeSqlRunnerSecurityError`)
- **"SQL content security validation failed"**: Remove dangerous patterns or use permissive mode
- **"Database URL contains dangerous pattern"**: Use safe URL format

#### Validation Errors (`SplurgeSqlRunnerValueError`)
- **"Maximum statements per file exceeded"**: Split large files or increase limit
- **"No files found matching pattern"**: Check glob pattern and file locations
- **Configuration validation errors**: Check configuration values for required format

## Advanced Usage

### Scripting and Automation
```bash
#!/bin/bash
# Automated database setup script

DB_URL="sqlite:///production.db"
SCRIPTS_DIR="sql/migrations"

# Run all migration scripts
if splurge-sql-runner -c "$DB_URL" -p "$SCRIPTS_DIR/*.sql" -v; then
    echo "✅ Database migrations completed successfully"
    exit 0
else
    echo "❌ Database migrations failed"
    exit 1
fi
```

### Docker Integration
```dockerfile
FROM python:3.11-slim

RUN pip install splurge-sql-runner

COPY sql/ /sql/
COPY config.json /config.json

CMD ["splurge-sql-runner", "--config", "/config.json", "-p", "/sql/*.sql"]
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Run Database Migrations
  run: |
    splurge-sql-runner \
      -c "postgresql://user:pass@localhost:5432/db" \
      -p "migrations/*.sql" \
      --continue-on-error \
      -v
```

## Performance Considerations

### Memory Usage
- SQL files loaded entirely into memory
- Large result sets consume memory
- Consider file size limits for production use

### Connection Management
- SQLite: File-based locking, no connection pooling
- Other databases: Connection pooling enabled
- Long-running processes: Monitor connection limits

### Optimization Tips
- Use appropriate `--max-statements` limits
- Split large SQL files when possible
- Use `--continue-on-error` for batch processing
- Consider `--json` output for large result sets

## Development and Testing

### Running Tests
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=splurge_sql_runner

# Run specific test categories
pytest -m "critical"  # Critical path tests
pytest -m "fast"      # Fast tests only
```

### Type Checking
```bash
# Run mypy type checking
mypy splurge_sql_runner

# Check all files
mypy .
```

### Code Quality
```bash
# Run linting
flake8 splurge_sql_runner

# Format code
black splurge_sql_runner
isort splurge_sql_runner
```

## Architecture Overview

### Core Components
- **CLI Module**: Command-line interface and argument parsing
- **Database Client**: SQLAlchemy-based database abstraction
- **SQL Helper**: SQL parsing and statement processing
- **Security Module**: Validation and security checks
- **Configuration**: Settings management and loading
- **Result Models**: Typed data structures for results

### Design Principles
- **Security First**: All input validated and sanitized
- **Error Recovery**: Graceful handling of failures
- **Modular Design**: Clear separation of concerns
- **Type Safety**: Comprehensive type hints
- **Test Coverage**: High test coverage for reliability

## Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-org/splurge-sql-runner.git
cd splurge-sql-runner

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Code Standards
- **Type Hints**: All functions use proper type annotations
- **Docstrings**: Comprehensive documentation for all public APIs
- **Tests**: Unit tests for all functionality
- **Linting**: Code formatted with black and isort

## Links

- [CLI Reference](CLI-REFERENCE.md) - Detailed command-line options
- [Changelog](CHANGELOG.md) - Version history and release notes
- [API Reference](API-REFERENCE.md) - Programmatic usage documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions:
- GitHub Issues: Report bugs and request features
- GitHub Discussions: Ask questions and get help
- Pull Requests: Contribute improvements and fixes

---

*Last updated: November 1, 2025*
