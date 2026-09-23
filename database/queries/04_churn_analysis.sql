-- ============================================
-- 04. CHURN ANALYSIS
-- ============================================
-- Who cancels, how fast, and whether the seeded "power users churn
-- less" signal (config.py: POWER_USER_RETENTION_LIFT) shows up.
--
-- A subscription is only counted as "churned" here if it canceled
-- AFTER its trial converted to paid (canceled_at > trial_end_at).
-- A subscription with canceled_at == trial_end_at is a trial that
-- expired without ever becoming a paying customer -- not churn, since
-- there was nothing to churn from. See seed.sql / subscriptions.py.
-- ============================================


-- --------------------------------------------
-- 4a. Post-conversion churn rate by plan
-- --------------------------------------------
SELECT
    plan,
    COUNT(*) AS ever_paid_subscriptions,
    COUNT(*) FILTER (WHERE canceled_at > trial_end_at) AS churned,
    ROUND(100.0 * COUNT(*) FILTER (WHERE canceled_at > trial_end_at) / COUNT(*), 1) AS churn_rate_pct
FROM subscriptions
WHERE status = 'active' OR canceled_at > trial_end_at
GROUP BY plan
ORDER BY churn_rate_pct DESC;


-- --------------------------------------------
-- 4b. Time-to-churn: how long paying subscribers last before canceling
-- (in months since their trial converted to paid)
-- --------------------------------------------
SELECT
    plan,
    ROUND(AVG(EXTRACT(EPOCH FROM (canceled_at - trial_end_at)) / (30 * 86400))::NUMERIC, 1) AS avg_months_to_churn,
    ROUND(
        (PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (canceled_at - trial_end_at)) / (30 * 86400)
        ))::NUMERIC, 1
    ) AS median_months_to_churn,
    COUNT(*) AS churned_subscriptions
FROM subscriptions
WHERE canceled_at > trial_end_at
GROUP BY plan
ORDER BY plan;


-- --------------------------------------------
-- 4c. Churn rate: power users vs everyone else
-- Power user = used the key feature (report_export) >= 5 times total,
-- checked across their whole event history (not just pre-trial).
-- Confirms whether POWER_USER_RETENTION_LIFT actually reduced churn.
-- --------------------------------------------
WITH key_feature_totals AS (
    SELECT user_id, COUNT(*) AS kf_uses
    FROM events
    WHERE event_type = 'feature_used' AND feature = 'report_export'
    GROUP BY user_id
),
paid_users AS (
    SELECT
        a.user_id,
        s.canceled_at,
        s.trial_end_at,
        COALESCE(k.kf_uses, 0) >= 5 AS is_power_user
    FROM subscriptions s
    JOIN accounts a ON a.account_id = s.account_id
    LEFT JOIN key_feature_totals k ON k.user_id = a.user_id
    WHERE s.status = 'active' OR s.canceled_at > s.trial_end_at
)
SELECT
    is_power_user,
    COUNT(*) AS paid_subscribers,
    COUNT(*) FILTER (WHERE canceled_at > trial_end_at) AS churned,
    ROUND(100.0 * COUNT(*) FILTER (WHERE canceled_at > trial_end_at) / COUNT(*), 1) AS churn_rate_pct
FROM paid_users
GROUP BY is_power_user
ORDER BY is_power_user DESC;


-- --------------------------------------------
-- 4d. Failed payments leading up to cancellation
-- Do canceled subscriptions show more payment failures beforehand
-- than ones that are still active? A common leading indicator of churn.
-- --------------------------------------------
SELECT
    s.status,
    COUNT(DISTINCT s.subscription_id) AS subscriptions,
    COUNT(p.payment_id) FILTER (WHERE p.status = 'failed') AS failed_payments,
    ROUND(
        COUNT(p.payment_id) FILTER (WHERE p.status = 'failed')::NUMERIC
        / NULLIF(COUNT(DISTINCT s.subscription_id), 0), 2
    ) AS avg_failed_payments_per_sub
FROM subscriptions s
JOIN payments p ON p.subscription_id = s.subscription_id
GROUP BY s.status;
