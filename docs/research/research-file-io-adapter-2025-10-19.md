# Research: FileIoAdapter Pattern and Large File Handling Strategy

**Date**: October 19, 2025  
**Context**: Discussion about leveraging `SafeTextFileReader.readlines_as_stream()` for large file support and centralizing `SplurgeSafeIo` error translation

## Executive Summary

**Question 1: Should we use `readlines_as_stream()` for large file support?**  
**Answer**: Yes, but selectively. Streaming is beneficial for SQL file processing but not for config files.

**Question 2: Should we create a `FileIoAdapter` to wrap `SplurgeSafeIo*` errors?**  
**Answer**: Yes, definitely. This provides consistent error handling, domain-specific context, and architectural isolation.

---

## Current State Analysis

### Current File I/O Usage (3 locations)

1. **`main.py:110`** - SQL file processing
   ```python
   reader = SafeTextFileReader(fp)
   content = reader.read()  # ← Entire file loaded to memory
   ```
   - **Issue**: Large files (>100MB) cause memory problems
   - **Frequency**: Per file in multi-file batch processing
   - **Candidate for streaming**: **YES** ✅

2. **`config.py:120`** - Configuration file reading
   ```python
   reader = SafeTextFileReader(file_path, encoding="utf-8")
   config_data = json.loads(reader.read())
   ```
   - **Issue**: Config files assumed small
   - **Frequency**: Once at startup
   - **Candidate for streaming**: **NO** ❌ (JSON requires full document)

3. **`sql_helper.py:449`** - SQL file reading (utility function)
   ```python
   reader = SafeTextFileReader(file_path, encoding="utf-8")
   return reader.read()
   ```
   - **Issue**: Also loads entire file
   - **Frequency**: Called from `main.py`
   - **Candidate for streaming**: **YES** ✅

### Current Error Handling (Scattered)

**Pattern 1**: `config.py` - Explicit mapping
```python
except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
    raise ConfigFileError(f"Configuration file not found: {file_path}") from e
except safe_io_exc.SplurgeSafeIoFilePermissionError as e:
    raise ConfigFileError(f"Permission denied reading config file: {file_path}") from e
except safe_io_exc.SplurgeSafeIoUnknownError as e:
    raise ConfigFileError(f"Unknown error reading config file: {file_path}") from e
```

**Pattern 2**: `main.py` - Generic catch-all
```python
except Exception as e:
    summary["results"][fp] = [{"error": f"Unexpected error processing file {fp}: {e}"}]
```

**Pattern 3**: `sql_helper.py` - Converts to domain error
```python
from splurge_sql_runner.exceptions import SqlFileError
# ... attempt file read ...
# No explicit error handling visible in snippet
```

### Issues with Current Approach

1. **Duplication**: Same error mapping logic in multiple files
2. **Inconsistency**: Different strategies per location
3. **Limited Context**: Error messages lack domain context (file type, operation, etc.)
4. **No Abstraction**: Direct dependency on `SplurgeSafeIo` API throughout
5. **Memory Issue**: All SQL files fully loaded before processing
6. **Hard to Test**: Cannot mock file I/O without mocking entire `SafeTextFileReader`

---

## Recommendation: FileIoAdapter Pattern

### Design Overview

Create a `FileIoAdapter` class that:
1. Wraps `SafeTextFileReader` API
2. Translates `SplurgeSafeIo*` exceptions to domain errors
3. Provides both streaming and non-streaming read methods
4. Adds contextual information to errors
5. Simplifies caller code

### Architecture

```
┌─────────────────────────────────────────┐
│  Domain Code (main, sql_helper, etc.)   │
└──────────────┬──────────────────────────┘
               │ Uses
               ↓
      ┌────────────────────┐
      │  FileIoAdapter     │
      │  (New Module)      │
      └──────────┬─────────┘
               │ Uses
               ↓
      ┌────────────────────────────────┐
      │  SafeTextFileReader            │
      │  (splurge_safe_io library)     │
      └────────────────────────────────┘
```

