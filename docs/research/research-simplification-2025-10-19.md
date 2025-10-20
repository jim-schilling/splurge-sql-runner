# Research: splurge-sql-runner Package Simplification and Consistency Review

**Date**: October 19, 2025  
**Scope**: Code review, architecture analysis, consistency evaluation, and brittleness identification  
**Current Branch**: `chore/simplification`

## Executive Summary

This analysis reviews the `splurge-sql-runner` package (v2025.5.0) to identify opportunities for:
- **Simplification**: Reducing complexity without sacrificing functionality
- **Consistency**: Aligning patterns, naming conventions, and architectural approaches
- **Robustness**: Removing brittleness and improving reliability
- **Maintainability**: Improving code clarity and reducing cognitive load

The package demonstrates good architectural principles but contains opportunities for targeted improvements that would enhance developer experience and reduce maintenance burden.

---

## Current State Assessment

### Strengths
1. **Sound Package Structure**: Clear separation of concerns with dedicated modules for CLI, database, configuration, security, and logging
2. **Modern Python**: Type hints, f-strings, PEP 8 compliance, CalVer versioning
3. **Comprehensive Testing**: Unit, integration, and e2e tests with pytest markers
4. **Security-Forward Design**: Risk-based validation with configurable security levels
5. **Configuration Flexibility**: Multiple sources (JSON, environment, CLI) with intelligent precedence
6. **Error Handling**: Domain-specific exceptions with context support
7. **Development Practices**: Pre-commit hooks, mypy validation, ruff linting

### Implementation Status from Previous Phase
The previous simplification phase (2025-10-15) successfully:
- ✅ Flattened configuration from complex nested objects to simple dictionaries
- ✅ Consolidated error types (30+ errors → 20+ organized hierarchy)
- ✅ Implemented risk-based security (3 levels: strict, normal, permissive)
- ✅ Streamlined database client (removed connection pooling complexities for SQLite)
- ✅ Simplified main entry points

---

## Detailed Findings and Recommendations

### 1. Configuration System (Partially Improved)

#### Current State
The configuration system (`config.py` and constants) has been simplified from the previous complex object model to a flat dictionary approach. However, there are still opportunities for further optimization.

**File**: `splurge_sql_runner/config.py` (~160 lines)

**Positive Aspects**:
- ✅ Clean function-based API: `load_config()`, `get_default_config()`, `get_env_config()`
- ✅ Environment variables properly prefixed (`SPLURGE_SQL_RUNNER_*`)
- ✅ Simple JSON parsing with fallback to defaults
- ✅ Clear separation of concerns (default → file → env precedence)

**Improvement Opportunities**:

1. **Reduce Config Keys**: Current config supports 8 keys - could be consolidated
   - Consider: `max_statements_per_file` could be named `max_statements` (less verbose)
   - Consider: `enable_verbose` + `enable_debug` could be `log_level` only
   - Current structure: works, but could be tighter

2. **Simplify JSON Parsing** (`_parse_json_config`):
   - The function handles nested dictionaries like `db_config["database"]["url"]`
   - Opportunity: Use a flatter JSON structure or simpler parsing approach
   - **Recommendation**: Document expected JSON schema clearly, or accept only flat top-level keys

3. **Error Handling**: `load_json_config` catches multiple exception types
   - Could consolidate `SplurgeSafeIoFileNotFoundError`, `SplurgeSafeIoFilePermissionError`, `SplurgeSafeIoUnknownError` into single handler
   - **Recommendation**: Use `safe_io_exc.SplurgeSafeIoError` base class if available

4. **Missing Type Hint**: `_parse_json_config` should return `dict[str, Any]` but parameter is untyped
   ```python
   def _parse_json_config(config_data: dict[str, Any]) -> dict[str, Any]:
   ```

#### Recommendations
```python
# Simplification opportunity: Reduce verbose key names
config_keys = {
    "db_url": "sqlite:///:memory:",      # Instead of "database_url"
    "max_stmts": 100,                     # Instead of "max_statements_per_file"
    "timeout": 30.0,                      # Instead of "connection_timeout"
    "log_level": "INFO",
    "security_level": "normal",
}

# Or alternatively: consolidate verbosity flags
# Instead of "enable_verbose" + "enable_debug" → use log_level: DEBUG|INFO|WARNING|ERROR
```

---

### 2. Unified Exception Hierarchy

#### Current State
**File**: `splurge_sql_runner/exceptions.py` (~170 lines)

