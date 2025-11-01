# splurge-sql-runner

[![PyPI version](https://badge.fury.io/py/splurge-sql-runner.svg)](https://pypi.org/project/splurge-sql-runner/)
[![Python versions](https://img.shields.io/pypi/pyversions/splurge-sql-runner.svg)](https://pypi.org/project/splurge-sql-runner/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[![CI](https://github.com/jim-schilling/splurge-sql-runner/actions/workflows/ci-quick-test.yml/badge.svg)](https://github.com/jim-schilling/splurge-sql-runner/actions/workflows/ci-quick-test.yml)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](https://github.com/jim-schilling/splurge-sql-runner)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-checked-black)](https://mypy-lang.org/)


A robust, secure, and user-friendly Python utility for executing SQL files against databases with support for multiple statements, comments, and formatted results.

## ✨ Key Features

- **🔧 Multi-Statement Execution**: Process SQL files containing multiple statements
- **🗄️ Database Agnostic**: Support for SQLite, PostgreSQL, MySQL, Oracle, and more
- **🔒 Security First**: Configurable validation for SQL content and database URLs
- **📊 Smart Output**: Pretty tables, JSON format, and verbose logging
- **⚙️ Flexible Configuration**: CLI args, JSON files, and environment variables
- **🛡️ Error Recovery**: Continue processing on errors with detailed reporting

## 🚀 Quick Start

### Installation

```bash
pip install splurge-sql-runner
```

### Basic Usage

```bash
# Execute a single SQL file
splurge-sql-runner -c "sqlite:///database.db" -f "script.sql"

# Execute multiple SQL files using a pattern
splurge-sql-runner -c "sqlite:///database.db" -p "*.sql"

# With verbose output
splurge-sql-runner -c "sqlite:///database.db" -f "script.sql" -v

# JSON output for scripting
splurge-sql-runner -c "sqlite:///database.db" -f "query.sql" --json
```

## 📚 Documentation

- **[📖 Detailed Documentation](docs/README-DETAILS.md)** - Complete feature guide, configuration options, and examples
- **[🔧 CLI Reference](docs/cli/CLI-REFERENCE.md)** - Comprehensive command-line options and usage
- **[📋 Changelog](CHANGELOG.md)** - Version history and release notes

## 📋 Requirements

- **Python**: 3.10 or higher
- **sqlparse**: SQL parsing and validation
- **SQLAlchemy**: Database connectivity
- **tabulate**: Pretty table formatting

## 🤝 Contributing

We welcome contributions! Please see our [detailed documentation](docs/README-DETAILS.md#contributing) for development setup and contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*For the complete documentation, visit [docs/README-DETAILS.md](docs/README-DETAILS.md)*

