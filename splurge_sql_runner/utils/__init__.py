"""
Utilities package for splurge-sql-runner.

Contains shared utility functions and helpers that can be used
by both the main application and test suites.
"""

from ..utils.file_io_adapter import FileIoAdapter

# Package domains
__domains__ = ["utils", "file", "io", "security"]

__all__ = ["FileIoAdapter"]
