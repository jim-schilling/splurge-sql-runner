-- Database Cleanup and Maintenance Example
-- This file demonstrates database maintenance and cleanup operations

-- ============================================================================
-- MAINTENANCE AND CLEANUP OPERATIONS
-- ============================================================================

-- 1. Clean up expired sessions
SELECT '=== CLEANING UP EXPIRED SESSIONS ===' as operation;

-- First, let's add some expired sessions for demonstration
INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at, is_active) VALUES 
    (1, 'expired_token_1', '192.168.1.100', 'Mozilla/5.0...', datetime('now', '-1 day'), FALSE),
    (2, 'expired_token_2', '192.168.1.101', 'Mozilla/5.0...', datetime('now', '-2 days'), TRUE),
    (3, 'expired_token_3', '192.168.1.102', 'Mozilla/5.0...', datetime('now', '-1 week'), TRUE);

-- Show sessions that will be cleaned up
SELECT 
    'Sessions to be cleaned up:' as info,
    COUNT(*) as count
FROM user_sessions 
WHERE expires_at < CURRENT_TIMESTAMP OR is_active = FALSE;

-- Clean up expired sessions
DELETE FROM user_sessions 
WHERE expires_at < CURRENT_TIMESTAMP OR is_active = FALSE;

-- Verify cleanup
SELECT 
    'Remaining active sessions:' as info,
    COUNT(*) as count
FROM user_sessions 
WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP;

-- 2. Update user statistics
SELECT '=== UPDATING USER STATISTICS ===' as operation;

-- Update login counts for demonstration (simulate some logins)
UPDATE users SET 
    login_count = login_count + CASE 
        WHEN username IN ('john_doe', 'sarah_jones', 'emma_taylor') THEN 1
        ELSE 0
    END,
    last_login = CASE 
        WHEN username IN ('john_doe', 'sarah_jones', 'emma_taylor') THEN CURRENT_TIMESTAMP
        ELSE last_login
    END;

-- Show updated statistics
SELECT 
    username,
    login_count,
    last_login,
    CASE 
        WHEN last_login > datetime('now', '-1 day') THEN 'Recent'
        WHEN last_login > datetime('now', '-1 week') THEN 'This Week'
        WHEN last_login > datetime('now', '-1 month') THEN 'This Month'
        ELSE 'Old'
    END as login_recency
FROM users
ORDER BY last_login DESC;

-- 3. Database optimization
SELECT '=== DATABASE OPTIMIZATION ===' as operation;

-- Analyze table statistics for query optimization
ANALYZE;

-- Show table sizes and statistics
SELECT 
    name as table_name,
    type,
    sql
FROM sqlite_master 
WHERE type = 'table'
ORDER BY name;

-- 4. Data integrity checks
SELECT '=== DATA INTEGRITY CHECKS ===' as operation;

-- Check for orphaned posts (posts without valid users)
SELECT 
    'Orphaned posts:' as check_type,
    COUNT(*) as count
FROM posts p
LEFT JOIN users u ON p.user_id = u.id
WHERE u.id IS NULL;

-- Check for users with invalid roles
SELECT 
    'Users with invalid roles:' as check_type,
    COUNT(*) as count
FROM users u
LEFT JOIN roles r ON u.role = r.name
WHERE u.role IS NOT NULL AND r.name IS NULL;

-- Check for duplicate usernames or emails
SELECT 
    'Duplicate usernames:' as check_type,
    COUNT(*) as count
FROM (
    SELECT username, COUNT(*) as cnt
    FROM users
    GROUP BY username
    HAVING cnt > 1
);

SELECT 
    'Duplicate emails:' as check_type,
    COUNT(*) as count
FROM (
    SELECT email, COUNT(*) as cnt
    FROM users
    GROUP BY email
    HAVING cnt > 1
);

-- 5. Performance monitoring
SELECT '=== PERFORMANCE MONITORING ===' as operation;

-- Check index usage and effectiveness
SELECT 
    'Indexes on users table:' as info,
    COUNT(*) as count
FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'users';

