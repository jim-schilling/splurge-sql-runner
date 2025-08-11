-- Data Analysis Example
-- This file demonstrates complex SQL queries and data analysis

-- First, let's add some more sample data for analysis
INSERT INTO users (username, email, full_name, role) VALUES 
    ('sarah_jones', 'sarah@example.com', 'Sarah Jones', 'moderator'),
    ('mike_davis', 'mike@example.com', 'Mike Davis', 'user'),
    ('lisa_wang', 'lisa@example.com', 'Lisa Wang', 'user'),
    ('david_lee', 'david@example.com', 'David Lee', 'user'),
    ('emma_taylor', 'emma@example.com', 'Emma Taylor', 'moderator');

-- Add more posts for analysis
INSERT INTO posts (user_id, title, content, published) VALUES 
    (2, 'Getting Started with SQL', 'A beginner guide to SQL...', TRUE),
    (2, 'Advanced SQL Techniques', 'Advanced SQL patterns and techniques...', TRUE),
    (3, 'Database Design Principles', 'Best practices for database design...', TRUE),
    (4, 'Performance Optimization', 'How to optimize database performance...', TRUE),
    (5, 'Security Best Practices', 'Database security considerations...', TRUE),
    (6, 'Data Migration Strategies', 'Planning and executing data migrations...', TRUE),
    (7, 'Backup and Recovery', 'Database backup and recovery procedures...', TRUE),
    (8, 'Monitoring and Alerting', 'Setting up database monitoring...', TRUE),
    (9, 'Scaling Databases', 'Horizontal and vertical scaling strategies...', TRUE),
    (10, 'Cloud Database Solutions', 'Overview of cloud database options...', TRUE);

-- Simulate some user activity (login counts and last login)
UPDATE users SET 
    login_count = CASE 
        WHEN username = 'john_doe' THEN 45
        WHEN username = 'jane_smith' THEN 32
        WHEN username = 'bob_wilson' THEN 28
        WHEN username = 'alice_brown' THEN 15
        WHEN username = 'sarah_jones' THEN 67
        WHEN username = 'mike_davis' THEN 23
        WHEN username = 'lisa_wang' THEN 41
        WHEN username = 'david_lee' THEN 19
        WHEN username = 'emma_taylor' THEN 53
        ELSE 0
    END,
    last_login = CASE 
        WHEN username = 'john_doe' THEN datetime('now', '-2 hours')
        WHEN username = 'jane_smith' THEN datetime('now', '-1 day')
        WHEN username = 'bob_wilson' THEN datetime('now', '-3 days')
        WHEN username = 'alice_brown' THEN datetime('now', '-1 week')
        WHEN username = 'sarah_jones' THEN datetime('now', '-30 minutes')
        WHEN username = 'mike_davis' THEN datetime('now', '-2 days')
        WHEN username = 'lisa_wang' THEN datetime('now', '-6 hours')
        WHEN username = 'david_lee' THEN datetime('now', '-1 week')
        WHEN username = 'emma_taylor' THEN datetime('now', '-12 hours')
        ELSE NULL
    END;

-- ============================================================================
-- ANALYSIS QUERIES
-- ============================================================================

-- 1. User Activity Analysis
SELECT '=== USER ACTIVITY ANALYSIS ===' as section;

-- Most active users by login count
SELECT 
    username,
    full_name,
    role,
    login_count,
    last_login,
    CASE 
        WHEN last_login > datetime('now', '-1 day') THEN 'Very Active'
        WHEN last_login > datetime('now', '-1 week') THEN 'Active'
        WHEN last_login > datetime('now', '-1 month') THEN 'Inactive'
        ELSE 'Very Inactive'
    END as activity_level
FROM users
ORDER BY login_count DESC;

-- 2. Content Analysis
SELECT '=== CONTENT ANALYSIS ===' as section;

-- Posts by user with engagement metrics
SELECT 
    u.username,
    u.full_name,
    u.role,
    COUNT(p.id) as total_posts,
    COUNT(CASE WHEN p.published = TRUE THEN 1 END) as published_posts,
    COUNT(CASE WHEN p.published = FALSE THEN 1 END) as draft_posts,
    ROUND(COUNT(CASE WHEN p.published = TRUE THEN 1 END) * 100.0 / COUNT(p.id), 2) as publish_rate
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
GROUP BY u.id, u.username, u.full_name, u.role
HAVING total_posts > 0
ORDER BY total_posts DESC;

-- 3. Role-based Analysis
SELECT '=== ROLE-BASED ANALYSIS ===' as section;

