# splurge-sql-runner CLI Examples

This document provides comprehensive examples for using the splurge-sql-runner command-line interface.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Database Connection Examples](#database-connection-examples)
3. [File Processing Examples](#file-processing-examples)
4. [Security and Validation](#security-and-validation)
5. [Advanced Features](#advanced-features)
6. [Error Handling Examples](#error-handling-examples)
7. [Real-World Scenarios](#real-world-scenarios)

## Basic Usage

### Execute a Single SQL File

```bash
# Basic SQLite execution
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql"

# With verbose output
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql" -v

# Using absolute paths
python -m splurge_sql_runner -c "sqlite:///test.db" -f "/path/to/script.sql"
```

### Execute Multiple Files with Pattern Matching

```bash
# Execute all SQL files in current directory
python -m splurge_sql_runner -c "sqlite:///test.db" -p "*.sql"

# Execute files in specific directory
python -m splurge_sql_runner -c "sqlite:///test.db" -p "migrations/*.sql"

# Execute files with specific naming pattern
python -m splurge_sql_runner -c "sqlite:///test.db" -p "setup_*.sql"
```

## Database Connection Examples

### SQLite

```bash
# In-memory database
python -m splurge_sql_runner -c "sqlite:///:memory:" -f "test.sql"

# File-based database
python -m splurge_sql_runner -c "sqlite:///database.db" -f "setup.sql"

# Database in specific directory
python -m splurge_sql_runner -c "sqlite:////absolute/path/database.db" -f "setup.sql"
```

### PostgreSQL

```bash
# Basic connection
python -m splurge_sql_runner -c "postgresql://user:password@localhost/dbname" -f "migration.sql"

# With port specification
python -m splurge_sql_runner -c "postgresql://user:password@localhost:5432/dbname" -f "setup.sql"

# With SSL
python -m splurge_sql_runner -c "postgresql://user:password@localhost/dbname?sslmode=require" -f "setup.sql"

# With connection parameters
python -m splurge_sql_runner -c "postgresql://user:password@localhost/dbname?connect_timeout=10" -f "setup.sql"
```

### MySQL

```bash
# Basic connection
python -m splurge_sql_runner -c "mysql://user:password@localhost/dbname" -f "setup.sql"

# With port specification
python -m splurge_sql_runner -c "mysql://user:password@localhost:3306/dbname" -f "setup.sql"

# With charset specification
python -m splurge_sql_runner -c "mysql://user:password@localhost/dbname?charset=utf8mb4" -f "setup.sql"
```

### Microsoft SQL Server

```bash
# Basic connection
python -m splurge_sql_runner -c "mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+17+for+SQL+Server" -f "setup.sql"

# With Windows authentication
python -m splurge_sql_runner -c "mssql+pyodbc://server/database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes" -f "setup.sql"
```

## File Processing Examples

### Single File with Different Output Modes

```bash
# Silent execution (default)
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql"

# Verbose output
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql" -v

# Debug mode (SQLAlchemy debug)
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql" --debug

# Verbose + Debug
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql" -v --debug
```

### Batch Processing Multiple Files

```bash
# Process all SQL files in current directory
python -m splurge_sql_runner -c "sqlite:///test.db" -p "*.sql"

# Process files in subdirectories
python -m splurge_sql_runner -c "sqlite:///test.db" -p "**/*.sql"

# Process specific file types
python -m splurge_sql_runner -c "sqlite:///test.db" -p "migrations/*.sql"
python -m splurge_sql_runner -c "sqlite:///test.db" -p "data/*.sql"
python -m splurge_sql_runner -c "sqlite:///test.db" -p "views/*.sql"
```

## Security and Validation

### Security Validation (Default)

```bash
# Security validation enabled (default)
python -m splurge_sql_runner -c "sqlite:///test.db" -f "setup.sql"

# This will validate:
# - Database URL format and safety
# - File path security
# - SQL content for dangerous operations
```

### Disabling Security (Not Recommended)

```bash
# Disable security validation (use with caution)
Security validation cannot be disabled. Adjust `security` in config instead (e.g., increase `max_statements_per_file`).

# Warning: This bypasses all security checks
```

### Statement Limits

```bash
# Set custom statement limit (default: 100)
python -m splurge_sql_runner -c "sqlite:///test.db" -f "complex_script.sql" --max-statements 500
```

## Advanced Features

### Environment Variable Usage

```bash
# Use environment variables for sensitive data
export DB_URL="postgresql://user:password@localhost/dbname"
python -m splurge_sql_runner -c "$DB_URL" -f "setup.sql"

# Or inline
DB_URL="postgresql://user:password@localhost/dbname" python -m splurge_sql_runner -c "$DB_URL" -f "setup.sql"
```

### Integration with Shell Scripts

```bash
#!/bin/bash
# deploy.sh - Database deployment script

DB_URL="postgresql://user:password@localhost/production"
LOG_FILE="deployment.log"

echo "Starting database deployment..."

# Run migrations
python -m splurge_sql_runner -c "$DB_URL" -p "migrations/*.sql" -v 2>&1 | tee "$LOG_FILE"

# Check exit code
if [ $? -eq 0 ]; then
    echo "Deployment successful!"
else
    echo "Deployment failed! Check $LOG_FILE for details."
    exit 1
fi
```

### Continuous Integration Examples

```yaml
# .github/workflows/database.yml
name: Database Migration

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install splurge-sql-runner
        
    - name: Run migrations
      run: |
        python -m splurge_sql_runner \
          -c "${{ secrets.DATABASE_URL }}" \
          -p "migrations/*.sql" \
          -v
```

## Error Handling Examples

### Handling Connection Errors

```bash
# Invalid connection string
python -m splurge_sql_runner -c "invalid://connection" -f "setup.sql"
# Output: ❌ Database error: Invalid database URL format

# Non-existent database
python -m splurge_sql_runner -c "postgresql://user:pass@localhost/nonexistent" -f "setup.sql"
# Output: ❌ Database error: Connection failed
```

### Handling File Errors

```bash
# Non-existent file
python -m splurge_sql_runner -c "sqlite:///test.db" -f "nonexistent.sql"
# Output: ❌ CLI file error: File not found: nonexistent.sql

# No files matching pattern
python -m splurge_sql_runner -c "sqlite:///test.db" -p "nonexistent/*.sql"
# Output: ❌ CLI file error: No files found matching pattern: nonexistent/*.sql
```

### Handling SQL Errors

```bash
# Invalid SQL syntax
python -m splurge_sql_runner -c "sqlite:///test.db" -f "invalid_syntax.sql"
# Output: ❌ SQL file error: Invalid SQL syntax in statement 1
```

## Real-World Scenarios

### Database Migration Workflow

```bash
# 1. Create migration files
mkdir -p migrations
echo "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);" > migrations/001_create_users.sql
echo "INSERT INTO users (name) VALUES ('Admin');" > migrations/002_add_admin.sql

# 2. Run migrations
python -m splurge_sql_runner -c "postgresql://user:pass@localhost/mydb" -p "migrations/*.sql" -v

# 3. Verify migration
python -m splurge_sql_runner -c "postgresql://user:pass@localhost/mydb" -f "verify.sql"
```

### Data Import Workflow

```bash
# 1. Import reference data
python -m splurge_sql_runner -c "sqlite:///app.db" -f "reference_data.sql" -v

# 2. Import user data
python -m splurge_sql_runner -c "sqlite:///app.db" -f "user_data.sql" -v

# 3. Create indexes
python -m splurge_sql_runner -c "sqlite:///app.db" -f "create_indexes.sql" -v
```

### Testing Database Setup

```bash
# 1. Setup test database
python -m splurge_sql_runner -c "sqlite:///test.db" -f "test_setup.sql" -v

# 2. Run test data
python -m splurge_sql_runner -c "sqlite:///test.db" -f "test_data.sql" -v

# 3. Verify test data
python -m splurge_sql_runner -c "sqlite:///test.db" -f "test_verification.sql" -v
```

### Production Deployment

```bash
#!/bin/bash
# deploy_production.sh

set -e  # Exit on any error

DB_URL="postgresql://prod_user:prod_pass@prod-server/prod_db"
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting production deployment..."

# 1. Create backup
echo "Creating backup..."
pg_dump "$DB_URL" > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

# 2. Run migrations
echo "Running migrations..."
python -m splurge_sql_runner -c "$DB_URL" -p "migrations/*.sql" -v

# 3. Update reference data
echo "Updating reference data..."
python -m splurge_sql_runner -c "$DB_URL" -f "reference_data.sql" -v

# 4. Verify deployment
echo "Verifying deployment..."
python -m splurge_sql_runner -c "$DB_URL" -f "verify_deployment.sql" -v

echo "Production deployment completed successfully!"
```

## Troubleshooting

### Common Issues and Solutions

1. **Permission Denied**
   ```bash
   # Solution: Check file permissions
   chmod +r script.sql
   ```

2. **Database Connection Timeout**
   ```bash
   # Solution: Add timeout parameters
   python -m splurge_sql_runner -c "postgresql://user:pass@localhost/db?connect_timeout=30" -f "script.sql"
   ```

3. **Large File Processing**
   ```bash
   # Solution: Increase file size limit
   python -m splurge_sql_runner -c "sqlite:///test.db" -f "large_file.sql" --max-file-size 100
   ```

4. **Complex SQL with Many Statements**
   ```bash
   # Solution: Increase statement limit
   python -m splurge_sql_runner -c "sqlite:///test.db" -f "complex_script.sql" --max-statements 1000
   ```

### Debug Mode

```bash
# Enable debug mode for troubleshooting
python -m splurge_sql_runner -c "sqlite:///test.db" -f "script.sql" --debug -v

# This will show:
# - SQLAlchemy debug information
# - Detailed connection information
# - Statement execution details
# - Performance metrics
```

## Best Practices

1. **Always use security validation in production**
2. **Use environment variables for sensitive connection strings**
3. **Test scripts in development before production**
4. **Use verbose mode for debugging**
5. **Implement proper error handling in automation scripts**
6. **Keep SQL files organized in directories**
7. **Use meaningful file names and comments**
8. **Version control your SQL scripts**
9. **Backup databases before running migrations**
10. **Monitor execution logs for issues**
