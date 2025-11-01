"""
Unit tests for `splurge_sql_runner.utils.security_utils`.

Covers happy paths and error branches for:
- sanitize_shell_arguments
- is_safe_shell_argument
"""

import pytest

from splurge_sql_runner.exceptions import SplurgeSqlRunnerValueError
from splurge_sql_runner.utils.security_utils import (
    sanitize_shell_arguments,
)


@pytest.mark.unit
def test_sanitize_shell_arguments_accepts_simple_flags() -> None:
    args = ["--help", "--verbose", "subcommand"]
    assert sanitize_shell_arguments(args) == args


@pytest.mark.unit
def test_sanitize_shell_arguments_rejects_non_list() -> None:
    with pytest.raises(SplurgeSqlRunnerValueError, match="args must be a list of strings"):
        # type: ignore[arg-type]
        sanitize_shell_arguments("--help")


@pytest.mark.unit
def test_sanitize_shell_arguments_rejects_non_string_items() -> None:
    with pytest.raises(SplurgeSqlRunnerValueError, match="All command arguments must be strings"):
        # type: ignore[list-item]
        sanitize_shell_arguments(["--ok", 123])


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_arg",
    [
        ";rm -rf /",
        "unsafe|pipe",
        "double && chain",
        "back`tick`",
        "$(substitution)",
        "${expansion}",
        ">> out",
        "<< in",
        "<<< here",
        "brackets[",
        "]brackets",
        "quote'",
        '"quote"',
        "history!bang",
        "space space",  # contains space
        "tab\tchar",
        "newline\nchar",
        "carriage\rreturn",
        "<(process)",
        ">(process)",
    ],
)
def test_sanitize_shell_arguments_blocks_dangerous_characters(bad_arg: str) -> None:
    with pytest.raises(SplurgeSqlRunnerValueError, match="Potentially dangerous characters"):
        sanitize_shell_arguments([bad_arg])
