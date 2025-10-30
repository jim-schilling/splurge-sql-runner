#!/usr/bin/env python3
"""
Entry point for splurge-sql-runner when run as a module.

This module serves as a stub that delegates to the CLI module.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import sys

from .cli import main

if __name__ == "__main__":
    # Ensure the return code from main() is propagated to the process exit
    sys.exit(main())
