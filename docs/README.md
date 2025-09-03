splurge-sql-runner Documentation

This folder contains project documentation per workspace standards.

- Project URL: https://github.com/jim-schilling/splurge-sql-runner
- License: MIT
- Author & Maintainer: Jim Schilling

Contents:
- Overview and goals
- Development standards and workflows
- Testing strategy and commands

Overview

splurge-sql-runner is a CLI utility for executing SQL files against databases with multi-statement support, security validation, and pretty-printed results.

Development

- Python: 3.10+
- Linting/formatting: ruff, black, mypy
- Tests: pytest, pytest-cov, pytest-xdist

Quickstart

```bash
python -m pytest -x -v -n auto
```

Testing

- Unit, integration, and e2e tests live under `tests/`
- Coverage HTML report is generated in `htmlcov/`

Security

- Security validation is always enforced; no flag exists to disable it.
- See `splurge_sql_runner/config/security_config.py` for configuration options.

