# Implementation Plan: splurge-sql-runner Simplification and Modernization

**Date**: October 19, 2025  
**Branch**: `chore/simplification`  
**Target Completion**: 4-6 weeks  
**Research Basis**: 
- `research-simplification-2025-10-19.md` (11 improvement areas)
- `research-file-io-adapter-2025-10-19.md` (FileIoAdapter pattern)

---

## Executive Summary

This plan outlines a phased approach to improve the `splurge-sql-runner` package across four dimensions:

1. **File I/O Architecture** - Centralize error handling and enable large file support
2. **Core Simplification** - Reduce complexity in configuration, exceptions, and CLI
3. **Consistency** - Standardize naming, imports, and patterns
4. **Robustness** - Add error recovery, validation, and monitoring

The implementation maintains backward compatibility and can be executed incrementally.

---

## Phase 1: File I/O Architecture (1-2 weeks)

### Goal
Centralize file I/O error handling and create foundation for large file support.

### Tasks

#### Task 1.1: Create FileIoAdapter Module
**File**: `splurge_sql_runner/utils/file_io_adapter.py` (NEW)

**Deliverables**:
- [ ] `FileIoAdapter` class with static methods
- [ ] `read_file()` - full content read with error translation
- [ ] `read_file_chunked()` - streaming read for large files
- [ ] Error context mapping (config, sql, generic types)
- [ ] Logging integration

**Acceptance Criteria**:
- All `SplurgeSafeIo*` exceptions translated to domain `FileError`
- Context dict includes file_path, context_type, operation
- No uncaught exceptions escape adapter
- API is intuitive for callers

**Code Sketch**:
```python
from typing import Iterator
from splurge_safe_io import SafeTextFileReader
import splurge_safe_io.exceptions as safe_io_exc

class FileIoAdapter:
    """Wraps SafeTextFileReader with domain error translation."""
    
    @staticmethod
    def read_file(
        file_path: str,
        encoding: str = "utf-8",
        context_type: str = "generic",
    ) -> str:
        """Read entire file content with error translation.
        
        Args:
            file_path: Path to file to read
            encoding: Character encoding (default: utf-8)
            context_type: "config", "sql", or "generic" for error context
            
        Returns:
            File content as string
            
        Raises:
            FileError: If file cannot be read (wraps SplurgeSafeIo* errors)
        """
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            return reader.read()
        except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
            raise FileError(
                f"File not found: {file_path}",
                context={"file_path": file_path, "context_type": context_type}
            ) from e
        # ... handle other exceptions
    
    @staticmethod
    def read_file_chunked(
        file_path: str,
        encoding: str = "utf-8",
        context_type: str = "generic",
    ) -> Iterator[list[str]]:
        """Yield chunks of lines from file.
        
        Args:
            file_path: Path to file to read
            encoding: Character encoding
            context_type: "config", "sql", or "generic"
            
        Yields:
            Lists of lines (each <= 1000 lines per chunk)
            
        Raises:
            FileError: If file cannot be read
        """
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            for chunk in reader.readlines_as_stream():
                yield chunk
        except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
            # ... raise FileError
```

**Testing**:
- `tests/unit/test_file_io_adapter_basic.py`
  - [ ] test_read_file_existing_file_returns_content
  - [ ] test_read_file_missing_file_raises_file_error
  - [ ] test_read_file_permission_denied_raises_file_error
  - [ ] test_read_file_invalid_encoding_raises_file_error
  - [ ] test_read_file_chunked_yields_lists_of_strings
  - [ ] test_read_file_chunked_missing_file_raises_file_error
  - [ ] test_error_context_includes_file_path
  - [ ] test_context_type_preserved_in_error

---

#### Task 1.2: Migrate config.py to Use FileIoAdapter
**File**: `splurge_sql_runner/config.py` (MODIFY)