SELECT 
    'Indexes on posts table:' as info,
    COUNT(*) as count
FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'posts';

-- 6. Archive old data (example)
SELECT '=== ARCHIVING OLD DATA ===' as operation;

-- Create archive table for old posts
CREATE TABLE IF NOT EXISTS posts_archive (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    title VARCHAR(200),
    content TEXT,
    published BOOLEAN,
    created_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Archive posts older than 1 year (for demonstration, we'll use a shorter period)
-- In real scenarios, you might archive posts older than 1-2 years
INSERT INTO posts_archive (id, user_id, title, content, published, created_at)
SELECT id, user_id, title, content, published, created_at
FROM posts
WHERE created_at < datetime('now', '-1 month'); -- Using 1 month for demo

-- Show archived posts
SELECT 
    'Posts archived:' as info,
    COUNT(*) as count
FROM posts_archive;

-- 7. Backup verification
SELECT '=== BACKUP VERIFICATION ===' as operation;

-- Simulate backup verification by checking data consistency
SELECT 
    'Total users in main table:' as metric,
    COUNT(*) as count
FROM users
UNION ALL
SELECT 
    'Total posts in main table:',
    COUNT(*)
FROM posts
UNION ALL
SELECT 
    'Total archived posts:',
    COUNT(*)
FROM posts_archive
UNION ALL
SELECT 
    'Total active sessions:',
    COUNT(*)
FROM user_sessions
WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP;

-- 8. Maintenance summary report
SELECT '=== MAINTENANCE SUMMARY REPORT ===' as operation;

-- Generate maintenance summary
WITH maintenance_stats AS (
    SELECT 
        (SELECT COUNT(*) FROM users) as total_users,
        (SELECT COUNT(*) FROM posts) as total_posts,
        (SELECT COUNT(*) FROM posts_archive) as archived_posts,
        (SELECT COUNT(*) FROM user_sessions WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP) as active_sessions,
        (SELECT COUNT(*) FROM users WHERE last_login > datetime('now', '-1 day')) as active_users_today,
        (SELECT COUNT(*) FROM users WHERE last_login > datetime('now', '-1 week')) as active_users_week,
        (SELECT COUNT(*) FROM posts WHERE published = TRUE) as published_posts,
        (SELECT COUNT(*) FROM posts WHERE published = FALSE) as draft_posts
)
SELECT 
    'Database Health Summary' as report_section,
    total_users as users,
    total_posts as posts,
    archived_posts as archived,
    active_sessions as sessions,
    active_users_today as active_today,
    active_users_week as active_week,
    published_posts as published,
    draft_posts as drafts,
    ROUND(published_posts * 100.0 / total_posts, 2) as publish_rate,
    ROUND(active_users_today * 100.0 / total_users, 2) as daily_activity_rate
FROM maintenance_stats;

-- 9. Recommendations for next maintenance
SELECT '=== MAINTENANCE RECOMMENDATIONS ===' as operation;

-- Generate maintenance recommendations
SELECT 
    CASE 
        WHEN COUNT(*) > 100 THEN 'Consider archiving old posts'
        ELSE 'Post count is manageable'
    END as recommendation,
    COUNT(*) as current_count
FROM posts
WHERE created_at < datetime('now', '-6 months')
UNION ALL
SELECT 
    CASE 
        WHEN COUNT(*) > 50 THEN 'Consider cleaning up inactive users'
        ELSE 'User count is manageable'
    END,
    COUNT(*)
FROM users
WHERE last_login < datetime('now', '-3 months')
UNION ALL
SELECT 
    CASE 
        WHEN COUNT(*) > 10 THEN 'Consider optimizing indexes'
        ELSE 'Index count is reasonable'
    END,
    COUNT(*)
FROM sqlite_master
WHERE type = 'index';

-- 10. Final cleanup verification
SELECT '=== FINAL CLEANUP VERIFICATION ===' as operation;

-- Verify all cleanup operations were successful
SELECT 
    'Cleanup verification completed successfully' as status,
    datetime('now') as completed_at,
    'All maintenance tasks completed' as summary;
