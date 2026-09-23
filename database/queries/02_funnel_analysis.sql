-- ============================================
-- 02. FUNNEL ANALYSIS
-- ============================================
-- Drop-off through signup -> email_verified -> onboarding_completed ->
-- activated -> trial_started -> subscription_started.
--
-- "Activated" is a derived state (see docs/event_taxonomy.md), not a
-- stored event: >= 3 uses of the key feature (report_export) within
-- 7 days of signup. Computed fresh from feature_used events, same
-- approach as 01_user_analysis.sql.
-- ============================================


-- --------------------------------------------
-- Shared building block used by every query below: one row per user
-- with their signup timestamp, funnel milestone timestamps, and
-- whether they hit the derived activation threshold.
-- --------------------------------------------
-- (Repeated as a CTE in each query so every query file in this repo
-- runs standalone, without depending on a view defined elsewhere.)


-- --------------------------------------------
-- 2a. Overall funnel: users reaching each stage, with conversion
-- from the previous stage and from the top of the funnel.
-- --------------------------------------------
WITH funnel_events AS (
    SELECT
        user_id,
        MAX(event_timestamp) FILTER (WHERE event_type = 'signup')                AS signup_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'email_verified')        AS verified_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'onboarding_completed')  AS onboarded_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'trial_started')         AS trial_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'subscription_started')  AS paid_at
    FROM events
    GROUP BY user_id
),
key_feature_uses AS (
    SELECT user_id, event_timestamp
    FROM events
    WHERE event_type = 'feature_used' AND feature = 'report_export'
),
activation AS (
    SELECT
        f.user_id,
        COUNT(k.event_timestamp) FILTER (
            WHERE k.event_timestamp BETWEEN f.signup_at AND f.signup_at + INTERVAL '7 days'
        ) >= 3 AS is_activated
    FROM funnel_events f
    LEFT JOIN key_feature_uses k ON k.user_id = f.user_id
    GROUP BY f.user_id, f.signup_at
),
funnel AS (
    SELECT
        f.user_id,
        f.verified_at IS NOT NULL   AS reached_verified,
        f.onboarded_at IS NOT NULL  AS reached_onboarded,
        a.is_activated              AS reached_activated,
        f.trial_at IS NOT NULL      AS reached_trial,
        f.paid_at IS NOT NULL       AS reached_paid
    FROM funnel_events f
    JOIN activation a ON a.user_id = f.user_id
),
funnel_counts AS (
    SELECT 1 AS stage_order, 'signup' AS stage, COUNT(*) AS users FROM funnel
    UNION ALL
    SELECT 2, 'email_verified', COUNT(*) FILTER (WHERE reached_verified) FROM funnel
    UNION ALL
    SELECT 3, 'onboarding_completed', COUNT(*) FILTER (WHERE reached_onboarded) FROM funnel
    UNION ALL
    SELECT 4, 'activated', COUNT(*) FILTER (WHERE reached_activated) FROM funnel
    UNION ALL
    SELECT 5, 'trial_started', COUNT(*) FILTER (WHERE reached_trial) FROM funnel
    UNION ALL
    SELECT 6, 'subscription_started', COUNT(*) FILTER (WHERE reached_paid) FROM funnel
)
SELECT
    stage_order,
    stage,
    users,
    ROUND(100.0 * users / FIRST_VALUE(users) OVER (ORDER BY stage_order), 1) AS pct_of_signups,
    ROUND(100.0 * users / LAG(users) OVER (ORDER BY stage_order), 1)         AS pct_of_previous_stage
FROM funnel_counts
ORDER BY stage_order;


-- --------------------------------------------
-- 2b. Signup-to-paid conversion by acquisition channel
-- Full funnel breakdown per channel, not just top-of-funnel volume --
-- ties back to the activation-by-channel result in 01_user_analysis.sql.
-- --------------------------------------------
WITH funnel_events AS (
    SELECT
        user_id,
        MAX(event_timestamp) FILTER (WHERE event_type = 'signup')                AS signup_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'email_verified')        AS verified_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'onboarding_completed')  AS onboarded_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'trial_started')         AS trial_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'subscription_started')  AS paid_at
    FROM events
    GROUP BY user_id
),
key_feature_uses AS (
    SELECT user_id, event_timestamp
    FROM events
    WHERE event_type = 'feature_used' AND feature = 'report_export'
),
activation AS (
    SELECT
        f.user_id,
        COUNT(k.event_timestamp) FILTER (
            WHERE k.event_timestamp BETWEEN f.signup_at AND f.signup_at + INTERVAL '7 days'
        ) >= 3 AS is_activated
    FROM funnel_events f
    LEFT JOIN key_feature_uses k ON k.user_id = f.user_id
    GROUP BY f.user_id, f.signup_at
),
funnel AS (
    SELECT
        f.user_id,
        f.verified_at IS NOT NULL   AS reached_verified,
        f.onboarded_at IS NOT NULL  AS reached_onboarded,
        a.is_activated              AS reached_activated,
        f.trial_at IS NOT NULL      AS reached_trial,
        f.paid_at IS NOT NULL       AS reached_paid
    FROM funnel_events f
    JOIN activation a ON a.user_id = f.user_id
)
SELECT
    u.acquisition_channel,
    COUNT(*)                                        AS signups,
    COUNT(*) FILTER (WHERE f.reached_verified)       AS verified,
    COUNT(*) FILTER (WHERE f.reached_onboarded)      AS onboarded,
    COUNT(*) FILTER (WHERE f.reached_activated)      AS activated,
    COUNT(*) FILTER (WHERE f.reached_trial)          AS trial_started,
    COUNT(*) FILTER (WHERE f.reached_paid)           AS subscription_started,
    ROUND(100.0 * COUNT(*) FILTER (WHERE f.reached_paid) / COUNT(*), 2) AS signup_to_paid_pct
FROM funnel f
JOIN users u ON u.user_id = f.user_id
GROUP BY u.acquisition_channel
ORDER BY signup_to_paid_pct DESC;


-- --------------------------------------------
-- 2c. Funnel velocity: median time spent between consecutive stages
-- --------------------------------------------
WITH funnel_events AS (
    SELECT
        user_id,
        MAX(event_timestamp) FILTER (WHERE event_type = 'signup')                AS signup_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'email_verified')        AS verified_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'onboarding_completed')  AS onboarded_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'trial_started')         AS trial_at,
        MAX(event_timestamp) FILTER (WHERE event_type = 'subscription_started')  AS paid_at
    FROM events
    GROUP BY user_id
)
SELECT
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (verified_at - signup_at)) / 3600
    ) AS median_hours_signup_to_verified,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (onboarded_at - verified_at)) / 3600
    ) AS median_hours_verified_to_onboarded,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (trial_at - onboarded_at)) / 86400
    ) AS median_days_onboarded_to_trial,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (paid_at - trial_at)) / 86400
    ) AS median_days_trial_to_paid
FROM funnel_events;
