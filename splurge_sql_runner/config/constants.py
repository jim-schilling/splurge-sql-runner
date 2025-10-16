"""
Configuration constants for splurge-sql-runner.

Centralized location for all configuration constants to avoid duplication
across the codebase.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

# Statement limits
DEFAULT_MAX_STATEMENTS_PER_FILE: int = 100
DEFAULT_MAX_STATEMENT_LENGTH: int = 10000

# Database connection settings
DEFAULT_CONNECTION_TIMEOUT: int = 30

# Security patterns
DANGEROUS_PATH_PATTERNS: tuple[str, ...] = (
    "..",
    "~",
    "/etc",
    "/var",
    "/usr",
    "/bin",
    "/sbin",
    "/dev",
    "\\windows\\system32",
    "\\windows\\syswow64",
    "\\program files",
    "\\program files (x86)",
)

DANGEROUS_SQL_PATTERNS: tuple[str, ...] = (
    "DROP DATABASE",
    "TRUNCATE DATABASE",
    "DELETE FROM INFORMATION_SCHEMA",
    "DELETE FROM SYS.",
    "EXEC ",
    "EXECUTE ",
    "XP_",
    "SP_",
    "OPENROWSET",
    "OPENDATASOURCE",
    "BACKUP DATABASE",
    "RESTORE DATABASE",
    "SHUTDOWN",
    "KILL",
    "RECONFIGURE",
)

DANGEROUS_URL_PATTERNS: tuple[str, ...] = (
    "--",
    "/*",
    "*/",
    "xp_",
    "sp_",
    "exec",
    "execute",
    "script:",
    "javascript:",
    "data:",
)

# Dangerous characters for shell injection prevention
DANGEROUS_SHELL_CHARACTERS: tuple[str, ...] = (
    # Command separators and pipes
    ";",
    "|",
    "&&",
    "||",
    # Command substitution and evaluation
    "`",
    "$(",
    "${",
    # Redirection operators
    ">>",
    "<<",
    "<<<",
    # Character classes (dangerous for injection)
    "[",
    "]",
    # Escaping and quotes
    "'",
    '"',
    # History expansion
    "!",
    # Whitespace that can separate commands
    " ",
    "\t",
    "\n",
    "\r",
    # Process substitution
    "<(",
    ">(",
)

# Allowed file extensions
DEFAULT_ALLOWED_FILE_EXTENSIONS: tuple[str, ...] = (".sql",)

# Application settings
DEFAULT_ENABLE_VERBOSE_OUTPUT: bool = False
DEFAULT_ENABLE_DEBUG_MODE: bool = False
DEFAULT_ENABLE_VALIDATION: bool = True

# Logging settings
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_LOG_FORMAT: str = "json"
