-- Basic Database Setup Example
-- This file demonstrates common database operations

-- Create a users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create an index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create a posts table with foreign key relationship
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published);

-- Insert sample user data
INSERT INTO users (username, email, full_name) VALUES 
    ('john_doe', 'john@example.com', 'John Doe'),
    ('jane_smith', 'jane@example.com', 'Jane Smith'),
    ('bob_wilson', 'bob@example.com', 'Bob Wilson'),
    ('alice_brown', 'alice@example.com', 'Alice Brown');

-- Insert sample post data
INSERT INTO posts (user_id, title, content, published) VALUES 
    (1, 'My First Post', 'This is my first blog post content.', TRUE),
    (1, 'Draft Post', 'This is a draft post that is not published yet.', FALSE),
    (2, 'Hello World', 'Hello world! This is Jane''s first post.', TRUE),
    (3, 'Technical Article', 'A technical article about databases.', TRUE),
    (4, 'Personal Thoughts', 'Some personal thoughts and reflections.', FALSE);

-- Query to verify the setup
SELECT 'Users count:' as info, COUNT(*) as count FROM users
UNION ALL
SELECT 'Posts count:', COUNT(*) FROM posts
UNION ALL
SELECT 'Published posts:', COUNT(*) FROM posts WHERE published = TRUE;

-- Show users with their post counts
SELECT 
    u.username,
    u.full_name,
    COUNT(p.id) as post_count,
    COUNT(CASE WHEN p.published = TRUE THEN 1 END) as published_posts
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
GROUP BY u.id, u.username, u.full_name
ORDER BY post_count DESC;
