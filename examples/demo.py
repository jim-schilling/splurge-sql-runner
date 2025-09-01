#!/usr/bin/env python3
"""
Simple demonstration of splurge-sql-runner CLI functionality.

This script provides a step-by-step walkthrough of the CLI features.
"""

import subprocess
import sys
import os
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: list, description: str = "") -> bool:
    """Run a command and display the result."""
    if description:
        print(f"\n{'=' * 60}")
        print(description)
        print(f"{'=' * 60}")

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        if result.returncode == 0:
            print("✅ Command completed successfully")
            if result.stdout:
                print("Output:")
                print(
                    result.stdout[:1000] + "..."
                    if len(result.stdout) > 1000
                    else result.stdout
                )
            return True
        else:
            print(f"❌ Command failed with exit code {result.returncode}")
            if result.stderr:
                print("Error:")
                print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def create_demo_sql_file(content: str, filename: str) -> str:
    """Create a temporary SQL file with the given content."""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "w") as f:
        f.write(content)

    return file_path


def main():
    """Run the CLI demonstration."""
    print("splurge-sql-runner CLI Demonstration")
    print("=" * 60)

    try:
        import splurge_sql_runner  # noqa: F401

        print("✅ splurge-sql-runner is available")
    except ImportError as e:
        print(f"❌ splurge-sql-runner is not available: {e}")
        print("Please install it with: pip install splurge-sql-runner")
        print("Or run from the project root directory")
        print("For development, make sure you're in the project root directory")
        sys.exit(1)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        print(f"\nUsing temporary database: {db_path}")

        setup_sql = """
-- Basic setup demonstration
CREATE TABLE IF NOT EXISTS demo_users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO demo_users (name, email) VALUES 
    ('Alice Johnson', 'alice@example.com'),
    ('Bob Smith', 'bob@example.com'),
    ('Carol Davis', 'carol@example.com');

-- Query to verify setup
SELECT 'Setup completed successfully' as status;
SELECT COUNT(*) as user_count FROM demo_users;
"""

        setup_file = create_demo_sql_file(setup_sql, "setup.sql")

        success = run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                setup_file,
                "-v",
            ],
            "Step 1: Basic Database Setup",
        )

        if not success:
            print("❌ Setup failed, stopping demonstration")
            return

        migration_sql = """
-- Migration demonstration
ALTER TABLE demo_users ADD COLUMN role TEXT DEFAULT 'user';
ALTER TABLE demo_users ADD COLUMN last_login TIMESTAMP;

-- Create a new table
CREATE TABLE IF NOT EXISTS demo_posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    title TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES demo_users(id)
);

-- Insert some posts
INSERT INTO demo_posts (user_id, title, content) VALUES 
    (1, 'First Post', 'This is Alice''s first post'),
    (2, 'Hello World', 'Bob says hello to the world'),
    (3, 'Database Demo', 'Carol is demonstrating databases');

-- Update user roles
UPDATE demo_users SET role = 'admin' WHERE id = 1;
UPDATE demo_users SET role = 'moderator' WHERE id = 2;

-- Query to verify migration
SELECT 'Migration completed successfully' as status;
SELECT COUNT(*) as post_count FROM demo_posts;
SELECT role, COUNT(*) as count FROM demo_users GROUP BY role;
"""

        migration_file = create_demo_sql_file(migration_sql, "migration.sql")

        success = run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                migration_file,
                "-v",
            ],
            "Step 2: Database Migration",
        )

        if not success:
            print("❌ Migration failed, stopping demonstration")
            return

        analysis_sql = """
-- Data analysis demonstration
SELECT '=== DATA ANALYSIS DEMONSTRATION ===' as section;

-- User statistics
SELECT 
    'User Statistics' as analysis_type,
    COUNT(*) as total_users,
    COUNT(CASE WHEN role = 'admin' THEN 1 END) as admins,
    COUNT(CASE WHEN role = 'moderator' THEN 1 END) as moderators,
    COUNT(CASE WHEN role = 'user' THEN 1 END) as regular_users
FROM demo_users;

-- Content statistics
SELECT 
    'Content Statistics' as analysis_type,
    COUNT(*) as total_posts,
    AVG(LENGTH(content)) as avg_content_length,
    MIN(created_at) as first_post,
    MAX(created_at) as latest_post
FROM demo_posts;

-- User activity analysis
SELECT 
    u.name,
    u.role,
    COUNT(p.id) as post_count,
    AVG(LENGTH(p.content)) as avg_post_length
FROM demo_users u
LEFT JOIN demo_posts p ON u.id = p.user_id
GROUP BY u.id, u.name, u.role
ORDER BY post_count DESC;
"""

        analysis_file = create_demo_sql_file(analysis_sql, "analysis.sql")

        success = run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                analysis_file,
                "-v",
            ],
            "Step 3: Data Analysis",
        )

        if not success:
            print("❌ Analysis failed, stopping demonstration")
            return

        print(f"\n{'=' * 60}")
        print("Step 4: Pattern Matching Demonstration")
        print(f"{'=' * 60}")

        # Create multiple SQL files
        file1_sql = """
SELECT 'File 1 executed' as result;
"""
        file2_sql = """
SELECT 'File 2 executed' as result;
"""
        file3_sql = """
SELECT 'File 3 executed' as result;
"""

        temp_dir = tempfile.mkdtemp()
        file1_path = os.path.join(temp_dir, "file1.sql")
        file2_path = os.path.join(temp_dir, "file2.sql")
        file3_path = os.path.join(temp_dir, "file3.sql")

        with open(file1_path, "w") as f:
            f.write(file1_sql)
        with open(file2_path, "w") as f:
            f.write(file2_sql)
        with open(file3_path, "w") as f:
            f.write(file3_sql)

        success = run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-p",
                f"{temp_dir}/*.sql",
                "-v",
            ],
            "Processing multiple files with pattern matching",
        )

        print(f"\n{'=' * 60}")
        print("Step 5: Error Handling Demonstration")
        print(f"{'=' * 60}")

        print("Testing with non-existent file...")
        run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                "nonexistent.sql",
            ],
            "Error handling: Non-existent file",
        )

        invalid_sql = """
-- Invalid SQL demonstration
SELECT * FROM nonexistent_table;
INSERT INTO demo_users (invalid_column) VALUES ('test');
"""

        invalid_file = create_demo_sql_file(invalid_sql, "invalid.sql")

        run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                invalid_file,
                "-v",
            ],
            "Error handling: Invalid SQL",
        )

        print(f"\n{'=' * 60}")
        print("Step 6: Security Features Demonstration")
        print(f"{'=' * 60}")

        security_sql = """
-- Security demonstration
SELECT 'Security validation is enabled by default' as info;
SELECT 'This query should execute normally' as result;
"""

        security_file = create_demo_sql_file(security_sql, "security.sql")

        run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                security_file,
                "-v",
            ],
            "Security: Default validation",
        )

        run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                security_file,
                # Security is always enforced; adjust config if needed
                "-v",
            ],
            "Security: Validation disabled",
        )

        verification_sql = """
-- Final verification
SELECT '=== FINAL VERIFICATION ===' as section;

SELECT 'Database state after demonstration:' as info;
SELECT COUNT(*) as total_users FROM demo_users;
SELECT COUNT(*) as total_posts FROM demo_posts;

SELECT 'User roles distribution:' as info;
SELECT role, COUNT(*) as count FROM demo_users GROUP BY role;

SELECT 'Post count by user:' as info;
SELECT u.name, COUNT(p.id) as post_count 
FROM demo_users u 
LEFT JOIN demo_posts p ON u.id = p.user_id 
GROUP BY u.id, u.name 
ORDER BY post_count DESC;

SELECT 'Demonstration completed successfully!' as final_status;
"""

        verification_file = create_demo_sql_file(verification_sql, "verification.sql")

        success = run_command(
            [
                sys.executable,
                "-m",
                "splurge_sql_runner",
                "-c",
                f"sqlite:///{db_path}",
                "-f",
                verification_file,
                "-v",
            ],
            "Step 7: Final Verification",
        )

        print(f"\n{'=' * 60}")
        print("DEMONSTRATION SUMMARY")
        print(f"{'=' * 60}")
        print("✅ Basic database setup")
        print("✅ Database migration")
        print("✅ Data analysis")
        print("✅ Pattern matching")
        print("✅ Error handling")
        print("✅ Security features")
        print("✅ Final verification")
        print("\n🎉 CLI demonstration completed successfully!")
        print(f"\nDatabase file: {db_path}")
        print("You can inspect this file with any SQLite browser.")

        print("\nNext steps:")
        print("1. Try the examples in the examples/ directory")
        print("2. Run: python examples/test_cli.py")
        print("3. Run: ./examples/deploy_database.sh")
        print("4. Check examples/cli_examples.md for more examples")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

        for temp_file in [
            setup_file,
            migration_file,
            analysis_file,
            invalid_file,
            security_file,
            verification_file,
        ]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                os.rmdir(os.path.dirname(temp_file))


if __name__ == "__main__":
    main()
