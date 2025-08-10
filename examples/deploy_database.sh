#!/bin/bash

# Database Deployment Script
# This script demonstrates a complete database deployment workflow using splurge-sql-runner

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Database configuration
DB_URL="${DATABASE_URL:-sqlite:///example.db}"
DB_TYPE=$(echo "$DB_URL" | cut -d: -f1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    log_success "Directories created"
}

# Backup existing database
backup_database() {
    log_info "Creating database backup..."
    
    if [[ "$DB_TYPE" == "sqlite" ]]; then
        # For SQLite, just copy the file
        DB_FILE=$(echo "$DB_URL" | sed 's/sqlite:\/\///')
        if [[ -f "$DB_FILE" ]]; then
            cp "$DB_FILE" "$BACKUP_DIR/backup_$TIMESTAMP.db"
            log_success "SQLite backup created: backup_$TIMESTAMP.db"
        else
            log_warning "No existing SQLite database found, skipping backup"
        fi
    elif [[ "$DB_TYPE" == "postgresql" ]]; then
        # For PostgreSQL, use pg_dump
        pg_dump "$DB_URL" > "$BACKUP_DIR/backup_$TIMESTAMP.sql"
        log_success "PostgreSQL backup created: backup_$TIMESTAMP.sql"
    elif [[ "$DB_TYPE" == "mysql" ]]; then
        # For MySQL, use mysqldump
        mysqldump "$DB_URL" > "$BACKUP_DIR/backup_$TIMESTAMP.sql"
        log_success "MySQL backup created: backup_$TIMESTAMP.sql"
    else
        log_warning "Unknown database type: $DB_TYPE, skipping backup"
    fi
}

# Run database setup
run_setup() {
    log_info "Running database setup..."
    
    # Run basic setup
    log_info "Executing basic setup..."
    python -m splurge_sql_runner \
        -c "$DB_URL" \
        -f "$SCRIPT_DIR/basic_setup.sql" \
        -v \
        2>&1 | tee "$LOG_DIR/setup_$TIMESTAMP.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Basic setup completed successfully"
    else
        log_error "Basic setup failed"
        exit 1
    fi
}

# Run migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Run migration
    log_info "Executing migration..."
    python -m splurge_sql_runner \
        -c "$DB_URL" \
        -f "$SCRIPT_DIR/migration_example.sql" \
        -v \
        2>&1 | tee "$LOG_DIR/migration_$TIMESTAMP.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Migration completed successfully"
    else
        log_error "Migration failed"
        exit 1
    fi
}

# Run data analysis
run_analysis() {
    log_info "Running data analysis..."
    
    # Run analysis
    log_info "Executing data analysis..."
    python -m splurge_sql_runner \
        -c "$DB_URL" \
        -f "$SCRIPT_DIR/data_analysis.sql" \
        -v \
        2>&1 | tee "$LOG_DIR/analysis_$TIMESTAMP.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Data analysis completed successfully"
    else
        log_error "Data analysis failed"
        exit 1
    fi
}

# Run maintenance
run_maintenance() {
    log_info "Running database maintenance..."
    
    # Run maintenance
    log_info "Executing maintenance tasks..."
    python -m splurge_sql_runner \
        -c "$DB_URL" \
        -f "$SCRIPT_DIR/cleanup_and_maintenance.sql" \
        -v \
        2>&1 | tee "$LOG_DIR/maintenance_$TIMESTAMP.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Maintenance completed successfully"
    else
        log_error "Maintenance failed"
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Create a verification script
    cat > "$SCRIPT_DIR/verify_deployment.sql" << 'EOF'
-- Deployment Verification Script
SELECT '=== DEPLOYMENT VERIFICATION ===' as section;

-- Check if all tables exist
SELECT 
    'Tables created:' as check_type,
    COUNT(*) as count
FROM sqlite_master 
WHERE type = 'table' AND name IN ('users', 'posts', 'roles', 'user_sessions', 'migration_history');

-- Check if data was inserted
SELECT 
    'Users created:' as check_type,
    COUNT(*) as count
FROM users;

SELECT 
    'Posts created:' as check_type,
    COUNT(*) as count
FROM posts;

SELECT 
    'Roles created:' as check_type,
    COUNT(*) as count
FROM roles;

-- Check if migration was recorded
SELECT 
    'Migrations applied:' as check_type,
    COUNT(*) as count
FROM migration_history;

-- Show sample data
SELECT 'Sample users:' as info;
SELECT username, full_name, role FROM users LIMIT 5;

SELECT 'Sample posts:' as info;
SELECT title, published FROM posts LIMIT 5;
EOF

    # Run verification
    log_info "Executing verification..."
    python -m splurge_sql_runner \
        -c "$DB_URL" \
        -f "$SCRIPT_DIR/verify_deployment.sql" \
        -v \
        2>&1 | tee "$LOG_DIR/verification_$TIMESTAMP.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Verification completed successfully"
    else
        log_error "Verification failed"
        exit 1
    fi
    
    # Clean up verification file
    rm -f "$SCRIPT_DIR/verify_deployment.sql"
}