The exception hierarchy was improved in the previous phase from ~35 errors to a consolidated hierarchy:
- Base: `SplurgeSqlRunnerError`
- Categories: Configuration, Validation, Operation, CLI, Database, Security, SQL

**Positive Aspects**:
- ✅ Context storage with `add_context()` and `get_context()` methods
- ✅ `__eq__` and `__hash__` implementation for testing
- ✅ Deep copy of context to prevent external mutation
- ✅ Proper inheritance hierarchy

**Improvement Opportunities**:

1. **Exception Proliferation**: Still 20+ exception classes - could consolidate further
   - `DatabaseConnectionError`, `DatabaseOperationError`, `DatabaseBatchError`, `DatabaseEngineError`, `DatabaseTimeoutError`, `DatabaseAuthenticationError` → Could be `DatabaseError` with context
   - `SqlParseError`, `SqlFileError`, `SqlValidationError`, `SqlExecutionError` → Could be `SqlError` with context
   - **Rationale**: Callers rarely need specific exception types; context can distinguish issues

2. **Unused Exceptions**: 
   - `CliFileError` - not referenced in codebase, replaced by `FileError`
   - Some database errors may not be actively raised

3. **Deep Copy Overhead** (`__init__`):
   - Context is deep-copied on every exception creation
   - Most exceptions are raised once, not reused
   - **Recommendation**: Use shallow copy or reference for performance

4. **No __repr__**: Makes debugging harder in logs
   ```python
   def __repr__(self) -> str:
       return f"{self.__class__.__name__}({self.message!r})"
   ```

#### Recommendations
```python
# Option A: Keep specific types but reduce count
# Keep: FileError, DatabaseError, SecurityError, SqlError, CliError
# Move details into context:
#   raise DatabaseError("Connection failed", context={"error_type": "auth", "db": "postgres"})

# Option B: Analysis - count actual usage
# Recommendation: Audit which exception types are actually caught/handled by callers
```

---

### 3. CLI Architecture

#### Current State
**File**: `splurge_sql_runner/cli.py` (~230 lines)

**Positive Aspects**:
- ✅ Clear entry point with `main()` function
- ✅ Comprehensive argument parsing
- ✅ Helpful error messages and guidance
- ✅ Proper exit codes (0, 1, 2, 3)
- ✅ UTF-8 encoding handling

**Improvement Opportunities**:

1. **Tight Coupling Between Main Logic and CLI**:
   - The main() function performs:
     - Argument parsing ✓
     - Configuration loading ✓
     - File discovery/globbing ✓
     - SQL execution ✓
     - Result formatting ✓
     - Error handling ✓
   - Violation of Single Responsibility Principle
   - **Recommendation**: Extract file discovery and orchestration to separate functions

2. **String Constants Not Centralized**:
   ```python
   _ERROR_PREFIX: str = "ERROR:"           # Lines 52, 67
   _SUCCESS_PREFIX: str = "SUCCESS:"       # Line 81  
   _WARNING_PREFIX: str = "WARNING:"       # Line 83
   ```
   - Used scattered throughout
   - **Recommendation**: Define in module constants at top

3. **Complex Error Message Formatting** (`_print_security_guidance`):
   - 40 lines for security guidance
   - Contains hardcoded strings and context-dependent logic
   - **Recommendation**: Move to security module or use structured guidance dictionary

4. **File Globbing Logic** (~12 lines):
   ```python
   pattern = str(Path(args.pattern).expanduser())
   files_to_process = [str(Path(p).resolve()) for p in glob.glob(pattern)]
   ```
   - Could be extracted to function
   - No sorting guarantee (already added sort() - good catch)
   - **Recommendation**: Extract to `discover_files(pattern: str) -> list[str]` function

5. **Result Processing Logic**:
   ```python
   for fp, results in summary.get("results", {}).items():
       pretty_print_results(results, fp, output_json=args.output_json)
   ```
   - Intermingled with exit code logic
   - **Recommendation**: Separate result processing from orchestration

6. **Inconsistent Logging**:
   - Configure module logging early: `logger = configure_module_logging(...)`
   - Then reconfigure after setup_logging: `logger = configure_module_logging(...)`
   - **Recommendation**: Configure once or use consistent approach

