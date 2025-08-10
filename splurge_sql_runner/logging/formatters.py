"""
Log formatters for splurge-sql-runner.

Provides JSON and other log formatters for structured logging.
"""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging using Python's built-in json module.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON formatted log message
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        if hasattr(record, "correlation_id") and record.correlation_id:
            log_entry["correlation_id"] = record.correlation_id

        # Add request ID if present (for backward compatibility)
        if hasattr(record, "request_id") and record.request_id:
            log_entry["request_id"] = record.request_id

        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in log_entry and not key.startswith('_') and key != 'exc_info' and key != 'msg':
                log_entry[key] = value

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)
