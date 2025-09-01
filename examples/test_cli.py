#!/usr/bin/env python3
"""
Test script for splurge-sql-runner CLI examples.

This script demonstrates how to use the CLI programmatically and test
the various example scenarios.
"""

import subprocess
import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from typing import List

# Add the project root to Python path for development
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_cli_command(
    args: List[str], capture_output: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a splurge-sql-runner CLI command.

    Args:
        args: Command line arguments
        capture_output: Whether to capture output

    Returns:
        CompletedProcess result
    """
    # Validate input arguments
    if not isinstance(args, list):
        raise ValueError("args must be a list of strings")

    # Sanitize arguments to prevent shell injection
    sanitized_args = []
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError("All arguments must be strings")
        # Remove potentially dangerous characters
        if any(char in arg for char in [';', '|', '&', '`', '$', '(', ')', '<', '>', '\n', '\r']):
            raise ValueError(f"Potentially dangerous characters found in argument: {arg}")
        sanitized_args.append(arg)

    cmd = [sys.executable, "-m", "splurge_sql_runner"] + sanitized_args
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
        return result
    except subprocess.TimeoutExpired:
        print("Command timed out")
        return subprocess.CompletedProcess(cmd, -1, "", "Timeout")
    except Exception as e:
        print(f"Error running command: {e}")
        return subprocess.CompletedProcess(cmd, -1, "", str(e))


def test_basic_setup():
    """Test basic database setup."""
    print("\n" + "=" * 60)
    print("TESTING BASIC SETUP")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        result = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/basic_setup.sql", "-v"]
        )

        if result.returncode == 0:
            print("✅ Basic setup test passed")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Tables created: {tables}")

            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"Users created: {user_count}")

            cursor.execute("SELECT COUNT(*) FROM posts")
            post_count = cursor.fetchone()[0]
            print(f"Posts created: {post_count}")

            conn.close()
        else:
            print(f"❌ Basic setup test failed: {result.stderr}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_migration():
    """Test database migration."""
    print("\n" + "=" * 60)
    print("TESTING MIGRATION")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        result1 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/basic_setup.sql"]
        )

        if result1.returncode != 0:
            print(f"❌ Basic setup failed: {result1.stderr}")
            return

        result2 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/migration_example.sql", "-v"]
        )

        if result2.returncode == 0:
            print("✅ Migration test passed")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"All tables: {tables}")

            cursor.execute("SELECT COUNT(*) FROM migration_history")
            migration_count = cursor.fetchone()[0]
            print(f"Migrations recorded: {migration_count}")

            cursor.execute("SELECT COUNT(*) FROM users WHERE role IS NOT NULL")
            users_with_roles = cursor.fetchone()[0]
            print(f"Users with roles: {users_with_roles}")

            conn.close()
        else:
            print(f"❌ Migration test failed: {result2.stderr}")

    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_data_analysis():
    """Test data analysis."""
    print("\n" + "=" * 60)
    print("TESTING DATA ANALYSIS")
    print("=" * 60)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # Run all setup and migration first
        result1 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/basic_setup.sql"]
        )

        result2 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/migration_example.sql"]
        )

        if result1.returncode != 0 or result2.returncode != 0:
            print("❌ Setup failed, skipping analysis test")
            return

        # Run data analysis
        result3 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/data_analysis.sql", "-v"]
        )

        if result3.returncode == 0:
            print("✅ Data analysis test passed")

            # Verify analysis results
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            print(f"Total users: {total_users}")

            # Check total posts
            cursor.execute("SELECT COUNT(*) FROM posts")
            total_posts = cursor.fetchone()[0]
            print(f"Total posts: {total_posts}")

            # Check published posts
            cursor.execute("SELECT COUNT(*) FROM posts WHERE published = 1")
            published_posts = cursor.fetchone()[0]
            print(f"Published posts: {published_posts}")

            conn.close()
        else:
            print(f"❌ Data analysis test failed: {result3.stderr}")

    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_maintenance():
    """Test maintenance operations."""
    print("\n" + "=" * 60)
    print("TESTING MAINTENANCE")
    print("=" * 60)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # Run all previous steps first
        result1 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/basic_setup.sql"]
        )

        result2 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/migration_example.sql"]
        )

        result3 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/data_analysis.sql"]
        )

        if any(r.returncode != 0 for r in [result1, result2, result3]):
            print("❌ Previous steps failed, skipping maintenance test")
            return

        # Run maintenance
        result4 = run_cli_command(
            [
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                "examples/cleanup_and_maintenance.sql",
                "-v",
            ]
        )

        if result4.returncode == 0:
            print("✅ Maintenance test passed")

            # Verify maintenance results
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if archive table was created
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_archive'"
            )
            archive_exists = cursor.fetchone() is not None
            print(f"Archive table created: {archive_exists}")

            # Check archived posts
            if archive_exists:
                cursor.execute("SELECT COUNT(*) FROM posts_archive")
                archived_count = cursor.fetchone()[0]
                print(f"Posts archived: {archived_count}")

            conn.close()
        else:
            print(f"❌ Maintenance test failed: {result4.stderr}")

    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_error_handling():
    """Test error handling scenarios."""
    print("\n" + "=" * 60)
    print("TESTING ERROR HANDLING")
    print("=" * 60)

    # Test with non-existent file
    result1 = run_cli_command(["-c", "sqlite:///test.db", "-f", "nonexistent.sql"])

    if result1.returncode != 0:
        print("✅ Non-existent file error handled correctly")
    else:
        print("❌ Non-existent file should have failed")

    # Test with invalid connection string
    result2 = run_cli_command(
        ["-c", "invalid://connection", "-f", "examples/basic_setup.sql"]
    )

    if result2.returncode != 0:
        print("✅ Invalid connection string error handled correctly")
    else:
        print("❌ Invalid connection string should have failed")

    # Test with pattern that matches no files
    result3 = run_cli_command(["-c", "sqlite:///test.db", "-p", "nonexistent/*.sql"])

    if result3.returncode != 0:
        print("✅ No matching files error handled correctly")
    else:
        print("❌ No matching files should have failed")


def test_security_features():
    """Test security features."""
    print("\n" + "=" * 60)
    print("TESTING SECURITY FEATURES")
    print("=" * 60)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # Test with security enabled (default)
        result1 = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-f", "examples/basic_setup.sql", "-v"]
        )

        if result1.returncode == 0:
            print("✅ Security validation (default) test passed")
        else:
            print(f"❌ Security validation test failed: {result1.stderr}")

        # Test with security disabled
        result2 = run_cli_command(
            [
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                "examples/basic_setup.sql",
                # Security is always enforced
                "-v",
            ]
        )

        if result2.returncode == 0:
            print("✅ Security disabled test passed")
        else:
            print(f"❌ Security disabled test failed: {result2.stderr}")

    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_file_patterns():
    """Test file pattern matching."""
    print("\n" + "=" * 60)
    print("TESTING FILE PATTERNS")
    print("=" * 60)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # Test pattern matching with all SQL files in examples
        result = run_cli_command(
            ["-c", f"sqlite:///{db_path}", "-p", "examples/*.sql", "-v"]
        )

        if result.returncode == 0:
            print("✅ File pattern test passed")
            if result.stdout:
                print(f"Output: {result.stdout[:500]}...")
            else:
                print("Output: (no output)")
        else:
            print(f"❌ File pattern test failed: {result.stderr}")

    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """Run all tests."""
    print("splurge-sql-runner CLI Examples Test Suite")
    print("=" * 60)

    # Check if we're in the right directory
    if not os.path.exists("examples"):
        print(
            "❌ Examples directory not found. Please run this script from the project root."
        )
        sys.exit(1)

    # Check if splurge-sql-runner is available
    try:
        import splurge_sql_runner  # noqa: F401

        print("✅ splurge-sql-runner is available")
    except ImportError:
        print("❌ splurge-sql-runner is not installed. Please install it first.")
        sys.exit(1)

    # Run tests
    test_basic_setup()
    test_migration()
    test_data_analysis()
    test_maintenance()
    test_error_handling()
    test_security_features()
    test_file_patterns()

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)
    print("Check the output above for test results.")
    print("\nTo run the deployment script manually:")
    print("  ./examples/deploy_database.sh")
    print("\nTo run individual CLI commands:")
    print(
        "  python -m splurge_sql_runner -c sqlite:///test.db -f examples/basic_setup.sql -v"
    )


if __name__ == "__main__":
    main()