#### Recommendations
```python
# Extract core responsibilities:
def discover_files(file_path: str | None, pattern: str | None) -> list[str]:
    """Discover SQL files to process."""
    if file_path:
        return [Path(file_path).expanduser().resolve().as_posix()]
    if pattern:
        expanded = str(Path(pattern).expanduser())
        files = [str(Path(p).resolve()) for p in glob.glob(expanded)]
        return sorted(files)
    return []

def report_results(summary: dict, output_json: bool) -> None:
    """Display execution results."""
    for fp, results in summary.get("results", {}).items():
        pretty_print_results(results, fp, output_json=output_json)

# Extract error guidance:
SECURITY_GUIDANCE = {
    "too_many_statements": "Tip: increase --max-statements",
    "too_long": "Tip: increase max_statement_length config",
    # ...
}
```

---

### 4. Database Client

#### Current State
**File**: `splurge_sql_runner/database/database_client.py` (~229 lines)

**Positive Aspects**:
- ✅ Simplified from previous version
- ✅ Handles SQLite vs other databases appropriately (no pooling for SQLite)
- ✅ Proper transaction management (BEGIN/COMMIT/ROLLBACK)
- ✅ Distinction between FETCH and EXECUTE statements
- ✅ Context managers for connections

**Improvement Opportunities**:

1. **Method Bloat**: `execute_sql()` is 80+ lines handling two modes
   - `stop_on_error=True`: Single transaction, rollback on first error
   - `stop_on_error=False`: Individual transactions per statement
   - **Recommendation**: Split into two methods or create helper

2. **Statement Type Detection Duplication**:
   ```python
   stmt_type = detect_statement_type(stmt)
   if stmt_type == FETCH_STATEMENT:  # Line 103
       # ... fetch logic
   else:
       # ... execute logic
   ```
   - Done for every statement in loop
   - Could cache result
   - **Recommendation**: Cache `(stmt, type)` pairs or detect batch

3. **Error Messages Lack Context**:
   ```python
   raise DatabaseError(f"Failed to create database engine: {exc}") from exc
   ```
   - No context about the URL, statement, etc.
   - **Recommendation**: Add context dict

4. **Incomplete Logic** (lines 151-229 truncated):
   - Need to review full `stop_on_error=False` branch
   - May have duplicated logic

5. **Connection State Management**:
   - `_engine` is cached but never cleared
   - Multiple `connect()` calls reuse same engine
   - **Recommendation**: Add `close()` method to properly dispose engine

6. **Unused Parameters**:
   - `pool_size`, `max_overflow`, `pool_pre_ping` accepted in `__init__` but not used for SQLite
   - **Recommendation**: Remove or document clearly

#### Recommendations
```python
# Extract method to reduce complexity
def _execute_single_transaction(
    self, 
    conn: Connection, 
    statements: list[str]
) -> list[dict[str, Any]]:
    """Execute all statements in single transaction."""
    # 40-50 lines
    
def _execute_separate_transactions(
    self,
    conn: Connection,
    statements: list[str]
) -> list[dict[str, Any]]:
    """Execute each statement in separate transaction."""
    # 30-40 lines

# Add close method
def close(self) -> None:
    """Close database connection and dispose engine."""
    if self._engine:
        self._engine.dispose()
        self._engine = None
```

---

### 5. Security Validator

#### Current State
**File**: `splurge_sql_runner/security.py` (~140 lines)

**Positive Aspects**:
- ✅ Risk-based security levels (strict, normal, permissive)
- ✅ Separate patterns for different threat levels
- ✅ Validation for URLs, SQL content, and file paths
- ✅ Clear error messages

**Improvement Opportunities**:

1. **Pattern Duplication**: Three levels with mostly similar patterns
   ```python
   STRICT_PATTERNS = {...}      # ~15 items
   NORMAL_PATTERNS = {...}      # ~5 items  
   PERMISSIVE_PATTERNS = {...}  # ~1 item
   ```
   - Opportunity: Use inheritance or composition
   - **Recommendation**: Define base patterns and override specific ones

2. **Validation Logic Scattered**:
   - `validate_database_url()`: URL-specific
   - `validate_sql_content()`: SQL-specific
   - No file path validation in this class (exists elsewhere?)
   - **Recommendation**: Rename class to `SqlSecurityValidator` or add file validation

3. **Lazy Import**:
   ```python
   from splurge_sql_runner.sql_helper import parse_sql_statements  # Line 129
   ```
   - Inside method to avoid circular imports
   - Already done (good), but indicates architecture issue
   - **Recommendation**: Document why circular import exists

