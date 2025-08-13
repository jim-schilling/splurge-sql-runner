"""
Deprecated engine interface. Use `DatabaseClient` instead.

This file remains as a thin placeholder to avoid import errors in any
downstream usages during the migration window. All runtime functionality
has moved to `splurge_sql_runner.database.database_client`.
"""

from __future__ import annotations

# Intentionally no exports; import DatabaseClient directly from database_client.