**Changes**:
```python
# OLD (lines 118-128)
def load_json_config(file_path: str) -> dict[str, Any]:
    try:
        reader = SafeTextFileReader(file_path, encoding="utf-8")
        config_data = json.loads(reader.read())
        return _parse_json_config(config_data)
    except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
        raise ConfigFileError(f"Configuration file not found: {file_path}") from e
    except safe_io_exc.SplurgeSafeIoFilePermissionError as e:
        raise ConfigFileError(f"Permission denied reading config file: {file_path}") from e
    except safe_io_exc.SplurgeSafeIoUnknownError as e:
        raise ConfigFileError(f"Unknown error reading config file: {file_path}") from e
    except json.JSONDecodeError as e:
        raise ConfigFileError(f"Invalid JSON in config file: {e}") from e
    except Exception as e:
        raise ConfigFileError(f"Failed to read config file: {e}") from e

# NEW
def load_json_config(file_path: str) -> dict[str, Any]:
    try:
        content = FileIoAdapter.read_file(file_path, context_type="config")
        config_data = json.loads(content)
        return _parse_json_config(config_data)
    except FileError as e:
        raise ConfigFileError(f"Failed to read config file: {e}") from e
    except json.JSONDecodeError as e:
        raise ConfigFileError(f"Invalid JSON in config file: {e}") from e
```

**Benefit**: Removes 8 lines of error handling duplication

**Acceptance Criteria**:
- [ ] Import added at top: `from splurge_sql_runner.utils.file_io_adapter import FileIoAdapter`
- [ ] Removed direct `SafeTextFileReader` import
- [ ] All exception handling consolidated
- [ ] Tests still pass

---

#### Task 1.3: Migrate main.py to Use FileIoAdapter
**File**: `splurge_sql_runner/main.py` (MODIFY)

**Changes**:
```python
# OLD (lines 110-111)
reader = SafeTextFileReader(fp)
content = reader.read()

# NEW
content = FileIoAdapter.read_file(fp, context_type="sql")
```

**Updates to error handling** (lines 119-125):
```python
# OLD
except Exception as e:
    summary["results"][fp] = [{"error": f"Unexpected error processing file {fp}: {e}"}]

# NEW - Let FileError propagate from FileIoAdapter
# (SecurityValidationError already re-raised)
# Other exceptions caught and reported in summary
```

**Benefit**: Cleaner error handling, consistent with config.py

**Acceptance Criteria**:
- [ ] FileIoAdapter import added
- [ ] SafeTextFileReader import removed
- [ ] Error handling simplified
- [ ] File path errors now include context
- [ ] All existing tests pass

---

#### Task 1.4: Migrate sql_helper.py to Use FileIoAdapter
**File**: `splurge_sql_runner/sql_helper.py` (MODIFY)

**Changes**:
```python
# OLD (lines 449-450) - in read_sql_file function
reader = SafeTextFileReader(file_path, encoding="utf-8")
return reader.read()

# NEW
return FileIoAdapter.read_file(file_path, context_type="sql")
```

**Remove imports**:
- [ ] Remove `import splurge_safe_io.exceptions as safe_io_exc`
- [ ] Remove `from splurge_safe_io.safe_text_file_reader import SafeTextFileReader`

**Add imports**:
- [ ] Add `from splurge_sql_runner.utils.file_io_adapter import FileIoAdapter`

**Benefit**: Consistency across codebase, ~4 lines removed

**Acceptance Criteria**:
- [ ] FileIoAdapter used consistently
- [ ] No direct SafeTextFileReader usage in sql_helper
- [ ] Error handling works as before
- [ ] Tests pass

---

#### Task 1.5: Update __init__.py to Export FileIoAdapter
**File**: `splurge_sql_runner/__init__.py` (MODIFY)

**Changes**:
- [ ] Add to imports: `from splurge_sql_runner.utils.file_io_adapter import FileIoAdapter`
- [ ] Add to `__all__`: `"FileIoAdapter"`
- [ ] Document in public API

**Acceptance Criteria**:
- [ ] FileIoAdapter importable from package root
- [ ] Documented in __all__
- [ ] Type annotations correct

---

#### Phase 1 Success Criteria
- [ ] FileIoAdapter module created and tested (8+ tests)
- [ ] All 4 files migrated (config, main, sql_helper, __init__)
- [ ] All existing tests pass (100% pass rate)
- [ ] No regressions in error handling
- [ ] Code coverage maintained

---

## Phase 2: Core Simplification (2-3 weeks)

### Goal
Reduce complexity in core modules and improve consistency.

### Tasks