4. **Regex Patterns Actually String Matching**:
   - Despite name (patterns), code uses `.upper() in` string matching
   - Not using regex
   - **Recommendation**: Rename from "PATTERNS" to "KEYWORDS" or "PHRASES"

5. **Performance**: Statement parsing called on every validation
   ```python
   statements = parse_sql_statements(sql_content)  # Parses entire content
   if len(statements) > max_statements:
   ```
   - Could validate count differently (count semicolons as heuristic first)
   - **Recommendation**: Add fast-path count check before full parse

#### Recommendations
```python
# Restructure patterns
class SqlSecurityValidator:
    BASE_KEYWORDS = {
        "sql": ["DROP", "EXEC", "EXECUTE"],
        "url": ["script:", "javascript:"],
    }
    
    STRICT_KEYWORDS = {
        "sql": BASE_KEYWORDS["sql"] + ["BACKUP", "RESTORE", "SHUTDOWN"],
        "url": BASE_KEYWORDS["url"] + ["--", "/*"],
    }

# Rename: validate_database_url → validate_url
#         validate_sql_content → validate_sql

# Add fast-path:
def _count_statements_fast(sql: str) -> int:
    """Quick heuristic: count semicolons."""
    return sql.count(";")
```

---

### 6. Main Entry Point

#### Current State
**File**: `splurge_sql_runner/main.py` (~146 lines)

**Positive Aspects**:
- ✅ Clear separation between `process_sql()` and `process_sql_files()`
- ✅ Consistent function signatures
- ✅ Proper resource cleanup in try/finally
- ✅ Good documentation

**Improvement Opportunities**:

1. **Inconsistent Default Handling**:
   ```python
   if config is None:
       config = load_config(None)  # Lines 43, 79
   ```
   - Works but repeated twice
   - **Recommendation**: Use parameter default `config: dict | None = None` with helper

2. **Function Size**: `process_sql_files()` processes logic inline
   - Iterates files, processes each, accumulates results (looks like 20+ lines, likely more in not-shown portion)
   - **Recommendation**: Extract per-file processing to `_process_single_file()` function

3. **Error Context**: Generic exception handling
   ```python
   except Exception as e:
       summary["results"][fp] = [{"error": f"Unexpected error processing file {fp}: {e}"}]
   ```
   - Loses exception information, exc_info, traceback
   - **Recommendation**: Log with `exc_info=True`

4. **Summary Dict Keys**: Magic strings used throughout
   ```python
   summary["files_processed"] = 0
   summary["files_passed"] = 0
   # ...
   summary.get("success_count", 0)
   ```
   - Inconsistent keys used: `success_count` vs `files_passed`
   - **Recommendation**: Use TypedDict or dataclass

5. **Statement Type Detection in Summary**:
   ```python
   batch_passed = all(r.get("statement_type") != "error" for r in results)
   batch_failed = all(r.get("statement_type") == "error" for r in results)
   ```
   - Three states but only checks two conditions
   - What if one passes, one fails? (sets `files_mixed`)
   - **Recommendation**: Clarify logic or use enum

#### Recommendations
```python
from typing import TypedDict

class ProcessingSummary(TypedDict):
    files_processed: int
    files_passed: int
    files_failed: int
    files_mixed: int
    results: dict[str, list[dict[str, Any]]]

def _process_single_file(
    file_path: str,
    database_url: str,
    config: dict,
    security_level: str,
    max_statements: int,
    stop_on_error: bool,
) -> tuple[list[dict[str, Any]], str]:  # (results, status: "passed"|"failed"|"mixed")
    """Process single file and return results with status."""
```

---

### 7. SQL Helper Module

#### Current State
**File**: `splurge_sql_runner/sql_helper.py` (~430+ lines based on file listing)

**Key Areas**:
- SQL parsing (sqlparse-based)
- Statement type detection
- Comment removal
- Caching (via `@lru_cache`)

**Observations** (without full content read):
- Uses `lru_cache` for performance - good
- Handles comments properly
- Type detection for FETCH vs EXECUTE

**Likely Improvements**:
1. May have duplicated utility functions
2. Possibly inconsistent with comment removal approaches
3. Error handling for malformed SQL

---

### 8. Import Organization and Consistency

#### Current State
Throughout the codebase:

**Observations**:
- Imports generally follow guideline: standard → third-party → local
- Some inconsistency in relative vs absolute imports
- Some modules have local/delayed imports to avoid circular dependencies

**Issues Found**:

