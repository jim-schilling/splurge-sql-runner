"""Module entry-point to run the Splurge Pub-Sub CLI.

This module allows running the package as a script using:

    python -m splurge_pub_sub

It simply forwards execution to :func:`splurge_pub_sub.cli.main`.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
