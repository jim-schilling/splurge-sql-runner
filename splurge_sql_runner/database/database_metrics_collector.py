"""
Database metrics collector interface for splurge-sql-runner.

Defines the contract for database metrics collection following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class DatabaseMetricsCollector(ABC):
    """Abstract database metrics collector interface."""

    @abstractmethod
    def record_query_execution(self, sql: str, duration: float, success: bool) -> None:
        """Record query execution metrics."""
        pass

    @abstractmethod
    def record_connection_usage(self, connection_id: str, duration: float) -> None:
        """Record connection usage metrics."""
        pass

    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        pass

    @abstractmethod
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        pass
