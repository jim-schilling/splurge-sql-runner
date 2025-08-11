"""
Database health checker interface for splurge-sql-runner.

Defines the contract for database health checking following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class DatabaseHealthChecker(ABC):
    """Abstract database health checker interface."""

    @abstractmethod
    def check_connection(self) -> bool:
        """Check if database connection is healthy."""
        pass

    @abstractmethod
    def check_performance(self) -> Dict[str, Any]:
        """Check database performance metrics."""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get database metrics."""
        pass
