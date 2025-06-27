"""
SQL Helper utilities for parsing and cleaning SQL statements.

Copyright (c) 2025, Jim Schilling

Please keep this header when you use this code.

This module is licensed under the MIT License.
"""
from typing import List
import sqlparse
from sqlparse.tokens import Comment, Keyword, DML, DDL


# Private constants for SQL statement types
_FETCH_STATEMENT_TYPES = ('SELECT', 'VALUES', 'SHOW', 'EXPLAIN', 'PRAGMA', 'DESC', 'DESCRIBE')
_DML_STATEMENT_TYPES = ('SELECT', 'INSERT', 'UPDATE', 'DELETE')
_DESCRIBE_STATEMENT_TYPES = ('DESC', 'DESCRIBE')
_MODIFY_DML_TYPES = ('INSERT', 'UPDATE', 'DELETE')

# Private constants for SQL keywords and symbols
_WITH_KEYWORD = 'WITH'
_AS_KEYWORD = 'AS'
_SELECT_KEYWORD = 'SELECT'
_SEMICOLON = ';'
_COMMA = ','
_PAREN_OPEN = '('
_PAREN_CLOSE = ')'

# Public constants for statement type return values
EXECUTE_STATEMENT = 'execute'
FETCH_STATEMENT = 'fetch'


def remove_sql_comments(sql_text: str) -> str:
    """
    Remove SQL comments from a SQL string using sqlparse.
    Handles:
    - Single-line comments (-- comment)
    - Multi-line comments (/* comment */)
    - Preserves comments within string literals
    Args:
        sql_text: SQL string that may contain comments
    Returns:
        SQL string with comments removed
    """
    if not sql_text:
        return sql_text
    return sqlparse.format(sql_text, strip_comments=True)


def _is_fetch_statement(statement_type):
    """
    Determine if a statement type returns rows (fetch) or not (execute).
    
    This function identifies SQL statements that return data rows vs those that
    perform operations without returning data. Fetch statements include SELECT,
    VALUES, SHOW, EXPLAIN, PRAGMA, DESC, and DESCRIBE.
    
    Args:
        statement_type: The SQL statement type (e.g., 'SELECT', 'INSERT', 'VALUES')
        
    Returns:
        True if statement returns rows, False otherwise
        
    Examples:
        >>> _is_fetch_statement('SELECT')
        True
        >>> _is_fetch_statement('INSERT')
        False
        >>> _is_fetch_statement('VALUES')
        True
    """
    return statement_type in _FETCH_STATEMENT_TYPES


def _is_dml_statement(statement_type):
    """
    Determine if a statement type is a DML (Data Manipulation Language) statement.
    
    DML statements are those that manipulate data in the database. This includes
    SELECT (for reading), INSERT (for creating), UPDATE (for modifying), and
    DELETE (for removing) operations.
    
    Args:
        statement_type: The SQL statement type (e.g., 'SELECT', 'CREATE', 'DROP')
        
    Returns:
        True if statement is DML, False otherwise
        
    Examples:
        >>> _is_dml_statement('SELECT')
        True
        >>> _is_dml_statement('CREATE')
        False
        >>> _is_dml_statement('INSERT')
        True
    """
    return statement_type in _DML_STATEMENT_TYPES


def _find_first_dml_keyword_top_level(tokens):
    """
    Find first DML/Keyword at the top level after WITH (do not recurse into groups).
    
    This function searches through SQL tokens to find the first significant
    statement type, ignoring CTE definition groups and focusing only on the
    main statement. It's used as a fallback when more sophisticated parsing
    fails to identify the statement type.
    
    Args:
        tokens: List of sqlparse tokens to analyze
        
    Returns:
        The first DML/Keyword token value (e.g., 'SELECT', 'INSERT') or None if not found
        
    Note:
        This function skips over CTE definition groups and 'AS' keywords to focus
        on the actual statement type. It's a simpler approach compared to
        _find_main_statement_after_ctes().
    """
    for token in tokens:
        if token.is_group:
            continue  # skip CTE definitions
        if not token.is_whitespace and token.ttype not in Comment:
            token_value = token.value.strip().upper()
            if token_value == _AS_KEYWORD:
                continue
            if token.ttype in (DML, Keyword) or _is_dml_statement(token_value) or _is_fetch_statement(token_value):
                return token_value
    return None


