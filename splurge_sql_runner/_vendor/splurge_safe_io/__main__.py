"""Module entry-point to run the Splurge Safe IO CLI.

This module allows running the package as a script using:

    python -m splurge_safe_io

It simply forwards execution to :func:`splurge_safe_io.cli.main`.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