#### Task 2.1: Consolidate CLI String Constants
**File**: `splurge_sql_runner/cli.py` (MODIFY, lines 52-56)

**Before**:
```python
_ERROR_PREFIX: str = "ERROR:"
_SUCCESS_PREFIX: str = "SUCCESS:"
_WARNING_PREFIX: str = "WARNING:"
```

**After** (move to module-level with better organization):
```python
# Output formatting constants
ERROR_PREFIX = "ERROR:"
WARNING_PREFIX = "WARNING:"
SUCCESS_PREFIX = "SUCCESS:"

# Consolidated security guidance messages
SECURITY_GUIDANCE = {
    "too_many_statements": "Tip: increase --max-statements",
    "too_long": "Tip: increase max_statement_length in config",
    "file_extension": "Tip: update security.allowed_file_extensions in config",
    "dangerous_pattern_file": "Tip: rename file/path or adjust dangerous_path_patterns",
    "dangerous_pattern_url": "Tip: correct URL or adjust dangerous_url_patterns",
    "dangerous_pattern_sql": "Tip: remove pattern or adjust dangerous_sql_patterns",
    "missing_scheme": "Tip: include scheme like sqlite://, postgresql://, mysql://",
}
```

**Refactor `_print_security_guidance()`** (lines 29-48):
```python
def print_security_guidance(error_message: str, context: str = "file") -> None:
    """Print actionable guidance for security validation errors.
    
    Args:
        error_message: The error message
        context: "file", "sql", or "url"
    """
    msg_lower = error_message.lower()
    hints = []
    
    if "too many" in msg_lower:
        hints.append(SECURITY_GUIDANCE["too_many_statements"])
    if "too long" in msg_lower:
        hints.append(SECURITY_GUIDANCE["too_long"])
    # ... use dict lookups instead of if chains
    
    for hint in hints:
        print(f"{WARNING_PREFIX} {hint}")
```

**Benefit**: Reduces visual clutter, easier to maintain guidance messages

**Acceptance Criteria**:
- [ ] Constants at module top with clear naming (no leading underscore)
- [ ] Guidance messages in dict for easy maintenance
- [ ] Function uses dict lookups instead of nested ifs
- [ ] All tests pass
- [ ] No functional changes

---

#### Task 2.2: Extract CLI Helper Functions
**File**: `splurge_sql_runner/cli.py` (MODIFY, lines 160-200)

**Create new functions**:

```python
def discover_files(
    file_path: str | None,
    pattern: str | None,
) -> list[str]:
    """Discover SQL files to process.
    
    Args:
        file_path: Single file to process
        pattern: Glob pattern to match multiple files
        
    Returns:
        Sorted list of absolute file paths
        
    Raises:
        FileError: If no files found or paths invalid
    """
    if file_path:
        path_obj = Path(file_path).expanduser().resolve()
        if not path_obj.exists():
            raise FileError(f"File not found: {path_obj}")
        return [str(path_obj)]
    
    if pattern:
        expanded = str(Path(pattern).expanduser())
        files = [str(Path(p).resolve()) for p in glob.glob(expanded)]
        if not files:
            raise FileError(f"No files found matching pattern: {pattern}")
        return sorted(files)
    
    return []


def report_execution_summary(summary: dict[str, Any], verbose: bool = False) -> None:
    """Display execution summary and results.
    
    Args:
        summary: Processing summary from process_sql_files()
        verbose: Whether to print detailed file-by-file results
    """
    for fp, results in summary.get("results", {}).items():
        pretty_print_results(results, fp, output_json=False)
    
    files_processed = summary.get("files_processed", 0)
    files_passed = summary.get("files_passed", 0)
    files_failed = summary.get("files_failed", 0)
    
    print(f"\n{'=' * 60}")
    print(f"Summary: {files_passed}/{files_processed} files processed successfully")
    print(f"{'=' * 60}")
```

**Integrate into main()** (lines 95-145):
```python
# OLD
files_to_process = []
if args.file:
    # ... 15 lines of logic
elif args.pattern:
    # ... 10 lines of logic

# NEW
try:
    files_to_process = discover_files(args.file, args.pattern)
except FileError as e:
    logger.error(f"File discovery failed: {e}")
    print(f"{ERROR_PREFIX} {e}")
    return EXIT_CODE_FAILURE
```

