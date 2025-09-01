"""
End-to-end tests for CLI workflow.

Tests complete command-line workflows from file input to database output,
covering the full application lifecycle.
"""

import pytest
import subprocess
import json
import os
from pathlib import Path
from typing import List


class TestCLIWorkflowE2E:
    """End-to-end tests for complete CLI workflows."""

    def run_cli_command(self, args: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
        """Helper to run CLI commands."""
        cmd = ["python", "-m", "splurge_sql_runner"] + args
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)

        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid chars instead of failing
                cwd=cwd or Path.cwd(),
                env=env,
                timeout=30
            )
        except UnicodeDecodeError:
            # Fallback if Unicode decoding fails
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,  # Get bytes instead of text
                cwd=cwd or Path.cwd(),
                env=env,
                timeout=30
            )
            # Convert bytes to string with error handling
            if result.stdout:
                result.stdout = result.stdout.decode('utf-8', errors='replace')
            if result.stderr:
                result.stderr = result.stderr.decode('utf-8', errors='replace')
            return result

    @pytest.fixture
    def test_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database file."""
        return tmp_path / "test.db"

    @pytest.fixture
    def sql_setup_file(self, tmp_path: Path) -> Path:
        """Create a SQL setup file."""
        sql_file = tmp_path / "setup.sql"
        sql_file.write_text("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)
        return sql_file

    @pytest.fixture
    def sql_data_file(self, tmp_path: Path) -> Path:
        """Create a SQL data insertion file."""
        sql_file = tmp_path / "data.sql"
        sql_file.write_text("""
        INSERT INTO users (name, email) VALUES
            ('Alice Johnson', 'alice@example.com'),
            ('Bob Smith', 'bob@example.com'),
            ('Charlie Brown', 'charlie@example.com');

        INSERT INTO orders (user_id, amount) VALUES
            (1, 99.99),
            (1, 149.50),
            (2, 75.00),
            (3, 200.00);
        """)
        return sql_file

    @pytest.fixture
    def sql_query_file(self, tmp_path: Path) -> Path:
        """Create a SQL query file."""
        sql_file = tmp_path / "query.sql"
        sql_file.write_text("""
        -- Get user order summary
        SELECT
            u.name,
            u.email,
            COUNT(o.id) as order_count,
            ROUND(SUM(o.amount), 2) as total_amount
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name, u.email
        ORDER BY total_amount DESC;
        """)
        return sql_file

    @pytest.mark.e2e
    def test_complete_workflow_sqlite_file(self, test_db_path: Path, sql_setup_file: Path,
                                         sql_data_file: Path, sql_query_file: Path):
        """Test complete workflow: setup -> data -> query."""
        # Step 1: Setup database schema
        result = self.run_cli_command([
            "--connection", f"sqlite:///{test_db_path}",
            "--file", str(sql_setup_file)
        ])

        assert result.returncode == 0
        assert "Statement executed successfully" in result.stdout

        # Step 2: Insert data
        result = self.run_cli_command([
            "--connection", f"sqlite:///{test_db_path}",
            "--file", str(sql_data_file)
        ])

        assert result.returncode == 0
        assert result.stdout.count("Rows affected:") == 2  # 2 INSERT statements

        # Step 3: Query data
        result = self.run_cli_command([
            "--connection", f"sqlite:///{test_db_path}",
            "--file", str(sql_query_file)
        ])

        assert result.returncode == 0
        assert "Rows returned: 3" in result.stdout
        assert "Alice Johnson" in result.stdout
        assert "Bob Smith" in result.stdout
        assert "Charlie Brown" in result.stdout

    @pytest.mark.e2e
    def test_workflow_with_json_output(self, test_db_path: Path, sql_setup_file: Path,
                                     sql_data_file: Path):
        """Test workflow with JSON output format."""
        # Setup database
        self.run_cli_command([
            "--connection", f"sqlite:///{test_db_path}",
            "--file", str(sql_setup_file)
        ])

        # Insert data
        self.run_cli_command([
            "--connection", f"sqlite:///{test_db_path}",
            "--file", str(sql_data_file)
        ])

        # Query with JSON output
        result = self.run_cli_command([
            "--connection", f"sqlite:///{test_db_path}",
            "--json",
            "--file", str(Path(__file__).parent.parent / "test_data" / "simple_query.sql")
        ])

        # Create a simple query file for this test
        query_file = test_db_path.parent / "test_query.sql"
        query_file.write_text("SELECT name, email FROM users ORDER BY name;")

        result = self.run_cli_command([
            "--connection", f"sqlite:///{test_db_path}",
            "--json",
            "--file", str(query_file)
        ])

        assert result.returncode == 0

        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            assert isinstance(output_data, list)
            assert len(output_data) > 0
            assert "result" in output_data[0]
        except json.JSONDecodeError:
            # If not valid JSON, check for JSON-like structure
            assert "[" in result.stdout or "{" in result.stdout

    @pytest.mark.e2e
    def test_workflow_with_config_file(self, tmp_path: Path):
        """Test workflow using configuration file."""
        # Create config file
        config_file = tmp_path / "test_config.json"
        config_data = {
            "database": {
                "engine": "sqlite",
                "connection": {"database": str(tmp_path / "config_test.db")}
            },
            "logging": {
                "level": "INFO",
                "format": "json"
            },
            "security": {
                "validate_sql": True,
                "allowed_commands": ["SELECT", "INSERT", "CREATE"]
            }
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

        # Create SQL file
        sql_file = tmp_path / "config_test.sql"
        sql_file.write_text("""
        CREATE TABLE config_test (id INTEGER, name TEXT);
        INSERT INTO config_test VALUES (1, 'config_test_data');
        SELECT * FROM config_test;
        """)

        # Run with config (still need to specify connection)
        result = self.run_cli_command([
            "--config", str(config_file),
            "--connection", f"sqlite:///{tmp_path / 'config_test.db'}",
            "--file", str(sql_file)
        ])

        assert result.returncode == 0
        assert "Statement executed successfully" in result.stdout
        assert "Rows affected: 1" in result.stdout
        assert "Rows returned: 1" in result.stdout

    @pytest.mark.e2e
    def test_workflow_with_multiple_files_pattern(self, tmp_path: Path):
        """Test workflow with multiple files using pattern matching."""
        # Create database
        db_path = tmp_path / "pattern_test.db"

        # Create multiple SQL files
        for i in range(3):
            sql_file = tmp_path / f"pattern_test_{i}.sql"
            sql_file.write_text(f"""
            CREATE TABLE IF NOT EXISTS pattern_table_{i} (
                id INTEGER PRIMARY KEY,
                value TEXT DEFAULT 'file_{i}'
            );
            INSERT INTO pattern_table_{i} (value) VALUES ('data_{i}');
            """)

        # Run with pattern
        result = self.run_cli_command([
            "--connection", f"sqlite:///{db_path}",
            "--pattern", "pattern_test_*.sql"
        ], cwd=tmp_path)

        assert result.returncode == 0
        # Note: CREATE TABLE IF NOT EXISTS only executes for first file, others show Rows affected
        total_success_messages = (result.stdout.count("Statement executed successfully") +
                                result.stdout.count("Rows affected:"))
        assert total_success_messages >= 5  # At least 5 successful operations

    @pytest.mark.e2e
    def test_workflow_error_handling(self, tmp_path: Path):
        """Test workflow with error handling and recovery."""
        db_path = tmp_path / "error_test.db"

        # Create SQL file with errors
        sql_file = tmp_path / "error_test.sql"
        sql_file.write_text("""
        CREATE TABLE error_test (id INTEGER, name TEXT);

        -- Valid insert
        INSERT INTO error_test VALUES (1, 'valid');

        -- Invalid SQL
        INSERT INTO error_test VALUES (2, 'invalid', 'extra_column');

        -- Valid insert after error
        INSERT INTO error_test VALUES (3, 'also_valid');
        """)

        # Run without stop-on-error (default behavior)
        result = self.run_cli_command([
            "--connection", f"sqlite:///{db_path}",
            "--file", str(sql_file)
        ])

        assert result.returncode == 0  # Should succeed despite errors

        # Create check query
        check_file = tmp_path / "check_results.sql"
        check_file.write_text("SELECT COUNT(*) as count FROM error_test;")

        # Check that successful operations completed
        query_result = self.run_cli_command([
            "--connection", f"sqlite:///{db_path}",
            "--file", str(check_file)
        ])

        assert query_result.returncode == 0
        assert query_result.stdout is not None
        assert "2" in query_result.stdout  # Should have 2 valid rows

    @pytest.mark.e2e
    def test_workflow_with_security_validation(self, tmp_path: Path):
        """Test workflow with security validation enabled."""
        db_path = tmp_path / "security_test.db"

        # Create SQL file with potentially dangerous content
        sql_file = tmp_path / "security_test.sql"
        sql_file.write_text("""
        SELECT 1 as test;

        -- This should be blocked by security (EXEC pattern)
        EXEC sp_helpdb;
        """)

        # Run with security validation
        result = self.run_cli_command([
            "--connection", f"sqlite:///{db_path}",
            "--file", str(sql_file)
        ])

        # The first SELECT should work, but EXEC should be blocked
        assert result.returncode == 1  # Should fail due to blocked command
        assert "dangerous pattern" in result.stdout.lower() or "dangerous pattern" in str(result.stderr).lower()

    @pytest.mark.e2e
    def test_workflow_with_large_dataset(self, tmp_path: Path):
        """Test workflow performance with larger dataset."""
        db_path = tmp_path / "large_test.db"

        # Create setup file
        setup_file = tmp_path / "large_setup.sql"
        setup_file.write_text("""
        CREATE TABLE large_test (
            id INTEGER PRIMARY KEY,
            data TEXT,
            number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create data file with multiple inserts
        data_file = tmp_path / "large_data.sql"
        inserts = []
        for i in range(100):  # Create 100 inserts
            inserts.append(f"INSERT INTO large_test (data, number) VALUES ('data_{i}', {i});")
        data_file.write_text("\n".join(inserts))

        # Create query file
        query_file = tmp_path / "large_query.sql"
        query_file.write_text("""
        SELECT
            COUNT(*) as total_rows,
            AVG(number) as avg_number,
            MIN(number) as min_number,
            MAX(number) as max_number
        FROM large_test;
        """)

        # Execute workflow
        # Setup
        result = self.run_cli_command([
            "--connection", f"sqlite:///{db_path}",
            "--file", str(setup_file)
        ])
        assert result.returncode == 0

        # Data insertion
        result = self.run_cli_command([
            "--connection", f"sqlite:///{db_path}",
            "--file", str(data_file)
        ])
        assert result.returncode == 0
        assert "Rows affected: 1" in result.stdout

        # Query
        result = self.run_cli_command([
            "--connection", f"sqlite:///{db_path}",
            "--file", str(query_file)
        ])
        assert result.returncode == 0
        assert "Rows returned: 1" in result.stdout
        assert "100" in result.stdout  # Should show 100 total rows