### Proposed API

```python
# Location: splurge_sql_runner/utils/file_io_adapter.py

class FileIoAdapter:
    """Adapter for safe file I/O with domain error translation."""
    
    @staticmethod
    def read_file(
        file_path: str,
        encoding: str = "utf-8",
        context_type: str = "generic",
    ) -> str:
        """Read entire file content.
        
        Args:
            file_path: Path to file
            encoding: Character encoding
            context_type: "config", "sql", or "generic" for error messages
            
        Returns:
            File content as string
            
        Raises:
            FileError: If file cannot be read
            
        Example:
            content = FileIoAdapter.read_file("query.sql", context_type="sql")
        """
    
    @staticmethod
    def read_file_chunked(
        file_path: str,
        encoding: str = "utf-8",
        chunk_size: int = 1000,
        context_type: str = "generic",
    ) -> Iterator[list[str]]:
        """Yield chunks of lines from file.
        
        Args:
            file_path: Path to file
            encoding: Character encoding
            chunk_size: Max lines per chunk
            context_type: "config", "sql", or "generic" for error messages
            
        Yields:
            Lists of lines (each list has <= chunk_size lines)
            
        Raises:
            FileError: If file cannot be read
            
        Example:
            for chunk in FileIoAdapter.read_file_chunked("large.sql"):
                process_chunk(chunk)
        """
```

### Implementation Details

**File**: `splurge_sql_runner/utils/file_io_adapter.py` (~80 lines)

```python
from typing import Iterator
from splurge_safe_io import SafeTextFileReader
import splurge_safe_io.exceptions as safe_io_exc

from splurge_sql_runner.exceptions import FileError
from splurge_sql_runner.logging import configure_module_logging

logger = configure_module_logging("file_io")

CONTEXT_MESSAGES = {
    "config": "configuration file",
    "sql": "SQL file",
    "generic": "file",
}

class FileIoAdapter:
    """Wraps SafeTextFileReader with domain error translation."""
    
    @staticmethod
    def read_file(
        file_path: str,
        encoding: str = "utf-8",
        context_type: str = "generic",
    ) -> str:
        """Read entire file content with error translation."""
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            return reader.read()
        except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
            context_name = CONTEXT_MESSAGES.get(context_type, context_type)
            msg = f"File not found: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path, "type": context_type}) from e
        except safe_io_exc.SplurgeSafeIoFilePermissionError as e:
            context_name = CONTEXT_MESSAGES.get(context_type, context_type)
            msg = f"Permission denied reading {context_name}: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path, "type": context_type}) from e
        except safe_io_exc.SplurgeSafeIoFileDecodingError as e:
            msg = f"Invalid encoding in {context_type}: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path, "type": context_type}) from e
        except safe_io_exc.SplurgeSafeIoOsError as e:
            msg = f"OS error reading {context_type}: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path, "type": context_type}) from e
        except safe_io_exc.SplurgeSafeIoUnknownError as e:
            msg = f"Unknown error reading {context_type}: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path, "type": context_type}) from e
    
    @staticmethod
    def read_file_chunked(
        file_path: str,
        encoding: str = "utf-8",
        chunk_size: int = 1000,
        context_type: str = "generic",
    ) -> Iterator[list[str]]:
        """Yield chunks of lines from file with error translation."""
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            # readlines_as_stream yields list[str], we wrap it
            for chunk in reader.readlines_as_stream():
                yield chunk
        except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
            msg = f"File not found: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path, "type": context_type}) from e
        except safe_io_exc.SplurgeSafeIoFilePermissionError as e:
            msg = f"Permission denied reading {context_type}: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path, "type": context_type}) from e
        # ... other exceptions
```

### Benefits