def _find_main_statement_after_ctes(tokens):
    """
    Find the main statement after CTE definitions by looking for the first DML after all CTE groups.
    
    This function provides sophisticated parsing for Common Table Expressions (CTEs).
    It tracks the boundaries of CTE definitions and identifies the main statement
    that follows all CTE definitions. This is the preferred method for parsing
    complex WITH clauses.
    
    Args:
        tokens: List of sqlparse tokens to analyze
        
    Returns:
        The main statement type (e.g., 'SELECT', 'INSERT') or None if not found
        
    Note:
        This function handles complex CTE scenarios including:
        - Multiple CTEs separated by commas
        - Nested CTE definitions
        - CTEs with complex subqueries
        - The transition from CTE definitions to the main statement
    """
    in_cte_definition = False
    paren_level = 0
    
    for token in tokens:
        if token.is_whitespace or token.ttype in Comment:
            continue
            
        token_value = token.value.strip().upper()
        
        # Track parentheses for CTE definition boundaries
        if token_value == _PAREN_OPEN:
            paren_level += 1
        elif token_value == _PAREN_CLOSE:
            paren_level -= 1
            # If we're closing a CTE definition and we're at the top level
            if paren_level == 0 and in_cte_definition:
                in_cte_definition = False
                continue
        
        # Track CTE definition boundaries
        if token_value == _AS_KEYWORD:
            in_cte_definition = True
            continue
            
        if in_cte_definition:
            if token.is_group:
                # This is a CTE definition group, skip it
                continue
            elif token_value == _COMMA and paren_level == 0:
                # Another CTE definition starting (only at top level)
                continue
            elif paren_level == 0 and _is_dml_statement(token_value):
                # We've found the main statement after CTE definitions
                in_cte_definition = False
                return token_value
            elif paren_level == 0 and _is_fetch_statement(token_value):
                # We've found the main statement after CTE definitions
                in_cte_definition = False
                return token_value
        
        # Look for main statement when not in CTE definition
        if not in_cte_definition:
            if _is_dml_statement(token_value) or _is_fetch_statement(token_value):
                return token_value
                
    return None


def _next_non_ws_comment_token(tokens, start=0):
    """
    Find the next non-whitespace, non-comment token.
    
    This utility function helps navigate through SQL tokens by skipping over
    whitespace and comments to find the next meaningful token. It's used to
    identify the first significant keyword in a SQL statement.
    
    Args:
        tokens: List of sqlparse tokens to search through
        start: Starting index to search from (default: 0)
        
    Returns:
        Tuple of (index, token) or (None, None) if no non-whitespace/non-comment token found
        
    Examples:
        >>> tokens = [whitespace_token, comment_token, keyword_token]
        >>> _next_non_ws_comment_token(tokens)
        (2, keyword_token)
    """
    for i in range(start, len(tokens)):
        token = tokens[i]
        if not token.is_whitespace and token.ttype not in Comment:
            return i, token
    return None, None


def _is_with_keyword(token):
    """
    Check if a token represents the 'WITH' keyword.
    
    This helper function safely checks if a token is the WITH keyword,
    handling cases where the token might not have a 'value' attribute.
    
    Args:
        token: sqlparse token to check
        
    Returns:
        True if token is the 'WITH' keyword, False otherwise
    """
    return (hasattr(token, 'value') and 
            token.value.strip().upper() == _WITH_KEYWORD)


def _find_with_keyword_index(tokens):
    """
    Find the index of the 'WITH' keyword in a list of tokens.
    
    This function searches through tokens to locate the WITH keyword,
    which marks the beginning of a Common Table Expression.
    
    Args:
        tokens: List of sqlparse tokens to search through
        
    Returns:
        Index of the WITH keyword, or None if not found
    """
    for i, token in enumerate(tokens):
        if _is_with_keyword(token):
            return i
    return None


def _extract_tokens_after_with(stmt):
    """
    Extract tokens that come after the WITH keyword in a CTE statement.
    
    This function processes a SQL statement that starts with 'WITH' and extracts
    all tokens that follow the WITH keyword. This is the first step in parsing
    Common Table Expressions to identify the main statement type.
    
    Args:
        stmt: sqlparse statement object containing the full SQL statement
        
    Returns:
        List of tokens that come after the WITH keyword
        
    Note:
        This function handles the initial parsing of CTE statements by:
        1. Finding the 'WITH' keyword in the statement
        2. Collecting all subsequent tokens
        3. Preparing them for further analysis by CTE-specific parsing functions
    """
    top_tokens = list(stmt.tokens)
    with_index = _find_with_keyword_index(top_tokens)
    
    if with_index is None:
        return []
    
    # Return all tokens after the WITH keyword
    return top_tokens[with_index + 1:]


