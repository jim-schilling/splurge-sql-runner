import pytest

import splurge_sql_runner.cli as cli_mod


@pytest.mark.parametrize(
    "msg,context,expected_hint",
    [
        ("Too many SQL statements in file", "file", "increase --max-statements"),
        ("Statement too long to process", "file", "increase --max-statement-length"),
        ("Dangerous pattern detected", "file", "dangerous_path_patterns"),
        ("Dangerous pattern detected", "url", "dangerous_url_patterns"),
        ("scheme missing in url", "url", "include a scheme"),
    ],
)
def test_print_security_guidance_variations(capsys, msg, context, expected_hint):
    # The function prints warnings for various messages
    cli_mod.print_security_guidance(msg, context=context)
    out = capsys.readouterr().out
    assert expected_hint.split()[0] in out.lower()
