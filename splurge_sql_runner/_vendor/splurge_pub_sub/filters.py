"""Topic filtering and pattern matching for Splurge Pub-Sub.

This module provides topic pattern matching with wildcard support, enabling
selective message delivery based on topic patterns.

Example:
    >>> pattern = TopicPattern("user.*")
    >>> pattern.matches("user.created")
    True
    >>> pattern.matches("order.created")
    False

DOMAINS: ["filters", "pattern-matching"]
"""

import re
from dataclasses import dataclass

from .exceptions import SplurgePubSubPatternError

__all__ = ["TopicPattern"]

DOMAINS = ["filters", "pattern-matching"]


@dataclass(frozen=True)
class TopicPattern:
    """Represents a topic pattern with wildcard support.

    Supports wildcard patterns:
    - '*' matches any segment (between dots)
    - '?' matches any single character within a segment
    - Exact matches for literal topics

    Args:
        pattern: Topic pattern string (e.g., "user.created", "user.*", "order.?.paid")

    Raises:
        TopicPatternError: If pattern is invalid (empty, invalid characters)

    Attributes:
        pattern: The original pattern string
        regex: Compiled regex for efficient matching
        is_exact: True if pattern is exact match (no wildcards)

    Example:
        >>> p = TopicPattern("user.*")
        >>> p.matches("user.created")
        True
        >>> p.matches("user.updated")
        True
        >>> p.matches("order.created")
        False
    """

    pattern: str
    _regex: re.Pattern[str] = None  # type: ignore[assignment]
    _is_exact: bool = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Validate pattern and compile regex."""
        # Validate pattern
        if not self.pattern:
            raise SplurgePubSubPatternError("Pattern cannot be empty")

        if self.pattern.startswith(".") or self.pattern.endswith("."):
            raise SplurgePubSubPatternError("Pattern cannot start or end with dot")

        if ".." in self.pattern:
            raise SplurgePubSubPatternError("Pattern cannot contain consecutive dots")

        # Check for invalid characters
        for char in self.pattern:
            if char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._*?-":
                raise SplurgePubSubPatternError(f"Pattern contains invalid character: {char}")

        # Compile regex pattern
        object.__setattr__(self, "_regex", self._compile_regex())
        object.__setattr__(self, "_is_exact", "*" not in self.pattern and "?" not in self.pattern)

    def _compile_regex(self) -> re.Pattern[str]:
        """Compile pattern into regex.

        Converts wildcard pattern to regex:
        - '*' -> matches any characters except dot
        - '?' -> matches any single character except dot
        - '.' -> literal dot (escaped)
        - Other chars -> literal

        Returns:
            Compiled regex pattern

        Example:
            "user.*" -> "^user\\.[^.]*$"
            "order.?.paid" -> "^order\\.[^.].paid$"
        """
        # Use placeholder to handle wildcards before escaping
        # Replace wildcards with unique placeholders
        temp_pattern = self.pattern.replace("*", "\x00STAR\x00")
        temp_pattern = temp_pattern.replace("?", "\x00QUEST\x00")

        # Escape special regex chars (except our placeholders)
        escaped = ""
        for char in temp_pattern:
            if char in ".+^$()[]{}|:":
                escaped += "\\" + char
            elif char == "\x00":
                escaped += char  # Keep placeholder markers
            else:
                escaped += char

        # Replace placeholders with regex equivalents
        # * matches any chars except dot (one segment)
        regex_pattern = escaped.replace("\x00STAR\x00", "[^.]*")
        # ? matches any single char except dot
        regex_pattern = regex_pattern.replace("\x00QUEST\x00", "[^.]")

        # Anchor to start and end for exact matching
        regex_pattern = f"^{regex_pattern}$"

        return re.compile(regex_pattern)

    def matches(self, topic: str) -> bool:
        """Check if topic matches this pattern.

        Args:
            topic: Topic string to check

        Returns:
            True if topic matches pattern, False otherwise

        Example:
            >>> pattern = TopicPattern("user.*")
            >>> pattern.matches("user.created")
            True
            >>> pattern.matches("user.updated")
            True
            >>> pattern.matches("order.created")
            False
        """
        if not topic:
            return False

        match_result = self._regex.match(topic)
        return match_result is not None

    @property
    def is_exact(self) -> bool:
        """Whether this is an exact match pattern (no wildcards).

        Returns:
            True if pattern contains no wildcards

        Example:
            >>> TopicPattern("user.created").is_exact
            True
            >>> TopicPattern("user.*").is_exact
            False
        """
        return self._is_exact

    def __repr__(self) -> str:
        """String representation of pattern."""
        pattern_type = "exact" if self.is_exact else "wildcard"
        return f"TopicPattern(pattern={self.pattern!r}, type={pattern_type})"