| Benefit | Impact | Effort |
|---------|--------|--------|
| **Centralized Error Translation** | Reduces duplication; consistent across codebase | Low |
| **Domain Context** | Errors include file type, purpose, path | Low |
| **Memory Efficiency** | Streaming support for large files | Medium |
| **Easier Testing** | Can mock single adapter instead of SafeTextFileReader | Low |
| **Future Extensibility** | Can add file size checks, caching, etc. | Medium |
| **Loose Coupling** | Internal dependency changes don't affect domain code | Low |

---

## Streaming Implementation Strategy

### When to Use `readlines_as_stream()`

**✅ Use Streaming**:
- SQL files (can be 100MB+)
- Large batch processing
- When line-by-line processing is natural

**❌ Don't Use Streaming**:
- JSON config files (need full document for parsing)
- Small files (<10MB)
- When entire content needed upfront

### Integration Points

#### 1. **main.py** - Process files with streaming

**Before**:
```python
reader = SafeTextFileReader(fp)
content = reader.read()
results = process_sql(content, ...)
```

**After**:
```python
content = FileIoAdapter.read_file(fp, context_type="sql")
results = process_sql(content, ...)
```

Or for large file support:
```python
accumulated_lines = []
for chunk in FileIoAdapter.read_file_chunked(fp, context_type="sql"):
    accumulated_lines.extend(chunk)
content = "\n".join(accumulated_lines)
results = process_sql(content, ...)
```

#### 2. **config.py** - Continue non-streaming

**Before**:
```python
reader = SafeTextFileReader(file_path, encoding="utf-8")
config_data = json.loads(reader.read())
```

**After**:
```python
content = FileIoAdapter.read_file(file_path, context_type="config")
config_data = json.loads(content)
```

Stays simple; no streaming needed for config files.

#### 3. **sql_helper.py** - Utility simplification

**Before**:
```python
reader = SafeTextFileReader(file_path, encoding="utf-8")
return reader.read()
```

**After**:
```python
return FileIoAdapter.read_file(file_path, context_type="sql")
```

---

## Future Enhancements

### Phase 2: Advanced Streaming
```python
def read_sql_file_statements(file_path: str) -> Iterator[str]:
    """Yield individual SQL statements from file without loading all at once."""
    accumulated = ""
    for chunk in FileIoAdapter.read_file_chunked(file_path):
        accumulated += "\n".join(chunk)
        
        # Yield complete statements, keep incomplete for next chunk
        statements = split_statements_keeping_incomplete(accumulated)
        for stmt in statements[:-1]:  # All but last (incomplete)
            yield stmt
        accumulated = statements[-1]  # Keep incomplete for next chunk
    
    if accumulated.strip():
        yield accumulated
```

### Phase 3: File Size Validation
```python
def validate_file_size(
    file_path: str,
    max_size_mb: int = 500,
) -> None:
    """Validate file is not too large."""
    size = Path(file_path).stat().st_size / (1024 * 1024)
    if size > max_size_mb:
        raise FileError(
            f"File too large: {size:.1f}MB (max: {max_size_mb}MB)",
            context={"size_mb": size, "max_mb": max_size_mb}
        )
```

---

## Implementation Roadmap

### Step 1: Create FileIoAdapter (Immediate)
- Location: `splurge_sql_runner/utils/file_io_adapter.py`
- Lines: ~100-150
- Dependencies: SafeTextFileReader, exceptions, logging
- Tests: 8-10 test cases covering all error paths

### Step 2: Migrate Error Handling (Quick)
- Update `config.py` to use adapter
- Update `main.py` to use adapter
- Update `sql_helper.py` to use adapter
- Result: 3 files simplified, ~30 lines removed

### Step 3: Add Streaming Support (Optional)
- Modify `main.py` to use `read_file_chunked()` for large files
- Add file size detection
- Conditional: use streaming only if file > threshold

### Step 4: Documentation
- Add docstrings with examples
- Document context_type options
- Add to copilot-instructions.md

---

## Error Context Examples