**Benefit**: main() becomes more readable, functions reusable, testable

**Acceptance Criteria**:
- [ ] Helper functions have complete docstrings
- [ ] Logic extracted without behavior changes
- [ ] All tests pass
- [ ] main() reduced by ~30 lines

---

#### Task 2.3: Add __all__ to Modules Without It
**Files**: `main.py`, `security.py`, `database_client.py` (MODIFY)

**Changes**:

`main.py`:
```python
__all__ = [
    "process_sql",
    "process_sql_files",
]
```

`security.py`:
```python
__all__ = [
    "SecurityValidator",
]
```

`database/database_client.py`:
```python
__all__ = [
    "DatabaseClient",
]
```

**Benefit**: Clear public API, enables better IDE support and autocompletion

**Acceptance Criteria**:
- [ ] All public classes and functions exported
- [ ] __all__ placed after module docstring
- [ ] No functional changes

---

#### Task 2.4: Standardize Configuration Key Names
**File**: `splurge_sql_runner/config.py` (MODIFY, refactor keys)

**Current state** (8 keys):
- database_url, max_statements_per_file, connection_timeout, log_level, security_level, enable_verbose, enable_debug

**Decision point**: Defer large-scale key renames to avoid breaking changes
- Document expected key names clearly in docstrings
- Add validation that keys match expected set
- Plan major consolidation for v2026.x release

**Current approach is acceptable**: Simple dict already eliminates previous over-engineering

**Acceptance Criteria**:
- [ ] Decision documented in code comment
- [ ] Keys clearly listed in docstring
- [ ] No changes needed at this time

---

#### Task 2.5: Simplify Database Client Error Messages
**File**: `splurge_sql_runner/database/database_client.py` (MODIFY)

**Add context to exceptions** (lines 50-60, 70-75):
```python
# OLD
raise DatabaseError(f"Failed to create database engine: {exc}") from exc

# NEW
raise DatabaseError(
    f"Failed to create database engine: {exc}",
    context={
        "url": self.database_url[:20] + "..." if len(self.database_url) > 20 else self.database_url,
        "timeout": self.connection_timeout,
    }
) from exc
```

**Benefit**: Errors include diagnostic context for debugging

**Acceptance Criteria**:
- [ ] All DatabaseError raises include context dict
- [ ] Sensitive info (passwords) redacted
- [ ] Tests pass

---

#### Task 2.6: Extract Database Client Methods
**File**: `splurge_sql_runner/database/database_client.py` (MODIFY, lines 78-160)

**Split `execute_sql()` into helper methods**:

```python
def execute_sql(self, statements: list[str], *, stop_on_error: bool = True) -> list[dict]:
    """Execute SQL statements with optional error handling."""
    if not statements:
        return []
    
    conn = self.connect()
    try:
        if stop_on_error:
            return self._execute_single_transaction(conn, statements)
        else:
            return self._execute_separate_transactions(conn, statements)
    finally:
        # ... cleanup

def _execute_single_transaction(
    self,
    conn: Connection,
    statements: list[str],
) -> list[dict[str, Any]]:
    """Execute all statements in single transaction."""
    conn.exec_driver_sql("BEGIN")
    results = []
    for stmt in statements:
        # ... 40 lines of logic
    conn.exec_driver_sql("COMMIT")
    return results

def _execute_separate_transactions(
    self,
    conn: Connection,
    statements: list[str],
) -> list[dict[str, Any]]:
    """Execute each statement in its own transaction."""
    results = []
    for stmt in statements:
        # ... 30 lines of logic
    return results
```

**Benefit**: Reduced cognitive load, easier to test each path

**Acceptance Criteria**:
- [ ] Method extracted without behavior changes
- [ ] Each method <50 lines
- [ ] All tests pass
- [ ] Performance unchanged

---

#### Task 2.7: Add close() Method to DatabaseClient
**File**: `splurge_sql_runner/database/database_client.py` (ADD)

```python
def close(self) -> None:
    """Close database connection and dispose engine."""
    if self._engine is not None:
        try:
            self._engine.dispose()
            self._logger.debug("Database connection disposed")
        except Exception as e:
            self._logger.warning(f"Error disposing engine: {e}")
        finally:
            self._engine = None
```