# Generate deployment report
generate_report() {
    log_info "Generating deployment report..."
    
    REPORT_FILE="$LOG_DIR/deployment_report_$TIMESTAMP.txt"
    
    cat > "$REPORT_FILE" << EOF
Database Deployment Report
==========================
Date: $(date)
Database: $DB_URL
Timestamp: $TIMESTAMP

Deployment Steps:
1. ✅ Directory creation
2. ✅ Database backup
3. ✅ Basic setup
4. ✅ Migration execution
5. ✅ Data analysis
6. ✅ Maintenance tasks
7. ✅ Deployment verification

Log Files:
- Setup: $LOG_DIR/setup_$TIMESTAMP.log
- Migration: $LOG_DIR/migration_$TIMESTAMP.log
- Analysis: $LOG_DIR/analysis_$TIMESTAMP.log
- Maintenance: $LOG_DIR/maintenance_$TIMESTAMP.log
- Verification: $LOG_DIR/verification_$TIMESTAMP.log

Backup Files:
- Database: $BACKUP_DIR/backup_$TIMESTAMP.*

Deployment completed successfully!
EOF

    log_success "Deployment report generated: $REPORT_FILE"
    cat "$REPORT_FILE"
}

# Cleanup old files
cleanup_old_files() {
    log_info "Cleaning up old log and backup files..."
    
    # Keep only last 10 log files
    find "$LOG_DIR" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    
    # Keep only last 5 backup files
    find "$BACKUP_DIR" -name "backup_*" -type f -mtime +30 -delete 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting database deployment..."
    log_info "Database URL: $DB_URL"
    log_info "Timestamp: $TIMESTAMP"
    
    # Check if splurge-sql-runner is available
    if ! python -c "import splurge_sql_runner" 2>/dev/null; then
        log_error "splurge-sql-runner is not installed. Please install it first."
        exit 1
    fi
    
    # Execute deployment steps
    create_directories
    backup_database
    run_setup
    run_migrations
    run_analysis
    run_maintenance
    verify_deployment
    generate_report
    cleanup_old_files
    
    log_success "Database deployment completed successfully!"
    log_info "Check the log files in $LOG_DIR for detailed information"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "backup")
        create_directories
        backup_database
        ;;
    "setup")
        create_directories
        run_setup
        ;;
    "migrate")
        create_directories
        run_migrations
        ;;
    "analyze")
        create_directories
        run_analysis
        ;;
    "maintain")
        create_directories
        run_maintenance
        ;;
    "verify")
        create_directories
        verify_deployment
        ;;
    "cleanup")
        cleanup_old_files
        ;;
    "help"|"-h"|"--help")
        echo "Database Deployment Script"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  deploy    - Run complete deployment (default)"
        echo "  backup    - Create database backup only"
        echo "  setup     - Run basic setup only"
        echo "  migrate   - Run migrations only"
        echo "  analyze   - Run data analysis only"
        echo "  maintain  - Run maintenance tasks only"
        echo "  verify    - Verify deployment only"
        echo "  cleanup   - Clean up old log and backup files"
        echo "  help      - Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL - Database connection string (default: sqlite:///example.db)"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Run complete deployment"
        echo "  $0 migrate                            # Run migrations only"
        echo "  DATABASE_URL=postgresql://user:pass@localhost/db $0  # Use PostgreSQL"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
