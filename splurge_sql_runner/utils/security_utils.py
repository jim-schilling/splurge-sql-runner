"""
Security utilities for splurge-sql-runner.

Contains shared security validation functions that can be used
by both the main application and test suites to avoid circular dependencies.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.config.constants import DANGEROUS_SHELL_CHARACTERS


def sanitize_shell_arguments(args: list[str]) -> list[str]:
    """
    Sanitize shell command arguments to prevent shell injection attacks.

    This utility function provides shell injection protection by validating
    that command arguments don't contain dangerous characters that could
    be used for command injection attacks.

    Args:
        args: List of command arguments to sanitize

    Returns:
        List of sanitized arguments (same as input if validation passes)

    Raises:
        ValueError: If any argument contains dangerous characters or is not a string

    Examples:
        >>> sanitize_shell_arguments(['--help', '--verbose'])
        ['--help', '--verbose']

        >>> sanitize_shell_arguments(['safe', 'dangerous;rm -rf /'])
        ValueError: Potentially dangerous characters found in argument: dangerous;rm -rf /
    """
    if not isinstance(args, list):
        raise ValueError("args must be a list of strings")

    sanitized_args = []
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError("All command arguments must be strings")

        # Check for dangerous characters that could enable shell injection
        if any(char in arg for char in DANGEROUS_SHELL_CHARACTERS):
            raise ValueError(f"Potentially dangerous characters found in argument: {arg}")

        sanitized_args.append(arg)

    return sanitized_args