**Update main.py** (line 68):
```python
try:
    results = db_client.execute_sql(sql_stmts, stop_on_error=stop_on_error)
    return results
finally:
    db_client.close()  # Cleaner than try/except pass
```

**Benefit**: Explicit resource cleanup, prevents connection leaks

**Acceptance Criteria**:
- [ ] Method handles engine disposal gracefully
- [ ] Logged appropriately
- [ ] main.py uses close() in finally block
- [ ] No exceptions leak from close()

---

#### Phase 2 Success Criteria
- [ ] CLI constants consolidated and documented
- [ ] Helper functions extracted and tested
- [ ] All modules have __all__ exports
- [ ] Database client split into methods
- [ ] All tests pass (100% pass rate)
- [ ] Code complexity reduced by ~10-15%

---

## Phase 3: Consistency and Robustness (2 weeks)

### Goal
Standardize patterns, add validation, improve error recovery.

### Tasks

#### Task 3.1: Standardize Naming Conventions
**Document**: Update `copilot-instructions.md` (MODIFY)

**Add new section**:
```markdown
## Project-Specific Naming Conventions

### Configuration Keys (Internal)
All configuration access uses flat dict keys:
- `database_url` - database connection string (public API)
- `max_statements_per_file` - max statements allowed (public API)
- `connection_timeout` - connection timeout in seconds (public API)
- `log_level` - logging level (public API)
- `security_level` - security validation level (public API)
- `enable_verbose` - verbose output enabled (internal)
- `enable_debug` - debug mode enabled (internal)

### Local Variable Naming
In function bodies, accept common abbreviations:
- `db_url` for database_url in loops/local scopes
- `stmt` for statement in SQL processing loops
- `fp` for file_path in file processing loops
- `conn` for connection in database operations
- `config` for configuration dict throughout

### Module Naming
- Error classes: Use domain prefix (e.g., `FileError`, `DatabaseError`)
- Adapter classes: Suffix with "Adapter" (e.g., `FileIoAdapter`)
- Utility classes: Suffix with "Helper" or use descriptive nouns
- Private functions: Prefix with underscore (e.g., `_execute_single_transaction`)

### Exception Context Keys
When adding context to exceptions, use consistent keys:
- `file_path` - path to file being processed
- `context_type` - "config", "sql", "generic", etc.
- `db_url` - database URL (redact passwords)
- `statement` - SQL statement (first 100 chars)
- `error_type` - classification of error
```

**Task 3.2: Add Input Validation**
**Files**: `main.py`, `config.py`, `security.py` (MODIFY)

**main.py** - Validate file existence upfront:
```python
def discover_files(file_path: str | None, pattern: str | None) -> list[str]:
    """Discover files with validation."""
    files = []
    
    if file_path:
        path_obj = Path(file_path).expanduser().resolve()
        if not path_obj.exists():
            raise FileError(f"File not found: {path_obj}")
        if not path_obj.is_file():
            raise FileError(f"Not a file: {path_obj}")
        if path_obj.stat().st_size == 0:
            raise FileError(f"Empty file: {path_obj}")
        files.append(str(path_obj))
    
    elif pattern:
        expanded = str(Path(pattern).expanduser())
        found = sorted(str(Path(p).resolve()) for p in glob.glob(expanded))
        if not found:
            raise FileError(f"No files found matching pattern: {pattern}")
        files = found
    
    return files
```

**Acceptance Criteria**:
- [ ] File existence checked before processing
- [ ] Empty files detected and reported
- [ ] Invalid patterns caught early
- [ ] Clear error messages

---

#### Task 3.3: Add Error Recovery Logging
**Files**: All modules with exception handling (MODIFY)

**Pattern** - Always log with exc_info:
```python
# OLD
except Exception as e:
    summary["results"][fp] = [{"error": str(e)}]

# NEW
except Exception as e:
    logger.error(f"Processing failed for {fp}", exc_info=True)
    summary["results"][fp] = [{
        "error": str(e),
        "exception_type": type(e).__name__,
    }]
```

**Acceptance Criteria**:
- [ ] All exceptions logged with exc_info=True
- [ ] Exception type included in error details
- [ ] Traceback captured for debugging

---

