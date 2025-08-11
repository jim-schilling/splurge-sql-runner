# splurge-sql-runner Examples

This directory contains comprehensive examples demonstrating the `splurge-sql-runner` CLI functionality.

## Quick Start

1. **Run the interactive demo:**
   ```bash
   PYTHONPATH=. python examples/demo.py
   ```

2. **Run the automated test suite:**
   ```bash
   PYTHONPATH=. python examples/test_cli.py
   ```

3. **Run the deployment script:**
   ```bash
   ./examples/deploy_database.sh
   ```

## Example Files

### SQL Files

- **`basic_setup.sql`** - Basic database schema setup with users and posts tables
- **`migration_example.sql`** - Database migration example adding new columns and tables
- **`data_analysis.sql`** - Complex data analysis queries and reporting
- **`cleanup_and_maintenance.sql`** - Database maintenance and cleanup operations
- **`example.sql`** - Simple example from the original project

### Scripts

- **`demo.py`** - Interactive step-by-step demonstration of CLI features
- **`test_cli.py`** - Automated test suite for all CLI functionality
- **`deploy_database.sh`** - Real-world deployment script with backup and error handling

### Documentation

- **`cli_examples.md`** - Comprehensive CLI usage examples and scenarios
- **`config.json`** - Example configuration file

## Database Types Supported

The examples demonstrate connections to various database types:

- **SQLite** (default for examples)
- **PostgreSQL**
- **MySQL**
- **Microsoft SQL Server**

## Features Demonstrated

- ✅ Basic SQL file execution
- ✅ File pattern matching (`*.sql`)
- ✅ Verbose output and debugging
- ✅ Security validation
- ✅ Error handling
- ✅ Database migrations
- ✅ Data analysis and reporting
- ✅ Maintenance operations
- ✅ Backup strategies
- ✅ CI/CD integration

## Usage Examples

### Basic Usage
```bash
# Single file execution
python -m splurge_sql_runner -c "sqlite:///test.db" -f examples/basic_setup.sql -v

# Pattern matching
python -m splurge_sql_runner -c "sqlite:///test.db" -p "examples/*.sql" -v
```

### Different Database Types
```bash
# PostgreSQL
python -m splurge_sql_runner -c "postgresql://user:pass@localhost/db" -f setup.sql

# MySQL
python -m splurge_sql_runner -c "mysql://user:pass@localhost/db" -f setup.sql

# SQL Server
python -m splurge_sql_runner -c "mssql+pyodbc://user:pass@server/db" -f setup.sql
```

### Security Features
```bash
# Default security validation
python -m splurge_sql_runner -c "sqlite:///test.db" -f setup.sql

# Disable security (not recommended for production)
python -m splurge_sql_runner -c "sqlite:///test.db" -f setup.sql --disable-security

# Custom limits
python -m splurge_sql_runner -c "sqlite:///test.db" -f setup.sql --max-file-size 5 --max-statements 50
```

## Next Steps

1. Review `cli_examples.md` for detailed usage scenarios
2. Try the examples with your own database
3. Customize the SQL files for your specific needs
4. Integrate into your CI/CD pipeline using the deployment script

## Troubleshooting

- **Import errors**: Make sure you're running from the project root with `PYTHONPATH=.`
- **Unicode errors**: The CLI now handles UTF-8 encoding automatically
- **Permission errors**: Make sure the deployment script is executable (`chmod +x examples/deploy_database.sh`)
- **Database connection issues**: Check your connection string format and credentials
