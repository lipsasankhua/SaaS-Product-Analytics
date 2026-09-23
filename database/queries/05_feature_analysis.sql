-- ============================================
-- 05. FEATURE ANALYSIS -- the centerpiece
-- ============================================
-- config.py seeds one deliberate signal: users who become "power
-- users" of report_export (>= 5 total uses) get a real conversion
-- and retention lift (POWER_USER_CONVERSION_LIFT, POWER_USER_RETENTION_LIFT).
-- This file "discovers" that signal from the events table the way a
-- real analyst would -- without knowing in advance which feature it is
-- -- and checks it's specific to report_export, not just a "heavy
-- feature users convert more" artifact.
-- ============================================


-- --------------------------------------------
-- 5a. Feature usage popularity (adoption + intensity)
-- --------------------------------------------
SELECT
    feature,
    COUNT(*) AS total_uses,
    COUNT(DISTINCT user_id) AS distinct_users,
    ROUND(COUNT(*)::NUMERIC / COUNT(DISTINCT user_id), 1) AS avg_uses_per_user
FROM events
WHERE event_type = 'feature_used'
GROUP BY feature
ORDER BY distinct_users DESC;


-- --------------------------------------------
-- 5b. Cross-feature specificity check
-- For EVERY feature, compare signup-to-paid conversion between users
-- who used that feature >= 5 times ("power users" of it) and everyone
-- else. If the seeded signal is specific to one feature, only that
-- feature should show a meaningfully wider gap than the others.
--
-- NOTE: usage of the non-key features is randomized per user (0-10
-- uses), so hitting >= 5 on any of them is rare -- expect only a
-- handful of "power users" for those, versus hundreds for
-- report_export. Their conversion %s are small-sample noise; the
-- power_user COUNT itself (685 vs. single digits) is the real tell
-- that report_export is where the signal lives.
-- --------------------------------------------
WITH feature_list(feature) AS (
    VALUES ('dashboard_view'), ('report_export'), ('team_invite'),
           ('integration_setup'), ('api_usage'), ('custom_alert')
),
feature_use_counts AS (
    SELECT feature, user_id, COUNT(*) AS uses
    FROM events
    WHERE event_type = 'feature_used'
    GROUP BY feature, user_id
),
per_feature AS (
    SELECT
        fl.feature,
        u.user_id,
        COALESCE(fuc.uses, 0) >= 5 AS is_power_user
    FROM feature_list fl
    CROSS JOIN users u
    LEFT JOIN feature_use_counts fuc
        ON fuc.feature = fl.feature AND fuc.user_id = u.user_id
),
converted AS (
    SELECT DISTINCT user_id FROM events WHERE event_type = 'subscription_started'
)
SELECT
    pf.feature,
    COUNT(*) FILTER (WHERE is_power_user)     AS power_users,
    COUNT(*) FILTER (WHERE NOT is_power_user) AS non_power_users,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_power_user AND c.user_id IS NOT NULL)
        / NULLIF(COUNT(*) FILTER (WHERE is_power_user), 0), 1)     AS power_user_conversion_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE NOT is_power_user AND c.user_id IS NOT NULL)
        / NULLIF(COUNT(*) FILTER (WHERE NOT is_power_user), 0), 1) AS non_power_user_conversion_pct
FROM per_feature pf
LEFT JOIN converted c ON c.user_id = pf.user_id
GROUP BY pf.feature
ORDER BY power_user_conversion_pct DESC;


-- --------------------------------------------
-- 5c. The discovered signal, quantified
-- Observed conversion lift for report_export power users vs everyone
-- else. Note this comes out much bigger than the seeded per-stage
-- POWER_USER_CONVERSION_LIFT (1.8x): funnel.py applies that 1.8x
-- multiplier at EACH of the 5 funnel stages (signup->verified
-- through activated->trial->paid), so the lift compounds across the
-- whole funnel rather than applying once -- an ~10x overall lift from
-- a ~1.8x per-stage lift is expected, not a bug.
-- --------------------------------------------
WITH key_feature_totals AS (
    SELECT user_id, COUNT(*) AS kf_uses
    FROM events
    WHERE event_type = 'feature_used' AND feature = 'report_export'
    GROUP BY user_id
),
power_users AS (
    SELECT u.user_id, COALESCE(k.kf_uses, 0) >= 5 AS is_power_user
    FROM users u
    LEFT JOIN key_feature_totals k ON k.user_id = u.user_id
),
converted AS (
    SELECT DISTINCT user_id FROM events WHERE event_type = 'subscription_started'
),
conversion_summary AS (
    SELECT
        p.is_power_user,
        COUNT(*) AS users,
        COUNT(c.user_id) AS converted
    FROM power_users p
    LEFT JOIN converted c ON c.user_id = p.user_id
    GROUP BY p.is_power_user
)
SELECT
    p_true.users  AS power_users,
    p_true.converted  AS power_users_converted,
    ROUND(100.0 * p_true.converted / p_true.users, 1)   AS power_user_conversion_pct,
    p_false.users AS other_users,
    p_false.converted AS other_users_converted,
    ROUND(100.0 * p_false.converted / p_false.users, 1) AS other_user_conversion_pct,
    ROUND(
        (p_true.converted::NUMERIC / p_true.users) / (p_false.converted::NUMERIC / p_false.users)
    , 2) AS observed_conversion_lift_ratio
FROM conversion_summary p_true
CROSS JOIN conversion_summary p_false
WHERE p_true.is_power_user = TRUE AND p_false.is_power_user = FALSE;