#### Task 3.4: Add Large File Detection
**File**: `splurge_sql_runner/utils/file_io_adapter.py` (MODIFY)

**Add size validation**:
```python
MAX_FILE_SIZE_MB = 500  # Configurable limit

@staticmethod
def validate_file_size(
    file_path: str,
    max_size_mb: int = MAX_FILE_SIZE_MB,
) -> int:
    """Validate file size before reading.
    
    Args:
        file_path: Path to file
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        File size in MB
        
    Raises:
        FileError: If file exceeds max size
    """
    size_bytes = Path(file_path).stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    
    if size_mb > max_size_mb:
        raise FileError(
            f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)",
            context={"size_mb": size_mb, "limit_mb": max_size_mb}
        )
    
    return size_mb
```

**Update main.py** to use:
```python
for fp in files_to_process:
    try:
        FileIoAdapter.validate_file_size(fp)
        content = FileIoAdapter.read_file(fp, context_type="sql")
        # ... process
```

**Acceptance Criteria**:
- [ ] Size checked before reading
- [ ] Clear error for oversized files
- [ ] Configurable limit
- [ ] Tests cover size validation

---

#### Task 3.5: Document Architectural Decisions
**New File**: `docs/architecture/decision-log-2025-10-19.md` (CREATE)

**Content**:
```markdown
# Architectural Decisions - October 2025

## ADR-001: FileIoAdapter Pattern

**Status**: Approved (October 19, 2025)

**Issue**: File I/O error handling scattered across 3 modules with duplication

**Decision**: Create `FileIoAdapter` class to:
1. Centralize error translation from SplurgeSafeIo* to domain errors
2. Provide both streaming and non-streaming APIs
3. Enable large file support without changing callers
4. Add contextual error information

**Rationale**:
- Low-cost wrapper reduces duplication
- Centralizes file I/O strategy in one place
- Enables future monitoring/metrics
- Makes testing easier with single point to mock

**Consequences**:
- One additional dependency class in utils
- Slightly different error messages (improved)
- Foundation for streaming implementation

---

## ADR-002: Configuration Consolidation

**Status**: Deferred (to v2026.x)

**Issue**: 8 configuration keys could be further consolidated

**Decision**: Keep current key names for stability

**Rationale**:
- Already improved from previous version
- Large-scale rename is breaking change
- Current dict approach is clean and maintainable
- Further consolidation can be staged for next major version

**Consequences**:
- Supports smooth migration path
- No breaking changes
- Clearer versioning strategy

---

## ADR-003: Exception Consolidation

**Status**: Partial implementation

**Issue**: Still 20+ exception types; could reduce further

**Decision**: Keep current hierarchy, but encourage context over subclass-checking

**Rationale**:
- Current hierarchy is organized and clear
- Callers rarely catch specific database exceptions
- Context dicts enable distinguishing error types without subclasses
- Reduces API surface without losing clarity

**Consequences**:
- Encourages better error handling patterns
- Smoother path to future simplification
- No immediate breaking changes

---
```

**Acceptance Criteria**:
- [ ] Architecture decisions documented
- [ ] Rationale clear for future maintainers
- [ ] Deferred decisions noted with reasoning

---

#### Phase 3 Success Criteria
- [ ] Naming conventions documented and consistent
- [ ] Input validation added at entry points
- [ ] Error recovery logging comprehensive
- [ ] Large file detection implemented
- [ ] Architecture decisions documented
- [ ] All tests pass

---

## Phase 4: Testing and Validation (1 week)

### Goal
Verify implementation completeness and ensure no regressions.

### Tasks

#### Task 4.1: Create FileIoAdapter Tests
**File**: `tests/unit/test_file_io_adapter_basic.py` (CREATE)

```python
# 8-10 test cases covering:
# ✓ read_file with existing file
# ✓ read_file with missing file (FileError)
# ✓ read_file with permission denied (FileError)
# ✓ read_file with invalid encoding (FileError)
# ✓ read_file_chunked yields lists
# ✓ read_file_chunked with missing file
# ✓ Error context includes file_path
# ✓ Error context includes context_type
# ✓ validate_file_size detects large files
# ✓ validate_file_size accepts normal files
```