def detect_statement_type(sql: str) -> str:
    """
    Detect if a SQL statement returns rows using sqlparse.
    Handles:
    - SELECT statements
    - CTEs (WITH ... SELECT)
    - VALUES statements
    - SHOW statements (some databases)
    - DESCRIBE/DESC statements (some databases)
    - EXPLAIN statements (some databases)
    Args:
        sql: SQL statement string
    Returns:
        'fetch' if statement returns rows, 'execute' otherwise
    """
    if not sql or not sql.strip():
        return EXECUTE_STATEMENT
    
    parsed = sqlparse.parse(sql.strip())
    if not parsed:
        return EXECUTE_STATEMENT
    
    stmt = parsed[0]
    tokens = list(stmt.flatten())
    if not tokens:
        return EXECUTE_STATEMENT
    
    _, first_token = _next_non_ws_comment_token(tokens)
    if first_token is None:
        return EXECUTE_STATEMENT
    
    token_value = first_token.value.strip().upper()
    
    # DESC/DESCRIBE detection (regardless of token type)
    if token_value in _DESCRIBE_STATEMENT_TYPES:
        return FETCH_STATEMENT
    
    # CTE detection: WITH ...
    if token_value == _WITH_KEYWORD:
        after_with_tokens = _extract_tokens_after_with(stmt)
        
        # Try the more sophisticated approach first
        main_stmt = _find_main_statement_after_ctes(after_with_tokens)
        if main_stmt is None:
            # Fallback to the simpler approach
            main_stmt = _find_first_dml_keyword_top_level(after_with_tokens)
            
        if main_stmt == _SELECT_KEYWORD:
            return FETCH_STATEMENT
        elif main_stmt in _MODIFY_DML_TYPES:
            return EXECUTE_STATEMENT
        elif _is_fetch_statement(main_stmt):
            return FETCH_STATEMENT
        return EXECUTE_STATEMENT
    
    # SELECT
    if first_token.ttype is DML and token_value == _SELECT_KEYWORD:
        return FETCH_STATEMENT
    
    # VALUES, SHOW, EXPLAIN, PRAGMA
    if _is_fetch_statement(token_value):
        return FETCH_STATEMENT
    
    # All other statements (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.)
    return EXECUTE_STATEMENT


def parse_sql_statements(sql_text: str, strip_semicolon: bool = False) -> List[str]:
    """
    Parse a SQL string containing multiple statements into a list of individual statements using sqlparse.
    Handles:
    - Statements separated by semicolons
    - Preserves semicolons within string literals
    - Removes comments before parsing
    - Trims whitespace from individual statements
    - Filters out empty statements and statements that are only comments
    Args:
        sql_text: SQL string that may contain multiple statements
        strip_semicolon: If True, strip trailing semicolons in statements (default: False)
    Returns:
        List of individual SQL statements (with or without trailing semicolons based on parameter)
    """
    if not sql_text:
        return []
    
    # Remove comments first
    clean_sql = remove_sql_comments(sql_text)
    
    # Use sqlparse to split statements
    parsed_statements = sqlparse.parse(clean_sql)
    filtered_stmts = []
    
    for stmt in parsed_statements:
        stmt_str = str(stmt).strip()
        if not stmt_str:
            continue
            
        # Tokenize and check if all tokens are comments or whitespace
        tokens = list(stmt.flatten())
        if not tokens:
            continue
        if all(t.is_whitespace or t.ttype in Comment for t in tokens):
            continue
            
        # Filter out statements that are just semicolons
        if stmt_str == _SEMICOLON:
            continue
            
        # Apply semicolon stripping based on parameter
        if strip_semicolon:
            stmt_str = stmt_str.rstrip(';').strip()
            
        filtered_stmts.append(stmt_str)
    
    return filtered_stmts


def split_sql_file(file_path: str, strip_semicolon: bool = False) -> List[str]:
    """
    Read a SQL file and split it into individual statements.
    
    Args:
        file_path: Path to the SQL file
        strip_semicolon: If True, strip trailing semicolons in statements (default: False)
    
    Returns:
        List of individual SQL statements
    
    Raises:
        FileNotFoundError: If the file doesn't exist
        OSError: If there's an error reading the file
        ValueError: If file_path is empty or invalid
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")
    
    if not isinstance(file_path, str):
        raise ValueError("file_path must be a string")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        return parse_sql_statements(sql_content, strip_semicolon)
    except FileNotFoundError:
        raise FileNotFoundError(f"SQL file not found: {file_path}")
    except OSError as e:
        raise OSError(f"Error reading SQL file {file_path}: {e}") from e


# Usage examples
if __name__ == "__main__":
    # Example 1: Remove comments
    sql_with_comments = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY, -- user id
        name TEXT NOT NULL,     /* user name */
        email TEXT              -- user email
    );
    """
    
    clean_sql = remove_sql_comments(sql_with_comments)
    print("Clean SQL:")
    print(clean_sql)
    print()
    
    # Example 2: Parse multiple statements (preserve semicolons by default)
    multi_sql = """
    CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
    INSERT INTO users VALUES (1, 'John');
    INSERT INTO users VALUES (2, 'Jane');
    SELECT * FROM users;
    """
    
    statements = parse_sql_statements(multi_sql)
    print("Individual statements (semicolons preserved):")
    for i, stmt in enumerate(statements, 1):
        print(f"{i}. {stmt}")
    print()
    
    # Example 3: Parse multiple statements (strip semicolons)
    statements_without_semicolons = parse_sql_statements(multi_sql, strip_semicolon=True)
    print("Individual statements (semicolons stripped):")
    for i, stmt in enumerate(statements_without_semicolons, 1):
        print(f"{i}. {stmt}")
    print() 