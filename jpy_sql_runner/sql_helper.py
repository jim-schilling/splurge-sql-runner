"""
SQL Helper utilities for parsing and cleaning SQL statements.

Copyright (c) 2025, Jim Schilling

Please keep this header when you use this code.

This module is licensed under the MIT License.
"""
from typing import List
import sqlparse
from sqlparse.tokens import Comment


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
        if stmt_str == ';':
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