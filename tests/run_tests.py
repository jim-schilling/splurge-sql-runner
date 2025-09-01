#!/usr/bin/env python3
"""
Test runner script for splurge-sql-runner.

Provides convenient commands to run different types of tests.
"""

import subprocess
import sys
import argparse
from pathlib import Path

from splurge_sql_runner.security import SecurityValidator


def run_command(cmd: list, description: str = "") -> int:
    """Run a command and return the exit code."""
    # Validate input command
    if not isinstance(cmd, list):
        raise ValueError("cmd must be a list of strings")

    # Sanitize command arguments to prevent shell injection
    sanitized_cmd = SecurityValidator.sanitize_shell_arguments(cmd)
    if description:
        print(f"\n{'=' * 60}")
        print(description)
        print(f"{'=' * 60}")

    print(f"Running: {' '.join(sanitized_cmd)}")
    print()

    result = subprocess.run(sanitized_cmd, cwd=Path(__file__).parent.parent, shell=False)
    return result.returncode


def run_unit_tests(args):
    """Run unit tests only."""
    cmd = ["python", "-m", "pytest", "tests/"]
    if args.markers:
        cmd.extend(["-m", "unit"])
    if args.verbose:
        cmd.append("-v")
    if args.coverage:
        cmd.extend(["--cov=splurge_sql_runner", "--cov-report=term-missing"])

    return run_command(cmd, "Running Unit Tests")


def run_integration_tests(args):
    """Run integration tests only."""
    cmd = ["python", "-m", "pytest", "tests/integration/"]
    if args.markers:
        cmd.extend(["-m", "integration"])
    if args.verbose:
        cmd.append("-v")
    if args.coverage:
        cmd.extend(["--cov=splurge_sql_runner", "--cov-report=term-missing"])

    return run_command(cmd, "Running Integration Tests")


def run_e2e_tests(args):
    """Run end-to-end tests only."""
    cmd = ["python", "-m", "pytest", "tests/e2e/"]
    if args.markers:
        cmd.extend(["-m", "e2e"])
    if args.verbose:
        cmd.append("-v")
    if args.coverage:
        cmd.extend(["--cov=splurge_sql_runner", "--cov-report=term-missing"])

    return run_command(cmd, "Running End-to-End Tests")


def run_all_tests(args):
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "tests/"]
    if args.verbose:
        cmd.append("-v")
    if args.coverage:
        cmd.extend(["--cov=splurge_sql_runner", "--cov-report=term-missing", "--cov-report=html"])

    return run_command(cmd, "Running All Tests")


def run_coverage_report(args):
    """Generate coverage report."""
    cmd = [
        "python", "-m", "pytest", "tests/",
        "--cov=splurge_sql_runner",
        "--cov-report=html",
        "--cov-report=term-missing"
    ]
    if args.verbose:
        cmd.append("-v")

    exit_code = run_command(cmd, "Generating Coverage Report")

    if exit_code == 0:
        print("\n📊 Coverage report generated!")
        print("📁 HTML report: htmlcov/index.html")
        print("💡 Open in browser to view detailed coverage")

    return exit_code


def run_performance_tests(args):
    """Run performance-focused tests."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "performance"]
    if args.verbose:
        cmd.append("-v")

    return run_command(cmd, "Running Performance Tests")


def run_security_tests(args):
    """Run security-focused tests."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "security"]
    if args.verbose:
        cmd.append("-v")

    return run_command(cmd, "Running Security Tests")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test runner for splurge-sql-runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_tests.py unit              # Run unit tests
  python tests/run_tests.py integration       # Run integration tests
  python tests/run_tests.py e2e               # Run end-to-end tests
  python tests/run_tests.py all --coverage    # Run all tests with coverage
  python tests/run_tests.py coverage          # Generate coverage report
  python tests/run_tests.py security          # Run security tests
        """
    )

    parser.add_argument(
        "command",
        choices=["unit", "integration", "e2e", "all", "coverage", "performance", "security"],
        help="Test command to run"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Include coverage report"
    )

    parser.add_argument(
        "-m", "--markers",
        action="store_true",
        help="Use pytest markers to filter tests"
    )

    args = parser.parse_args()

    # Map commands to functions
    command_map = {
        "unit": run_unit_tests,
        "integration": run_integration_tests,
        "e2e": run_e2e_tests,
        "all": run_all_tests,
        "coverage": run_coverage_report,
        "performance": run_performance_tests,
        "security": run_security_tests,
    }

    # Run the selected command
    exit_code = command_map[args.command](args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