-- Statistics by user role
SELECT 
    role,
    COUNT(*) as user_count,
    AVG(login_count) as avg_logins,
    SUM(login_count) as total_logins,
    COUNT(CASE WHEN last_login > datetime('now', '-1 day') THEN 1 END) as active_today,
    COUNT(CASE WHEN last_login > datetime('now', '-1 week') THEN 1 END) as active_this_week
FROM users
GROUP BY role
ORDER BY user_count DESC;

-- 4. Content Publishing Trends
SELECT '=== PUBLISHING TRENDS ===' as section;

-- Publishing activity over time (simulated)
SELECT 
    strftime('%Y-%m', p.created_at) as month,
    COUNT(*) as total_posts,
    COUNT(CASE WHEN p.published = TRUE THEN 1 END) as published_posts,
    COUNT(CASE WHEN p.published = FALSE THEN 1 END) as draft_posts,
    ROUND(COUNT(CASE WHEN p.published = TRUE THEN 1 END) * 100.0 / COUNT(*), 2) as publish_percentage
FROM posts p
GROUP BY strftime('%Y-%m', p.created_at)
ORDER BY month;

-- 5. User Engagement Score
SELECT '=== USER ENGAGEMENT SCORES ===' as section;

-- Calculate engagement score based on multiple factors
WITH user_metrics AS (
    SELECT 
        u.id,
        u.username,
        u.full_name,
        u.role,
        u.login_count,
        COUNT(p.id) as post_count,
        COUNT(CASE WHEN p.published = TRUE THEN 1 END) as published_count,
        CASE 
            WHEN u.last_login > datetime('now', '-1 day') THEN 10
            WHEN u.last_login > datetime('now', '-1 week') THEN 5
            WHEN u.last_login > datetime('now', '-1 month') THEN 2
            ELSE 0
        END as recency_score
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    GROUP BY u.id, u.username, u.full_name, u.role, u.login_count
)
SELECT 
    username,
    full_name,
    role,
    login_count,
    post_count,
    published_count,
    recency_score,
    (login_count * 0.3 + post_count * 0.4 + published_count * 0.2 + recency_score * 0.1) as engagement_score
FROM user_metrics
ORDER BY engagement_score DESC;

-- 6. Content Quality Analysis
SELECT '=== CONTENT QUALITY ANALYSIS ===' as section;

-- Analyze post content length and complexity
SELECT 
    u.username,
    p.title,
    LENGTH(p.content) as content_length,
    CASE 
        WHEN LENGTH(p.content) < 100 THEN 'Short'
        WHEN LENGTH(p.content) < 500 THEN 'Medium'
        WHEN LENGTH(p.content) < 1000 THEN 'Long'
        ELSE 'Very Long'
    END as content_category,
    p.published,
    p.created_at
FROM posts p
JOIN users u ON p.user_id = u.id
ORDER BY content_length DESC;

-- 7. System Health Check
SELECT '=== SYSTEM HEALTH CHECK ===' as section;

-- Overall system statistics
SELECT 
    'Total Users' as metric,
    COUNT(*) as value
FROM users
UNION ALL
SELECT 
    'Active Users (Last 7 days)',
    COUNT(CASE WHEN last_login > datetime('now', '-7 days') THEN 1 END)
FROM users
UNION ALL
SELECT 
    'Total Posts',
    COUNT(*)
FROM posts
UNION ALL
SELECT 
    'Published Posts',
    COUNT(CASE WHEN published = TRUE THEN 1 END)
FROM posts
UNION ALL
SELECT 
    'Draft Posts',
    COUNT(CASE WHEN published = FALSE THEN 1 END)
FROM posts
UNION ALL
SELECT 
    'Average Posts per User',
    ROUND(COUNT(*) * 1.0 / (SELECT COUNT(*) FROM users), 2)
FROM posts
UNION ALL
SELECT 
    'Average Login Count',
    ROUND(AVG(login_count), 2)
FROM users;

-- 8. Recommendations
SELECT '=== RECOMMENDATIONS ===' as section;

-- Users who might need attention
SELECT 
    username,
    full_name,
    role,
    CASE 
        WHEN login_count = 0 THEN 'Never logged in'
        WHEN last_login < datetime('now', '-1 month') THEN 'Inactive for over a month'
        WHEN post_count = 0 THEN 'No posts created'
        ELSE 'OK'
    END as recommendation
FROM users u
LEFT JOIN (
    SELECT user_id, COUNT(*) as post_count 
    FROM posts 
    GROUP BY user_id
) p ON u.id = p.user_id
WHERE login_count = 0 
   OR last_login < datetime('now', '-1 month')
   OR post_count = 0 OR post_count IS NULL
ORDER BY recommendation, username;
