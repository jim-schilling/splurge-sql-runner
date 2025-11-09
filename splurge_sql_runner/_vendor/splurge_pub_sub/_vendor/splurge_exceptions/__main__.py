"""Module entry-point to run the Splurge Exceptions CLI.

This module allows running the package as a script using:

    python -m splurge_exceptions

It simply forwards execution to :func:`splurge_exceptions.cli.main`.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