**Acceptance Criteria**:
- [ ] 10+ tests, all passing
- [ ] Coverage >85%
- [ ] Each error path tested
- [ ] Context validation tested

---

#### Task 4.2: Create Integration Tests
**File**: `tests/integration/test_end_to_end_2025_10_19.py` (CREATE)

```python
# Integration tests verifying:
# ✓ Configuration loading through FileIoAdapter
# ✓ SQL file processing through FileIoAdapter
# ✓ Multi-file batch processing
# ✓ Error handling in end-to-end flow
# ✓ Large file handling (simulated)
# ✓ CLI execution with real database
```

**Acceptance Criteria**:
- [ ] 5-8 integration tests
- [ ] All passing
- [ ] Cover key workflows

---

#### Task 4.3: Regression Testing
**Execution**: Run full test suite (1-2 hours)

```bash
# Run all tests
pytest tests/ -v

# Check coverage
pytest --cov=splurge_sql_runner tests/

# Verify coverage meets 85% threshold
```

**Acceptance Criteria**:
- [ ] All tests pass (100%)
- [ ] Coverage maintained >85%
- [ ] No new warnings
- [ ] Performance unchanged

---

#### Task 4.4: Code Quality Checks
**Execution**: Run linting and type checking

```bash
# Ruff check
ruff check splurge_sql_runner/

# MyPy validation
mypy splurge_sql_runner/

# Format check
ruff format --check splurge_sql_runner/
```

**Acceptance Criteria**:
- [ ] No ruff violations
- [ ] MyPy passes with strict settings
- [ ] Code formatted correctly
- [ ] No unused imports

---

#### Task 4.5: Documentation Review
**Files**: Update if needed

- [ ] README.md reflects changes
- [ ] Docstrings complete
- [ ] Examples up-to-date
- [ ] CHANGELOG.md entry

---

#### Task 4.6: Performance Benchmarking
**Execution**: Compare performance before/after

```python
# Test with various file sizes
# ✓ Small files (< 1MB)
# ✓ Medium files (10-50MB)
# ✓ Large files (100-500MB)

# Measure:
# ✓ File read time
# ✓ Memory usage
# ✓ Error handling overhead
```

**Acceptance Criteria**:
- [ ] No performance regression
- [ ] Large file support working
- [ ] Memory usage acceptable

---

#### Phase 4 Success Criteria
- [ ] All tests passing (>400 tests expected)
- [ ] Code coverage >85%
- [ ] No code quality issues
- [ ] Performance benchmarked
- [ ] Documentation complete

---

## Implementation Timeline

### Week 1: File I/O Architecture (Phase 1)
- **Mon-Tue**: FileIoAdapter implementation (1.1)
- **Wed**: config.py migration (1.2)
- **Thu**: main.py and sql_helper.py migration (1.3-1.4)
- **Fri**: Testing and validation (1.5)

### Week 2: Core Simplification (Phase 2)
- **Mon**: CLI constants and helper functions (2.1-2.2)
- **Tue**: __all__ exports (2.3)
- **Wed**: Database client refactoring (2.5-2.6)
- **Thu**: Configuration standardization (2.4)
- **Fri**: Database close() method (2.7)

### Week 3: Consistency and Robustness (Phase 3)
- **Mon**: Naming conventions documentation (3.1)
- **Tue**: Input validation (3.2)
- **Wed**: Error recovery logging (3.3)
- **Thu**: Large file detection (3.4)
- **Fri**: Architecture decisions documentation (3.5)

### Week 4: Testing and Validation (Phase 4)
- **Mon-Tue**: Unit and integration tests (4.1-4.2)
- **Wed**: Regression testing (4.3-4.4)
- **Thu**: Performance benchmarking (4.6)
- **Fri**: Documentation and release prep (4.5)

---

## Success Criteria - Overall

### Code Quality
- [ ] Test coverage >85% (maintained)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] MyPy clean (strict mode)
- [ ] Ruff clean
- [ ] No performance regressions

### Functionality
- [ ] Large files (100-500MB) handled gracefully
- [ ] Error handling consistent across codebase
- [ ] Security validation unchanged
- [ ] All features working as before
- [ ] Backward compatibility maintained

### Documentation
- [ ] All public APIs documented
- [ ] Architecture decisions logged
- [ ] Naming conventions standardized
- [ ] README and examples updated
- [ ] CHANGELOG entries added

