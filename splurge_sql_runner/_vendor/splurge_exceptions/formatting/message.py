"""Error message formatting utilities.

Provides ErrorMessageFormatter class for formatting Splurge exceptions
with context, suggestions, and metadata in a readable way.
"""

from typing import Any

from .. import SplurgeError


class ErrorMessageFormatter:
    """Formats Splurge exceptions into readable error messages.

    Provides methods for formatting exceptions with context, suggestions,
    and other metadata in a clear and structured way.
    """

    def format_error(
        self,
        error: SplurgeError,
        include_context: bool = True,
        include_suggestions: bool = True,
    ) -> str:
        """Format a Splurge exception into a readable message.

        Args:
            error: The SplurgeError to format
            include_context: Whether to include context data
            include_suggestions: Whether to include suggestions

        Returns:
            Formatted error message as a string
        """
        lines: list[str] = []

        # Add error code if present
        if error.error_code:
            lines.append(f"[{error.error_code}]")

        # Add message if present
        if error.message:
            lines.append(error.message)

        # Add context if requested and present
        if include_context and error.get_all_context():
            lines.append("")
            lines.append("Context:")
            context_str = self.format_context(error.get_all_context())
            lines.append(context_str)

        # Add suggestions if requested and present
        if include_suggestions and error.get_suggestions():
            lines.append("")
            lines.append("Suggestions:")
            suggestions_str = self.format_suggestions(error.get_suggestions())
            lines.append(suggestions_str)

        return "\n".join(lines)

    def format_context(self, context: dict[str, Any]) -> str:
        """Format context data into a readable string.

        Args:
            context: Dictionary of context key-value pairs

        Returns:
            Formatted context as a string
        """
        if not context:
            return ""

        lines: list[str] = []
        for key, value in context.items():
            # Safely format values: protect against objects whose __str__/__repr__ raise
            try:
                value_str = str(value)
            except Exception:
                try:
                    value_str = repr(value)
                except Exception:
                    value_str = "<unrepresentable object>"

            lines.append(f"  {key}: {value_str}")

        return "\n".join(lines)

    def format_suggestions(self, suggestions: list[str]) -> str:
        """Format suggestions list into a readable string.

        Args:
            suggestions: List of suggestion strings

        Returns:
            Formatted suggestions as a string
        """
        if not suggestions:
            return ""

        lines: list[str] = []
        for i, suggestion in enumerate(suggestions, 1):
            lines.append(f"  {i}. {suggestion}")

        return "\n".join(lines)
