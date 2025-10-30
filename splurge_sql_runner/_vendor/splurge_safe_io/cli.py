"""Command-line interface for the Splurge Safe IO framework.

This module provides a minimal CLI that currently only exposes package
metadata (version). It's intentionally lightweight; when run without
subcommands it prints help.

Examples:

    python -m splurge_safe_io --version

"""

import argparse
import sys

from . import __version__


def main(args: list[str] | None = None) -> int:
    """Main entry point for the command-line interface.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        int: Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        prog="splurge-safe-io",
        description="Splurge Safe IO - Python file I/O framework",
    )

    # Global version argument
    parser.add_argument(
        "--version",
        action="version",
        version=f"splurge-safe-io {__version__}",
    )

    # Parse arguments (validates syntax)
    parser.parse_args(args)

    # If no command specified, show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
