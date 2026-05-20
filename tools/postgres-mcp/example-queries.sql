-- Query to get recent failed tasks and their source URLs.
SELECT id, created_at, input_info->>'href' AS url
FROM tasks
WHERE status ? 'error'
ORDER BY id DESC;

-- Query to fetch recent tasks created by a specific user email.
SELECT t.id, t.created_at, t.input_info->>'href' AS url
FROM tasks t
JOIN users u ON u.user_id = t.user_id
WHERE u.email = '<email-address>'
ORDER BY t.created_at DESC;

-- Query to group failures by day for the last two weeks.
SELECT
    date_trunc('day', created_at) AS day,
    COUNT(*) FILTER (WHERE status ? 'error') AS failed_tasks,
    COUNT(*) AS total_tasks,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE status ? 'error') / NULLIF(COUNT(*), 0),
        2
    ) AS failure_percentage
FROM tasks
WHERE created_at >= NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1;