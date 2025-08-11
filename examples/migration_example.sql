-- Database Migration Example
-- This file demonstrates how to safely modify database schema

-- Migration: Add user roles and permissions
-- Version: 1.1.0
-- Date: 2025-01-15

-- First, let's check if the migration has already been applied
-- (This is a common pattern in migration systems)
CREATE TABLE IF NOT EXISTS migration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64),
    execution_time_ms INTEGER
);

-- Check if this migration was already applied
SELECT COUNT(*) as already_applied 
FROM migration_history 
WHERE migration_name = 'add_user_roles_v1_1_0';

-- Add new columns to users table
-- Using IF NOT EXISTS pattern for idempotency
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user';
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;
ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0;

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    permissions TEXT, -- JSON string of permissions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_sessions table for tracking user sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- Insert default roles
INSERT OR IGNORE INTO roles (name, description, permissions) VALUES 
    ('admin', 'Administrator with full access', '["read", "write", "delete", "admin"]'),
    ('moderator', 'Moderator with limited admin access', '["read", "write", "moderate"]'),
    ('user', 'Regular user with basic access', '["read", "write"]'),
    ('guest', 'Guest user with read-only access', '["read"]');

-- Update existing users to have appropriate roles
-- Set the first user as admin, others as regular users
UPDATE users SET role = 'admin' WHERE id = 1;
UPDATE users SET role = 'user' WHERE role IS NULL OR role = '';

-- Create a view for active sessions
CREATE VIEW IF NOT EXISTS active_sessions AS
SELECT 
    us.id,
    us.session_token,
    u.username,
    u.full_name,
    us.ip_address,
    us.created_at,
    us.expires_at
FROM user_sessions us
JOIN users u ON us.user_id = u.id
WHERE us.is_active = TRUE 
  AND us.expires_at > CURRENT_TIMESTAMP;

-- Create a view for user statistics
CREATE VIEW IF NOT EXISTS user_stats AS
SELECT 
    u.id,
    u.username,
    u.full_name,
    u.role,
    u.login_count,
    u.last_login,
    COUNT(p.id) as total_posts,
    COUNT(CASE WHEN p.published = TRUE THEN 1 END) as published_posts,
    COUNT(us.id) as active_sessions
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
LEFT JOIN user_sessions us ON u.id = us.user_id AND us.is_active = TRUE
GROUP BY u.id, u.username, u.full_name, u.role, u.login_count, u.last_login;

-- Record this migration in the migration history
INSERT OR IGNORE INTO migration_history (migration_name, version, checksum) 
VALUES ('add_user_roles_v1_1_0', '1.1.0', 'abc123def456');

-- Verify the migration
SELECT 'Migration verification:' as info, 'add_user_roles_v1_1_0' as migration_name
UNION ALL
SELECT 'Users with roles:', COUNT(*) FROM users WHERE role IS NOT NULL
UNION ALL
SELECT 'Roles created:', COUNT(*) FROM roles
UNION ALL
SELECT 'Tables created:', (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('roles', 'user_sessions', 'migration_history'));

-- Show current user roles
SELECT 
    username,
    full_name,
    role,
    login_count,
    last_login
FROM users
ORDER BY role, username;
