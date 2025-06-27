-- Example SQL file for testing jpy-sql-runner CLI

-- Create a test table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert some test data
INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com');
INSERT INTO users (name, email) VALUES ('Jane Smith', 'jane@example.com');
INSERT INTO users (name, email) VALUES ('Bob Johnson', 'bob@example.com');

-- Query the data
SELECT * FROM users;

-- Count users
SELECT COUNT(*) as user_count FROM users;

-- Find users with specific names
SELECT name, email FROM users WHERE name LIKE '%John%'; 