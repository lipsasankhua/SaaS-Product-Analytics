-- ============================================
-- 03. RETENTION ANALYSIS
-- ============================================
-- Cohort retention curves, DAU/MAU stickiness, and a check of whether
-- the seeded "power users retain more" signal (config.py:
-- POWER_USER_RETENTION_LIFT) actually shows up in session activity.
--
-- "Active" here means "had at least one session" -- sessions are
-- ongoing product usage, independent of the funnel milestone events
-- used in 01/02.
--
-- NOTE ON MAGNITUDE: absolute retention % here runs high (non-power
-- users still show ~74% at D30) because sessions.py spreads a user's
-- sessions uniformly across their whole tenure window rather than
-- modeling decay over time -- it's a flat-engagement simplification,
-- not a realistic churn-of-usage curve. The relative signal (power
-- users retain more, per POWER_USER_RETENTION_LIFT) is still valid
-- and is the intended takeaway from 3c; treat the query logic here,
-- not the exact percentages, as the deliverable.
-- ============================================


-- --------------------------------------------
-- 3a. Weekly cohort retention grid
-- For each signup-week cohort, % of that cohort with >= 1 session in
-- each of the following 8 weeks after signup.
-- --------------------------------------------
WITH cohorts AS (
    SELECT user_id, DATE_TRUNC('week', signup_date)::DATE AS cohort_week
    FROM users
),
cohort_sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_week
),
user_weeks AS (
    SELECT DISTINCT
        s.user_id,
        c.cohort_week,
        FLOOR(EXTRACT(EPOCH FROM (s.started_at - c.cohort_week)) / (7 * 86400))::INT AS week_number
    FROM sessions s
    JOIN cohorts c ON c.user_id = s.user_id
    WHERE s.started_at >= c.cohort_week
)
SELECT
    c.cohort_week,
    cs.cohort_size,
    uw.week_number,
    COUNT(DISTINCT uw.user_id) AS active_users,
    ROUND(100.0 * COUNT(DISTINCT uw.user_id) / cs.cohort_size, 1) AS retention_pct
FROM cohort_sizes cs
JOIN cohorts c ON c.cohort_week = cs.cohort_week
JOIN user_weeks uw ON uw.user_id = c.user_id AND uw.cohort_week = c.cohort_week
WHERE uw.week_number BETWEEN 0 AND 8
GROUP BY c.cohort_week, cs.cohort_size, uw.week_number
ORDER BY c.cohort_week, uw.week_number;


-- --------------------------------------------
-- 3b. DAU/MAU stickiness by month
-- Average daily active users as a % of monthly active users --
-- a standard proxy for how habitual product usage is.
-- --------------------------------------------
WITH daily_actives AS (
    SELECT DATE(started_at) AS day, COUNT(DISTINCT user_id) AS dau
    FROM sessions
    GROUP BY DATE(started_at)
),
avg_dau_by_month AS (
    SELECT DATE_TRUNC('month', day)::DATE AS month, AVG(dau) AS avg_dau
    FROM daily_actives
    GROUP BY DATE_TRUNC('month', day)::DATE
),
monthly_actives AS (
    SELECT DATE_TRUNC('month', started_at)::DATE AS month, COUNT(DISTINCT user_id) AS mau
    FROM sessions
    GROUP BY DATE_TRUNC('month', started_at)::DATE
)
SELECT
    m.month,
    ROUND(a.avg_dau) AS avg_dau,
    m.mau,
    ROUND(100.0 * a.avg_dau / m.mau, 1) AS stickiness_pct
FROM monthly_actives m
JOIN avg_dau_by_month a ON a.month = m.month
ORDER BY m.month;


-- --------------------------------------------
-- 3c. Day-30 retention: power users vs everyone else
-- Power user = used the key feature (report_export) >= 5 times total.
-- Retained at day 30 = had a session 30-37 days after signup.
-- --------------------------------------------
WITH signup_ts AS (
    SELECT user_id, event_timestamp AS signup_at
    FROM events
    WHERE event_type = 'signup'
),
key_feature_totals AS (
    SELECT user_id, COUNT(*) AS kf_uses
    FROM events
    WHERE event_type = 'feature_used' AND feature = 'report_export'
    GROUP BY user_id
),
retention AS (
    SELECT
        s.user_id,
        COALESCE(k.kf_uses, 0) >= 5 AS is_power_user,
        EXISTS (
            SELECT 1
            FROM sessions se
            WHERE se.user_id = s.user_id
              AND se.started_at BETWEEN s.signup_at + INTERVAL '30 days'
                                    AND s.signup_at + INTERVAL '37 days'
        ) AS retained_day30
    FROM signup_ts s
    LEFT JOIN key_feature_totals k ON k.user_id = s.user_id
)
SELECT
    is_power_user,
    COUNT(*) AS users,
    COUNT(*) FILTER (WHERE retained_day30) AS retained,
    ROUND(100.0 * COUNT(*) FILTER (WHERE retained_day30) / COUNT(*), 1) AS day30_retention_pct
FROM retention
GROUP BY is_power_user
ORDER BY is_power_user DESC;