### Developer Experience
- [ ] Code easier to understand
- [ ] Error messages clearer
- [ ] Debugging easier with context
- [ ] Patterns more consistent
- [ ] New contributor onboarding faster

---

## Risk Mitigation

### Risk: Regressions in File I/O
**Mitigation**:
- Comprehensive FileIoAdapter tests before migration
- Keep SafeTextFileReader tests as baseline
- Gradual migration of callers
- Validation after each file

### Risk: Breaking Changes
**Mitigation**:
- FileIoAdapter is new addition (non-breaking)
- Configuration keys unchanged
- Public APIs maintained
- Deprecation path for any changes

### Risk: Performance Degradation
**Mitigation**:
- Benchmark before/after each phase
- Profile memory usage with large files
- Monitor test suite performance
- Revert if performance drops >5%

### Risk: Incomplete Testing
**Mitigation**:
- Target >85% coverage threshold
- Include edge cases in tests
- Run full suite before commit
- Add tests for new code before shipping

---

## Rollback Plan

Each phase can be independently rolled back:

1. **Phase 1 Rollback**: Remove FileIoAdapter, revert migrations
2. **Phase 2 Rollback**: Undo CLI and database refactoring
3. **Phase 3 Rollback**: Remove new documentation/validation
4. **Phase 4 Rollback**: Remove new tests (keep old ones)

To rollback to current state:
```bash
git reset --hard origin/chore/simplification
git clean -fd
```

---

## Approval and Sign-Off

**Prepared by**: AI Assistant (Copilot)  
**Date**: October 19, 2025  
**Branch**: chore/simplification  
**Status**: Ready for Review  

**Next Steps**:
1. Review and approve plan
2. Begin Phase 1 implementation
3. Conduct weekly progress reviews
4. Adjust timeline as needed

---

## Appendix A: Quick Reference

### FileIoAdapter Usage Examples

```python
# Simple file read with error translation
from splurge_sql_runner.utils.file_io_adapter import FileIoAdapter

content = FileIoAdapter.read_file("query.sql", context_type="sql")

# Streaming large file
for chunk in FileIoAdapter.read_file_chunked("large.sql"):
    for line in chunk:
        process_line(line)

# Size validation
FileIoAdapter.validate_file_size("file.sql", max_size_mb=500)
```

### Error Handling Pattern

```python
from splurge_sql_runner.exceptions import FileError

try:
    content = FileIoAdapter.read_file(path, context_type="sql")
except FileError as e:
    logger.error(f"File error: {e}", exc_info=True)
    logger.debug(f"Context: {e.context}")
    raise
```

### Configuration Access Pattern

```python
# Load with defaults and env overrides
config = load_config(config_file_path)

# Access flat dict directly
db_url = config["database_url"]
max_stmts = config["max_statements_per_file"]
timeout = config["connection_timeout"]
```

### Exception Context Pattern

```python
raise FileError(
    "Failed to read file",
    context={
        "file_path": "/path/to/file.sql",
        "context_type": "sql",
        "operation": "read",
        "size_mb": 125.5,
    }
)
```

---

## Appendix B: Files Modified Summary

| File | Modifications | Lines Changed | Risk |
|------|---------------|---------------|------|
| `utils/file_io_adapter.py` | NEW | +150 | Low |
| `config.py` | Error handling | -8 | Low |
| `main.py` | FileIoAdapter usage | -5, Helper functions | Low |
| `sql_helper.py` | FileIoAdapter usage | -4 | Low |
| `database/database_client.py` | Method extraction | +50, -10 net | Low |
| `cli.py` | Constants/helpers | +20, -30 net | Low |
| `exceptions.py` | No changes | 0 | Low |
| `security.py` | Add __all__ | +2 | None |
| `__init__.py` | Export FileIoAdapter | +3 | Low |
| Tests | Unit + integration | +200 | Low |
| Docs | Architecture decisions | +100 | None |

**Total Impact**: ~400 lines added, ~50 lines removed, net +350 lines (mostly tests)

---

*Implementation Plan - October 19, 2025*  
*Status: Ready for Execution*  
*Next Review: Upon completion of Phase 1*
