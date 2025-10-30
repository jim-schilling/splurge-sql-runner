"""
File path validation utilities for secure file operations.

This module provides utilities for validating file paths to prevent
path traversal attacks and ensure secure file operations.

Copyright (c) 2025 Jim Schilling

Please preserve this header and all related material when sharing!

This module is licensed under the MIT License.
"""

# Standard library imports
import os
import re
from collections.abc import Callable
from pathlib import Path

# Local imports
from .exceptions import (
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoOSError,
    SplurgeSafeIoPathValidationError,
    SplurgeSafeIoPermissionError,
)

# Module-level constants for path validation
_MAX_PATH_LENGTH = 4096  # Maximum path length for most filesystems
_DEFAULT_FILENAME = "unnamed_file"  # Default filename when sanitization results in empty string


class PathValidator:
    """Utility class for validating file paths securely.

    This class centralizes path validation logic to prevent path
    traversal attacks and reject paths with dangerous characters or
    unsupported formats. It offers helpers for registering lightweight
    pre-resolution policies used by applications or tests.
    """

    # Private constants for path validation
    # A list of pre-resolution policy callables. Each callable receives
    # the raw path string and may either return None (pass) or raise
    # SplurgeSafeIoPathValidationError to reject the path. Policies are
    # intentionally lightweight and optional — by default there are no
    # pre-resolution checks to avoid false positives on valid platform
    # paths. Callers/tests can register policies via
    # `register_pre_resolution_policy` if they need additional checks.
    _pre_resolution_policies: list[Callable[[str], None]] = []

    @classmethod
    def register_pre_resolution_policy(cls, policy: Callable[[str], None]) -> None:
        """Register a pre-resolution policy callable.

        The `policy` callable will be invoked with the raw path string
        prior to resolution. The callable should raise
        :class:`SplurgeSafeIoPathValidationError` to reject the path, or
        return ``None`` to allow it.

        Args:
            policy (Callable[[str], None]): A callable that accepts the raw
                path string and either returns None or raises
                :class:`SplurgeSafeIoPathValidationError`.

        Raises:
            None: This method does not raise exceptions.
        """
        cls._pre_resolution_policies.append(policy)

    @classmethod
    def clear_pre_resolution_policies(cls) -> None:
        """Clear all registered pre-resolution policies.

        This is primarily useful for tests or application shutdown to
        ensure no policies remain registered.
        """
        cls._pre_resolution_policies.clear()

    @classmethod
    def list_pre_resolution_policies(cls) -> list[Callable[[str], None]]:
        """Return a shallow copy of registered pre-resolution policies.

        Returns:
            list[Callable[[str], None]]: A shallow copy of policy callables.
        """
        return list(cls._pre_resolution_policies)

    # Commonly reserved characters that should be rejected in many
    # filesystem contexts. Control characters (U+0000..U+001F) are
    # checked programmatically in `_check_dangerous_characters` below
    # to avoid enumerating them here.
    _DANGEROUS_CHARS = [
        "<",
        ">",
        '"',
        "|",
        "?",
        "*",  # Windows reserved characters (excluding ':' for drive letters)
    ]

    MAX_PATH_LENGTH = _MAX_PATH_LENGTH

    @classmethod
    def get_validated_path(
        cls,
        file_path: str | Path,
        *,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_readable: bool = False,
        must_be_writable: bool = False,
        allow_relative: bool = True,
        base_directory: str | Path | None = None,
    ) -> Path:
        """Validate and return a resolved pathlib.Path.

        Args:
            file_path (str | Path): The file path to validate
            must_exist (bool): If True, the path must exist
            must_be_file (bool): If True, the path must be a file (not directory)
            must_be_readable (bool): If True, the file must be readable
            must_be_writable (bool): If True, the file must be writable
            allow_relative (bool): If False, relative paths are rejected
            base_directory (str | Path | None): If provided, the resolved path
                must reside within this base directory

        Returns:
            Path: The validated and resolved Path object.

        Raises:
            SplurgeSafeIoPathValidationError: If the path fails validation checks.
            SplurgeSafeIoFileNotFoundError: If file existence checks fail.
            SplurgeSafeIoPermissionError: If permission checks fail.
        """
        # Convert to Path object
        path = Path(file_path) if isinstance(file_path, str) else file_path

        # Get the original string for validation (before Path normalization)
        path_str = str(file_path) if isinstance(file_path, str) else str(path)

        # Check for dangerous characters
        cls._check_dangerous_characters(path_str)

        # Check for path traversal patterns
        cls._check_path_traversal(path_str)

        # Check path length
        cls._check_path_length(path_str)

        # Handle relative paths
        if not path.is_absolute() and not allow_relative:
            raise (
                SplurgeSafeIoPathValidationError(
                    error_code="relative-path-not-allowed", message=f"Relative paths are not allowed: {path}"
                ).add_suggestion("Use an absolute path or set allow_relative=True if appropriate.")
            )

        # Resolve path (handles symlinks and normalizes)
        try:
            if base_directory:
                base_path = Path(base_directory).resolve()
                if not path.is_absolute():
                    resolved_path = (base_path / path).resolve()
                else:
                    resolved_path = path.resolve()

                # Ensure resolved path is within base directory
                try:
                    resolved_path.relative_to(base_path)
                except ValueError:
                    raise SplurgeSafeIoPathValidationError(
                        error_code="path-traversal-detected",
                        message=f"Path {path} resolves outside base directory {base_directory}",
                    ) from None
            else:
                resolved_path = path.resolve()
        except (OSError, RuntimeError) as e:
            raise (
                SplurgeSafeIoPathValidationError(
                    error_code="path-resolution-failed", message=f"Failed to resolve path {path}"
                ).add_suggestion("Ensure the path contains valid characters and does not contain problematic symlinks.")
            ) from e

        # Check if file exists
        if must_exist and not resolved_path.exists():
            raise (
                SplurgeSafeIoFileNotFoundError(
                    error_code="file-not-found", message=f"File does not exist: {resolved_path}"
                )
                .add_suggestion("Verify the file path is correct.")
                .add_suggestion("Create the file if it is missing.")
                .add_suggestion("Set must_exist=False if the file is expected to be created later.")
            )

        # Check if it's a file (not directory)
        if must_be_file and resolved_path.exists() and not resolved_path.is_file():
            raise SplurgeSafeIoPathValidationError(
                error_code="not-a-file", message=f"Path is not a file: {resolved_path}"
            )

        # Check if file is readable
        if must_be_readable:
            if not resolved_path.exists():
                raise (
                    SplurgeSafeIoFileNotFoundError(
                        error_code="file-not-found",
                        message=f"Cannot check readability of non-existent file: {resolved_path}",
                    )
                    .add_suggestion("Ensure the file exists before checking readability.")
                    .add_suggestion(
                        "Set must_be_readable=False and must_exist=False if the file is not expected to exist."
                    )
                )

            if not os.access(resolved_path, os.R_OK):
                raise (
                    SplurgeSafeIoPermissionError(
                        error_code="permission-denied", message=f"File is not readable: {resolved_path}"
                    )
                    .add_suggestion("Check file permissions.")
                    .add_suggestion("Ensure the file is not locked by another process.")
                )

        # Check if file is writable
        if must_be_writable:
            if not resolved_path.exists():
                raise (
                    SplurgeSafeIoFileNotFoundError(
                        error_code="file-not-found",
                        message=f"Cannot check writability of non-existent file: {resolved_path}",
                    )
                    .add_suggestion("Ensure the file exists before checking writability.")
                    .add_suggestion(
                        "Set must_be_writable=False and must_exist=False if the file is not expected to exist."
                    )
                )

            if not os.access(resolved_path, os.W_OK):
                raise (
                    SplurgeSafeIoPermissionError(
                        error_code="permission-denied", message=f"File is not writable: {resolved_path}"
                    )
                    .add_suggestion("Check file permissions.")
                    .add_suggestion("Ensure the file is not read-only or locked by another process.")
                    .add_suggestion(
                        "Set must_be_writable=False and must_exist=False if the file is not expected to exist."
                    )
                )

        return resolved_path

    @classmethod
    def _is_valid_windows_drive_pattern(cls, path_str: str) -> bool:
        """Return True if ``path_str`` looks like a valid Windows drive pattern.

        Accepts both ``C:`` and ``C:\\...`` or ``C:/...`` forms.
        """
        # Must be C: at the end of the string, or C:\ (or C:/) followed by path
        return bool(re.match(r"^[A-Za-z]:$", path_str)) or bool(re.match(r"^[A-Za-z]:[\\/]", path_str))

    @classmethod
    def _check_dangerous_characters(cls, path_str: str) -> None:
        """Raise if ``path_str`` contains characters disallowed by policy.

        This guards against NULs, control characters, and reserved filesystem
        characters which may be used in injection or traversal attacks.
        """
        # Check for reserved dangerous characters (e.g. < > " | ? *)
        for char in cls._DANGEROUS_CHARS:
            idx = path_str.find(char)
            if idx != -1:
                raise SplurgeSafeIoPathValidationError(
                    error_code="dangerous-character",
                    message=f"Path contains dangerous character: {repr(char)}",
                    details={"Character at position": idx},
                )

        # Programmatic check for C0 control characters (U+0000..U+001F).
        # This avoids listing control characters explicitly and is easier
        # to maintain. Report the first found control character's position.
        for idx, ch in enumerate(path_str):
            if ord(ch) < 32:
                raise SplurgeSafeIoPathValidationError(
                    error_code="control-character",
                    message=f"Path contains control character: U+{ord(ch):04X}",
                    details={"Character at position": idx},
                )

        # Special handling for colons - only allow them in Windows drive letters (e.g., C:)
        if ":" in path_str:
            if not cls._is_valid_windows_drive_pattern(path_str):
                raise SplurgeSafeIoPathValidationError(
                    error_code="invalid-colon-position", message="Path contains colon in invalid position"
                ).add_suggestion("Colons are only allowed in Windows drive letters (e.g., C: or C:\\)")

    @classmethod
    def _check_path_traversal(cls, path_str: str) -> None:
        """Raise if ``path_str`` contains obvious traversal patterns.

        This is a best-effort check that catches sequences such as ``..``
        and unusual repeated separators that are likely malicious.
        """
        # Invoke any registered pre-resolution policy callables. Each
        # policy may raise SplurgeSafeIoPathValidationError to reject the
        # path. If no policies are registered, this check is a no-op.
        for policy in cls._pre_resolution_policies:
            # Policies are trusted callables provided by the application or
            # tests; call them with the raw path string.
            policy(path_str)

    @classmethod
    def _check_path_length(cls, path_str: str) -> None:
        """Raise if the path exceeds the configured maximum length.

        Long paths can indicate malformed input or attempt to overflow
        downstream APIs; this check enforces a sane upper bound.
        """
        if len(path_str) > cls.MAX_PATH_LENGTH:
            raise SplurgeSafeIoPathValidationError(
                error_code="path-too-long", message=f"Path is too long: {len(path_str)} characters"
            ).add_suggestion("Consider shortening the path or using a different file name.")

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize a filename by removing dangerous characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename

        Raises:
            None: This method does not raise exceptions.
        """
        # Remove or replace dangerous characters
        sanitized = filename

        # Replace Windows reserved characters
        for char in ["<", ">", ":", '"', "|", "?", "*"]:
            sanitized = sanitized.replace(char, "_")

        # Remove control characters
        sanitized = "".join(char for char in sanitized if ord(char) >= 32)

        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(" .")

        # Ensure filename is not empty
        if not sanitized:
            sanitized = _DEFAULT_FILENAME

        return sanitized

    @classmethod
    def is_safe_path(cls, file_path: str | Path) -> bool:
        """Check if a path is safe without raising exceptions.

        Args:
            file_path: Path to check

        Returns:
            True if path is safe, False otherwise

        Raises:
            None: This method does not raise exceptions; it returns False for invalid paths.
        """
        try:
            cls.get_validated_path(file_path)
            return True
        except (SplurgeSafeIoPathValidationError, SplurgeSafeIoOSError):
            return False
