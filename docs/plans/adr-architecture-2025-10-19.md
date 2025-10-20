# Architecture Decision Records (ADRs)

## Overview

This document captures key architectural decisions made in splurge-sql-runner to maintain consistency and clarity for future development.

## ADR-001: FileIoAdapter Pattern

**Status**: ACCEPTED

**Decision**: Create a centralized `FileIoAdapter` class to wrap file I/O operations and provide consistent error translation from library exceptions to domain exceptions.

**Rationale**:
- Eliminates code duplication across `config.py`, `main.py`, and `sql_helper.py`
- Provides consistent error handling and context information
- Enables streaming support for large files without API changes
- Centralizes file operation logging and validation

**Implementation**:
- Created `splurge_sql_runner/utils/file_io_adapter.py` (225 lines)
- Wraps `SafeTextFileReader` from `splurge_safe_io`
- Translates `SplurgeSafeIo*` exceptions to domain `FileError` with context
- Supports both streaming and non-streaming reads
- Three context types: "config", "sql", "generic"

**Trade-offs**:
- Added abstraction layer (single responsibility benefit outweighs complexity)
- Slightly more code upfront, but saves maintenance burden

## ADR-002: Flat Configuration Dictionary

**Status**: ACCEPTED

**Decision**: Use simple dictionary-based configuration instead of nested objects or dataclasses.

**Rationale**:
- Simple to use and understand
- Easy to merge from multiple sources (JSON, environment, CLI)
- No complex validation frameworks needed
- Works well with Python's built-in types

**Implementation**:
- Single-level dictionary with keys: `database_url`, `max_statements_per_file`, `connection_timeout`, `log_level`, `security_level`, `enable_verbose`, `enable_debug`
- Precedence: defaults → JSON file → environment variables → CLI args
- Added `_validate_config()` function to validate all keys

**Trade-offs**:
- Less type-safe than dataclasses (mitigated by validation)
- Documentation required for key names

## ADR-003: Risk-Based Security Validation

**Status**: ACCEPTED

**Decision**: Implement three-level security validation (strict, normal, permissive) with pattern-based rules rather than strict allowlists.

**Rationale**:
- Provides flexibility for different security requirements
- Reduces false positives from strict allowlists
- Patterns are more maintainable than exhaustive allowlists
- Follows principle of least surprise

**Implementation**:
- `SecurityValidator` class with level-specific patterns
- Patterns for file paths, SQL keywords, URL schemes
- Validation occurs at CLI layer before SQL processing

## ADR-004: Domain Error Hierarchy

**Status**: ACCEPTED

**Decision**: Create consolidated domain-specific exception hierarchy with context dictionaries instead of using library exceptions directly.

**Rationale**:
- Provides stable API for external consumers
- Insulates from library changes
- Enables rich context information for debugging
- Supports semantic error handling

**Implementation**:
- Base: `SplurgeSqlRunnerError`
- Categories: `ConfigurationError`, `ValidationError`, `OperationError`
- Specific: `FileError`, `DatabaseError`, `SecurityError`, `CliError`, `SqlError`
- Each exception has `message` and optional `context` dict

## ADR-005: Database Client Simplification

**Status**: ACCEPTED

**Decision**: Extract transaction execution logic into separate helper methods to reduce complexity in main `execute_sql()` method.

**Rationale**:
- Main method was 90+ lines with nested if/else
- Two distinct strategies (single vs separate transactions) deserve separate methods
- Improved testability and readability
- Easier to add transaction logging and monitoring

**Implementation**:
- `_execute_statement()` - processes individual statement
- `_execute_single_transaction()` - all statements in one transaction
- `_execute_separate_transactions()` - each statement in own transaction
- Main `execute_sql()` reduced to 45 lines

## ADR-006: CLI Constant Consolidation

**Status**: ACCEPTED

**Decision**: Consolidate CLI string constants and create reusable helper functions.

**Rationale**:
- Reduces main() function from 200+ lines to more manageable size
- Centralizes UI strings for consistent branding
- Helper functions can be tested independently
- SECURITY_GUIDANCE dictionary enables data-driven messaging

