# splurge-sql-runner
Splurge Python SQL Runner

A Python utility for executing SQL files against databases with support for multiple statements, comments, and pretty-printed results.

## Features

- Execute SQL files with multiple statements
- Support for various database backends (SQLite, PostgreSQL, MySQL, etc.)
- Automatic comment removal and statement parsing
- Pretty-printed results with tabulated output
- Batch processing of multiple files
- Transaction support with rollback on errors
- Clean CLI interface with comprehensive error handling
- Security validation for database URLs and file operations
- Comprehensive error handling with circuit breaker patterns
- Configuration management with JSON-based config files
- Advanced logging with multiple output formats
- Resilience patterns for production deployments

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
```

### Command Line Options

- `-c, --connection`: Database connection string (required)
  - SQLite: `sqlite:///database.db`
  - PostgreSQL: `postgresql://user:pass@localhost/db`
  - MySQL: `mysql://user:pass@localhost/db`
  
- `-f, --file`: Single SQL file to execute
  
- `-p, --pattern`: File pattern to match multiple SQL files (e.g., "*.sql")
  
- `-v, --verbose`: Enable verbose output
  
- `--debug`: Enable SQLAlchemy debug mode

- `--disable-security`: Disable security validation (not recommended for production)

- `--max-file-size`: Maximum file size in MB (default: 10)

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

# With security validation disabled (not recommended)
python -m splurge_sql_runner -c "sqlite:///database.db" -f "script.sql" --disable-security
```

## Programmatic Usage

### Basic Usage

```python
from splurge_sql_runner.database.engines import UnifiedDatabaseEngine
from splurge_sql_runner.config.security_config import SecurityConfig

# Initialize the database engine
engine = UnifiedDatabaseEngine("sqlite:///database.db")

# Create security configuration
security_config = SecurityConfig(
    max_file_size_mb=10,
    max_statements_per_file=100
)

# Execute SQL with security validation
try:
    results = engine.execute_file("script.sql", security_config)
    for result in results:
        print(f"Statement executed: {result.success}")
except Exception as e:
    print(f"Execution failed: {e}")

engine.shutdown()
```

### Advanced Usage with New Architecture

```python
from splurge_sql_runner.config import ConfigManager, AppConfig
from splurge_sql_runner.database import SqlRepository, DatabaseEngineFactory
from splurge_sql_runner.errors import ErrorHandler, CircuitBreakerConfig

# Load configuration
config_manager = ConfigManager("config.json")
config = config_manager.load_config()

# Create database repository with error handling
error_handler = ErrorHandler(
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60
    )
)

repository = SqlRepository(
    engine_factory=DatabaseEngineFactory(),
    error_handler=error_handler
)

# Execute SQL with resilience
try:
    results = repository.execute_batch("script.sql", config)
    for result in results:
        print(f"Statement executed: {result.success}")
except Exception as e:
    print(f"Execution failed: {e}")
```



## Configuration

The library supports JSON-based configuration files for advanced usage:

```json
{
    "database": {
        "url": "sqlite:///database.db",
        "type": "sqlite",
        "connection": {
            "timeout": 30,
            "max_connections": 5
        },
        "pool": {
            "size": 5,
            "max_overflow": 0,
            "recycle_time": 3600
        }
    },
    "security": {
        "enable_validation": true,
        "max_file_size_mb": 10,
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
- Circuit breaker patterns for handling repeated failures
- Retry strategies with exponential backoff
- Comprehensive error context and recovery mechanisms
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

### 2025.2.0 (08-10-2025)

- **Breaking Changes**: `DbEngine` class has been removed entirely
- **New**: `UnifiedDatabaseEngine` is the only database engine for programmatic usage
- **New**: Centralized configuration constants in `splurge_sql_runner.config.constants`
- **Improved**: Security validation now uses centralized `SecurityConfig` from `splurge_sql_runner.config.security_config`
- **Code Quality**: Eliminated code duplication across the codebase

### Initial Commit