1. **Circular Import Pattern**:
   - `security.py` delays import of `sql_helper`
   - `main.py` imports from `security`, `sql_helper`, `config`
   - Structure allows but indicates tight coupling

2. **`__all__` Inconsistency**:
   - `cli.py` has `__all__` (~3 items)
   - `main.py` missing `__all__`
   - `security.py` missing `__all__`
   - `database_client.py` missing `__all__`

3. **Star Imports in `__init__.py`**:
   ```python
   from splurge_sql_runner.logging import (
       ContextualLogger,
       # ... many imports
   )
   ```
   - All required and explicit - good
   - Could use star import if logging module had `__all__`

#### Recommendations
```python
# Add __all__ to modules without it
# security.py
__all__ = ["SecurityValidator"]

# main.py
__all__ = ["process_sql", "process_sql_files"]

# database_client.py
__all__ = ["DatabaseClient"]

# Refactor circular imports by moving to separate module:
# splurge_sql_runner/validation.py (combines security + sql parsing)
```

---

### 9. Naming Conventions and Consistency

#### Current State
Review of naming across codebase:

**Positive**:
- ✅ Consistent snake_case for functions/variables
- ✅ Consistent PascalCase for classes
- ✅ Consistent UPPER_SNAKE_CASE for constants
- ✅ Proper use of auxiliary verbs: `is_*`, `has_*`, `get_*`

**Inconsistencies Found**:

1. **Prefix Inconsistency**:
   - `_error_prefix` (private variable, but public constant)
   - `_ERROR_PREFIX` (correct approach)
   - `_print_security_guidance()` (private function, correct)
   - BUT in `cli.py` lines 52-56: Constants defined with underscores then used as public constants
   - **Recommendation**: Define at module level without leading underscore if used as constants

2. **Parameter Naming**:
   - `config` → sometimes `config_dict`, sometimes `config_data`
   - `connection` → sometimes `conn`
   - **Recommendation**: Standardize: use full names in signatures, short names in bodies

3. **Abbreviation Usage**:
   - `db_url` vs `database_url` (both used in different modules)
   - `stmt` vs `statement`
   - `fp` vs `file_path`
   - **Recommendation**: Establish conventions per module or globally

#### Recommendations
```python
# Standardize abbreviations document in copilot-instructions:
# Guidelines:
# - Use full names in public APIs
# - Use abbreviations in loop variables/local scopes:
#   - db_url (internal)
#   - stmt (internal)  
#   - fp (file path, internal)
# - Consistent: database_url (public), db_url (internal)
```

---

### 10. Error Recovery and Brittleness

#### Current State
Areas of potential brittleness:

1. **File Operations**:
   - Uses `SafeTextFileReader` from `splurge_safe_io` (good)
   - But doesn't handle encoding errors explicitly
   - Large files not handled (memory considerations)

2. **Configuration Loading**:
   ```python
   try:
       reader = SafeTextFileReader(config_file_path, encoding="utf-8")
       json_config = json.loads(reader.read())
   except ...:
       pass  # Use defaults if JSON loading fails
   ```
   - Silently fails - might be desired, but unclear intent
   - **Recommendation**: Document or log why failing silently

3. **Database Connections**:
   - No connection retry logic
   - No timeout handling for long-running queries
   - Connection pool not configured for non-SQLite

4. **Pattern Matching**:
   - Security validation uses string matching (`.upper() in`)
   - Could have false positives/negatives
   - No regex = less precise but simpler

5. **Missing Validation**:
   - No check for empty SQL files
   - No check for file permissions before execution
   - No check for database availability before starting

#### Recommendations
```python
# Add retry logic:
def connect_with_retry(
    database_url: str, 
    timeout: float = 30.0,
    max_retries: int = 3
) -> Connection:
    """Connect with exponential backoff retry."""
    
# Add logging for silent failures:
logger.debug(f"Failed to load config from {config_file_path}, using defaults")

# Add validations:
def validate_prerequisites(files: list[str], db_url: str) -> None:
    """Validate files exist and DB is accessible."""
    for f in files:
        if not Path(f).exists():
            raise FileError(f"File not found: {f}")
    # Test database connection
```

---

### 11. Testing Structure (Based on Copilot Instructions)

#### Current State
According to copilot-instructions.md, expected structure:
- `tests/unit/` - unit tests (target: 85% coverage)
- `tests/integration/` - integration tests
- `tests/e2e/` - end-to-end tests
- `tests/data/` - test data