### Current (Scattered)
```
FileError: Permission denied reading config file: config.json
```

### With Adapter
```
FileError: Permission denied reading configuration file: config.json
Context: {
    "file_path": "config.json",
    "type": "config",
    "operation": "read"
}
```

This context can be:
- Logged for debugging
- Included in error messages
- Used for metrics/monitoring
- Passed to handlers

---

## Testing Strategy

```python
# tests/unit/test_file_io_adapter_basic.py

def test_read_file_existing_returns_content():
    """Test reading existing file returns content."""
    content = FileIoAdapter.read_file("tests/data/test.sql", context_type="sql")
    assert "SELECT" in content

def test_read_file_not_found_raises_file_error():
    """Test reading missing file raises FileError."""
    with pytest.raises(FileError) as exc_info:
        FileIoAdapter.read_file("nonexistent.sql", context_type="sql")
    assert exc_info.value.get_context("file_path") == "nonexistent.sql"

def test_read_file_chunked_yields_lines():
    """Test streaming yields line chunks."""
    chunks = list(FileIoAdapter.read_file_chunked("tests/data/large.sql"))
    assert len(chunks) > 0
    assert all(isinstance(c, list) for c in chunks)

def test_context_type_in_error():
    """Test context_type is preserved in error."""
    with pytest.raises(FileError) as exc_info:
        FileIoAdapter.read_file("missing.sql", context_type="config")
    error = exc_info.value
    assert error.get_context("type") == "config"
```

---

## Summary Table: FileIoAdapter vs Current Approach

| Aspect | Current | With Adapter |
|--------|---------|--------------|
| **Error Translation** | Scattered in 3 files | Centralized in 1 class |
| **Large File Support** | Not possible | Streaming option |
| **Error Context** | Minimal | Rich (file_path, type, etc.) |
| **Code Duplication** | 15+ lines repeated | 0 duplication |
| **Testability** | Hard to mock | Easy to mock |
| **Dependency Isolation** | Tight coupling | Loose coupling |
| **Memory Efficiency** | All-at-once loading | On-demand chunking |
| **LOC (Domain Code)** | Same or more | Reduced by ~15-20 lines |

---

## Recommendations (Prioritized)

### ✅ DO: Implement FileIoAdapter (High Value, Low Cost)
- Creates single source of truth for file I/O errors
- Simplifies domain code in 3 locations
- Enables future enhancements (streaming, monitoring)
- 1-2 hours implementation + 1-2 hours testing

### ✅ MAYBE: Add Streaming Support (Medium Value, Medium Cost)
- Only needed if large SQL files become common
- Can be added after FileIoAdapter exists
- Check if current memory usage is actually a problem
- Recommended: defer until demonstrated need

### ✅ NICE-TO-HAVE: File Size Validation (Low Value, Low Cost)
- Add guard check: fail fast on huge files
- Prevent memory exhaustion
- Can be added to FileIoAdapter in Phase 2

---

## Conclusion

**FileIoAdapter is recommended** because:

1. **Low Risk**: Wraps existing API; no behavior changes
2. **High Clarity**: Single place to understand file I/O strategy
3. **Future-Proof**: Enables streaming without changing callers
4. **Better Errors**: Rich context for debugging
5. **Reduced Duplication**: 15+ lines of similar error handling eliminated

**Streaming is optional but viable** because:

1. `SafeTextFileReader.readlines_as_stream()` API is stable
2. SQL files don't need full content upfront (can process line-by-line)
3. Can be added transparently within FileIoAdapter
4. No caller changes needed to switch between streaming/non-streaming

**Recommended Execution**:
1. Implement FileIoAdapter immediately (Quick Win)
2. Assess actual large-file needs before implementing streaming
3. Add monitoring to understand file I/O patterns

---

*Document: FileIoAdapter Design Analysis*  
*Date: October 19, 2025*  
*Recommendation: Proceed with Phase 1 (FileIoAdapter) immediately*
