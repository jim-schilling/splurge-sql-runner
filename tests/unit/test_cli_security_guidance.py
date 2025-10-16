import pytest

import splurge_sql_runner.cli as cli_mod


@pytest.mark.parametrize(
    "msg,context,expected_hint",
    [
        ("Too many SQL statements in file", "file", "increase --max-statements"),
        ("Statement too long to process", "file", "increase security.validation.max_statement_length"),
        ("File extension not allowed: .exe", "file", "add the extension to security.allowed_file_extensions"),
        ("Dangerous pattern detected", "file", "adjust security.validation.dangerous_path_patterns"),
        ("Dangerous pattern detected", "url", "dangerous_url_patterns"),
        ("Not safe to execute", "file", "use a safe path"),
        ("scheme missing in url", "url", "include a scheme"),
    ],
)
def test_print_security_guidance_variations(capsys, msg, context, expected_hint):
    # The function prints warnings for various messages
    cli_mod._print_security_guidance(msg, context=context)
    out = capsys.readouterr().out
    assert expected_hint.split()[0] in out.lower()