**Implementation**:
- Public constants: `ERROR_PREFIX`, `WARNING_PREFIX`, `SUCCESS_PREFIX`
- `SECURITY_GUIDANCE` dict with 7 message templates
- Helper functions: `discover_files()`, `report_execution_summary()`, `print_security_guidance()`

## ADR-007: Module Domains

**Status**: ACCEPTED

**Decision**: Add `DOMAINS` list to every module indicating its associated domains, and `__domains__` to packages.

**Rationale**:
- Improves code organization awareness
- Supports test discovery (test names mirror module domains)
- Aids onboarding and codebase navigation
- Enables future cross-cutting concern tooling

**Implementation**:
- Single-element list minimum (e.g., `["database"]`)
- Multi-element lists for cross-domain modules (e.g., `["cli", "interface"]`)
- Package level: `__domains__ = ["domain1", "domain2", ...]`

## ADR-008: Public API Definition with `__all__`

**Status**: ACCEPTED

**Decision**: Explicitly define module public APIs using `__all__`.

**Rationale**:
- Makes public/private boundaries clear
- Supports IDE autocompletion
- Documents intended API surface
- Enables tools like type checkers to validate exports

**Implementation**:
- Every module has `__all__` listing public exports
- Functions, classes, constants included if part of public API
- Private functions (leading underscore) excluded

## ADR-009: Configuration Validation Strategy

**Status**: ACCEPTED

**Decision**: Validate configuration at load time with comprehensive error reporting rather than lazy validation.

**Rationale**:
- Fails fast with clear error messages
- Prevents invalid states from propagating
- Validation errors include context for debugging
- Single validation point maintains consistency

**Implementation**:
- `_validate_config()` function validates all configuration
- Called in `load_config()` after all sources merged
- Validates: types, ranges, allowed values
- Raises `ConfigValidationError` with context dict

## ADR-010: Enhanced Error Logging with Context

**Status**: ACCEPTED

**Decision**: Add contextual information to error logs using logging `extra` parameter.

**Rationale**:
- Structured logging enables better analysis
- Context helps debugging without code changes
- Low overhead with proper logger configuration
- Industry best practice

**Implementation**:
- Add `extra` dict with relevant context to logger calls
- Examples: `statement_count`, `error_type`, `engine_type`
- All errors logged with `exc_info=True` for tracebacks

## ADR-011: Separation of Concerns: CLI vs API

**Status**: ACCEPTED

**Decision**: Keep CLI and API entry points separate with clear boundaries.

**Rationale**:
- `main.py` provides programmatic API (`process_sql`, `process_sql_files`)
- `cli.py` provides command-line interface
- API layer raises domain exceptions for client handling
- CLI layer catches and translates to user-friendly messages

**Implementation**:
- Main functions in `main.py` don't use `print()`
- CLI in `cli.py` catches exceptions and prints
- Different logging levels by layer
- Exit codes distinct from exception types

## ADR-012: Type Safety with mypy Strict Mode

**Status**: ACCEPTED

**Decision**: Maintain strict mypy compliance and use modern Python type syntax.

**Rationale**:
- Catches type errors at development time
- PEP 604 syntax (`X | Y`) cleaner than `Union`
- PEP 585 syntax (built-in generics) simpler than `typing` module
- Supports Python 3.10+ targets

**Implementation**:
- All function/method signatures have type annotations
- Use `X | Y` instead of `Union[X, Y]`
- Use `list[X]` instead of `List[X]`
- mypy configuration enforces strict mode

---

## Future Considerations

### Security Enhancement
- Add audit logging for security validation results
- Implement rate limiting for API consumers
- Add request signing capability

### Performance Optimization
- Connection pooling improvements
- Query result caching strategy
- Batch processing optimizations

### Testing Coverage
- Increase integration test coverage
- Add performance benchmarks
- Implement chaos engineering tests

### Observability
- Add OpenTelemetry instrumentation
- Implement distributed tracing
- Add metrics collection