Test markers defined:
- unit, integration, e2e
- slow, database, security, performance
- critical, essential, important, nice_to_have
- fast, medium, in_memory

**Questions for Review**:
1. Are all modules having `test_*` prefix files?
2. Coverage level at 85%?
3. Are test names following pattern `test_[condition]_[expectedResult]`?
4. Module tests named `test_[module_path]_basic.py`?

**Recommendations**:
- Audit test coverage against guidelines
- Ensure all public APIs have tests
- Consider performance: tests should complete in 60-120s total

---

## Summary Table: Improvement Opportunities

| Area | Severity | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Configuration key consolidation | Low | Low | Medium | Not Started |
| Exception type reduction | Low | Low | High | Not Started |
| CLI method extraction | Medium | Medium | High | Not Started |
| Database client simplification | Medium | Medium | High | Not Started |
| Security pattern refactoring | Low | Low | Medium | Not Started |
| Main.py orchestration | Low | Low | Medium | Not Started |
| __all__ consistency | Low | Low | Low | Not Started |
| Naming standardization | Low | Medium | Medium | Not Started |
| Error recovery enhancement | Medium | Medium | High | Not Started |
| File operation robustness | Medium | Medium | High | Not Started |
| Test coverage audit | Medium | High | High | Not Started |
| Circular import resolution | Medium | High | Medium | Not Started |

---

## Recommended Implementation Priorities

### Phase 1: High-Impact, Low-Effort (Quick Wins)
1. Add `__all__` to modules without it
2. Standardize naming conventions (prefixes, abbreviations)
3. Consolidate string constants in CLI module
4. Extract CLI helper functions

### Phase 2: Medium-Impact, Medium-Effort (Core Improvements)
1. Simplify exception hierarchy further
2. Refactor database client `execute_sql()`
3. Optimize security validation performance
4. Add logging to silent failure paths

### Phase 3: High-Impact, Higher-Effort (Architectural)
1. Resolve circular imports
2. Implement structured result types (TypedDict/dataclass)
3. Add retry logic and error recovery
4. Conduct full test coverage audit

### Phase 4: Long-Term Maintainability
1. Document architectural decisions
2. Create code style guide for the project
3. Establish performance benchmarks
4. Build compatibility matrix for databases

---

## Key Metrics for Success

If these recommendations are implemented:

- **Cognitive Load**: Reduce complex functions to <50 lines
- **Test Suite**: Should complete in <120 seconds
- **Documentation**: All public APIs documented with examples
- **Consistency**: Zero naming inconsistencies in codebase
- **Robustness**: All file operations have explicit error handling
- **Maintainability**: New developer can understand core flow in <2 hours

---

## Conclusion

The `splurge-sql-runner` package is well-designed with good foundational practices. The previous simplification phase (2025-10-15) successfully reduced complexity from earlier iterations. This follow-up analysis identifies targeted improvements in:

1. **Consistency**: Naming, imports, and patterns should align across modules
2. **Robustness**: Error handling and validation could be more explicit
3. **Simplification**: A few remaining complex functions could be refactored
4. **Maintainability**: Documentation and structure could be enhanced

Recommended approach: Implement Phase 1 immediately (quick wins), then assess impact before proceeding to subsequent phases. The package is already production-ready; these improvements are for long-term maintainability and developer experience.

---

## Appendix: Quick Reference for Developers

### Naming Conventions to Use
```
Configuration keys:  db_url, max_stmts, timeout, log_level, security_level
Local variables:     stmt (statement), fp (file_path), conn (connection)
Public APIs:         database_url, max_statements_per_file, execute_sql()
Constants:           DEFAULT_TIMEOUT, MAX_STATEMENTS_PER_FILE
```

### Module __all__ Exports
- Should include: All public classes, functions, and constants
- Should exclude: Internal utilities, private functions, test helpers

### Error Handling Pattern
```python
try:
    # operation
except SpecificError as e:
    logger.error(f"Failed: {e}", exc_info=True)
    raise
except Exception as e:
    logger.error(f"Unexpected: {e}", exc_info=True)
    raise SplurgeSqlRunnerError(f"Unexpected error: {e}") from e
```

### Configuration Pattern
```python
config = load_config(config_file)  # Merges file + env
config["db_url"] = args.connection  # CLI override
# Use config dict directly, no object wrapper
```

---

*Document generated: October 19, 2025*  
*Analysis branch: chore/simplification*  
*Next review: Upon completion of Phase 1 improvements*
