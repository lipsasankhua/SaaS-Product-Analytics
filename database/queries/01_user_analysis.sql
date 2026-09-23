-- ============================================
-- 01. USER ANALYSIS
-- ============================================
-- Who signs up, where they come from, and how many actually activate.
--
-- "Activated" is a DERIVED state, not a stored event (see
-- docs/event_taxonomy.md): a user who used the key feature
-- (report_export) at least 3 times within 7 days of their signup
-- event. It's computed fresh in each query below from feature_used
-- events, the way a real analytics stack would, rather than trusting
-- a stored flag.
-- ============================================


-- --------------------------------------------
-- 1a. Monthly signup trend + cumulative user growth
-- --------------------------------------------
SELECT
    DATE_TRUNC('month', signup_date)::DATE AS signup_month,
    COUNT(*) AS new_users,
    SUM(COUNT(*)) OVER (ORDER BY DATE_TRUNC('month', signup_date)::DATE) AS cumulative_users
FROM users
GROUP BY DATE_TRUNC('month', signup_date)::DATE
ORDER BY signup_month;


-- --------------------------------------------
-- 1b. Acquisition channel performance
-- Signup volume and share of total by channel.
-- --------------------------------------------
SELECT
    acquisition_channel,
    COUNT(*) AS users,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_total
FROM users
GROUP BY acquisition_channel
ORDER BY users DESC;


-- --------------------------------------------
-- 1c. User base breakdown by device and country
-- --------------------------------------------
SELECT
    device,
    country,
    COUNT(*) AS users
FROM users
GROUP BY device, country
ORDER BY device, users DESC;


-- --------------------------------------------
-- 1d. Activation rate (overall)
-- Activated = >= 3 uses of the key feature (report_export) within
-- 7 days of the user's signup event.
-- --------------------------------------------
WITH signup_ts AS (
    SELECT user_id, event_timestamp AS signup_at
    FROM events
    WHERE event_type = 'signup'
),
key_feature_uses AS (
    SELECT user_id, event_timestamp
    FROM events
    WHERE event_type = 'feature_used'
      AND feature = 'report_export'
),
activation AS (
    SELECT
        s.user_id,
        COUNT(k.event_timestamp) FILTER (
            WHERE k.event_timestamp BETWEEN s.signup_at AND s.signup_at + INTERVAL '7 days'
        ) >= 3 AS is_activated
    FROM signup_ts s
    LEFT JOIN key_feature_uses k ON k.user_id = s.user_id
    GROUP BY s.user_id, s.signup_at
)
SELECT
    COUNT(*) AS total_users,
    COUNT(*) FILTER (WHERE is_activated) AS activated_users,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_activated) / COUNT(*), 1) AS activation_rate_pct
FROM activation;


-- --------------------------------------------
-- 1e. Activation rate by acquisition channel and device
-- Surfaces which acquisition channels bring users who actually
-- reach activation, not just users who sign up.
-- --------------------------------------------
WITH signup_ts AS (
    SELECT user_id, event_timestamp AS signup_at
    FROM events
    WHERE event_type = 'signup'
),
key_feature_uses AS (
    SELECT user_id, event_timestamp
    FROM events
    WHERE event_type = 'feature_used'
      AND feature = 'report_export'
),
activation AS (
    SELECT
        s.user_id,
        COUNT(k.event_timestamp) FILTER (
            WHERE k.event_timestamp BETWEEN s.signup_at AND s.signup_at + INTERVAL '7 days'
        ) >= 3 AS is_activated
    FROM signup_ts s
    LEFT JOIN key_feature_uses k ON k.user_id = s.user_id
    GROUP BY s.user_id, s.signup_at
)
SELECT
    u.acquisition_channel,
    u.device,
    COUNT(*) AS users,
    COUNT(*) FILTER (WHERE a.is_activated) AS activated_users,
    ROUND(100.0 * COUNT(*) FILTER (WHERE a.is_activated) / COUNT(*), 1) AS activation_rate_pct
FROM users u
JOIN activation a ON a.user_id = u.user_id
GROUP BY u.acquisition_channel, u.device
ORDER BY activation_rate_pct DESC;
