# jpy-sql-runner
Jim's Python SQL Runner

A Python utility for executing SQL files against databases with support for multiple statements, comments, and pretty-printed results.

## Features

- Execute SQL files with multiple statements
- Support for various database backends (SQLite, PostgreSQL, MySQL, etc.)
- Automatic comment removal and statement parsing
- Pretty-printed results with tabulated output
- Batch processing of multiple files
- Transaction support with rollback on errors
- Clean CLI interface with comprehensive error handling

## Installation

```bash
pip install jpy-sql-runner
```

## CLI Usage

The main interface is through the command-line tool:

### Basic Usage

```bash
# Execute a single SQL file
python -m jpy_sql_runner -c "sqlite:///database.db" -f "script.sql"

# Execute multiple SQL files using a pattern
python -m jpy_sql_runner -c "sqlite:///database.db" -p "*.sql"

# With verbose output
python -m jpy_sql_runner -c "sqlite:///database.db" -f "script.sql" -v
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

### Examples

```bash
# SQLite example
python -m jpy_sql_runner -c "sqlite:///test.db" -f "setup.sql"

# PostgreSQL example
python -m jpy_sql_runner -c "postgresql://user:pass@localhost/mydb" -p "migrations/*.sql"

# MySQL example with verbose output
python -m jpy_sql_runner -c "mysql://user:pass@localhost/mydb" -f "data.sql" -v

# Process all SQL files in current directory
python -m jpy_sql_runner -c "sqlite:///database.db" -p "*.sql"
```

## Programmatic Usage

```python
from jpy_sql_runner.db_helper import DbEngine
from jpy_sql_runner.sql_helper import split_sql_file

# Initialize database engine
db = DbEngine("sqlite:///database.db")

# Execute SQL from file
sql_statements = split_sql_file("script.sql")
sql_content = ";\n".join(sql_statements) + ";"
results = db.batch(sql_content)

# Process results
for result in results:
    if result['type'] == 'fetch':
        print(f"Query returned {result['row_count']} rows")
    elif result['type'] == 'execute':
        print("Statement executed successfully")
    elif result['type'] == 'error':
        print(f"Error: {result['error']}")

db.shutdown()
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

## License

MIT License - see LICENSE file for details.

## Changelog

### 0.1.3 (06-29-2025)
- **Major CLI Refactoring**: Separated CLI logic into dedicated `cli.py` module for better code organization
- **Improved Architecture**: Made `__main__.py` a simple stub that delegates to the CLI module
- **Enhanced Test Coverage**: Added comprehensive tests for CLI functionality, achieving 90% overall coverage
- **Better Error Handling**: Improved CLI error messages and validation
- **Code Quality**: Fixed deprecation warnings in `pyproject.toml` license format
- **Documentation**: Updated README with improved installation instructions and CLI examples

### 0.1.2 (06-29-2025)
- Update sql_helper.py

### 0.1.1 (06-28-2025)
- Refactored `detect_statement_type` into smaller, modular helper functions for clarity and maintainability.
- Improved code readability and reduced duplication in SQL type detection logic.
- Added comprehensive tests for complex, nested, malformed, and database-specific SQL cases.
- Ensured robust handling of edge cases and advanced SQL features.
