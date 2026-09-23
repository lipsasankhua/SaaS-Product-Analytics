-- ============================================
-- 06. REVENUE ANALYSIS
-- ============================================
-- Realized revenue over time, ARPU/LTV by plan, revenue at risk from
-- failed payments, and whether report_export power users are worth
-- more over their lifetime -- ties the feature signal from
-- 05_feature_analysis.sql to the bottom line.
-- ============================================


-- --------------------------------------------
-- 6a. Monthly recurring revenue (realized, succeeded payments only)
-- --------------------------------------------
SELECT
    DATE_TRUNC('month', payment_date)::DATE AS month,
    SUM(amount) FILTER (WHERE status = 'succeeded')   AS mrr,
    COUNT(*) FILTER (WHERE status = 'succeeded')       AS successful_payments,
    COUNT(*) FILTER (WHERE status = 'failed')          AS failed_payments
FROM payments
GROUP BY month
ORDER BY month;


-- --------------------------------------------
-- 6b. Revenue and ARPU by plan
-- --------------------------------------------
SELECT
    s.plan,
    COUNT(DISTINCT p.subscription_id) AS paying_subscriptions,
    SUM(p.amount) FILTER (WHERE p.status = 'succeeded') AS total_revenue,
    ROUND(
        SUM(p.amount) FILTER (WHERE p.status = 'succeeded') / COUNT(DISTINCT p.subscription_id), 2
    ) AS revenue_per_subscription,
    ROUND(
        100.0 * SUM(p.amount) FILTER (WHERE p.status = 'succeeded')
        / SUM(SUM(p.amount) FILTER (WHERE p.status = 'succeeded')) OVER (), 1
    ) AS pct_of_total_revenue
FROM subscriptions s
JOIN payments p ON p.subscription_id = s.subscription_id
GROUP BY s.plan
ORDER BY total_revenue DESC;


-- --------------------------------------------
-- 6c. LTV proxy by plan: total realized revenue per subscription
-- over its lifetime so far in this dataset.
-- --------------------------------------------
WITH sub_revenue AS (
    SELECT
        s.subscription_id,
        s.plan,
        COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'succeeded'), 0) AS lifetime_revenue
    FROM subscriptions s
    JOIN payments p ON p.subscription_id = s.subscription_id
    GROUP BY s.subscription_id, s.plan
)
SELECT
    plan,
    COUNT(*) AS subscriptions,
    ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lifetime_revenue))::NUMERIC, 2) AS median_ltv
FROM sub_revenue
GROUP BY plan
ORDER BY plan;


-- --------------------------------------------
-- 6d. Revenue at risk from failed payments
-- --------------------------------------------
SELECT
    SUM(amount) FILTER (WHERE status = 'succeeded') AS realized_revenue,
    SUM(amount) FILTER (WHERE status = 'failed')     AS revenue_at_risk,
    ROUND(100.0 * SUM(amount) FILTER (WHERE status = 'failed') / SUM(amount), 2) AS pct_of_billed_revenue_lost
FROM payments;


-- --------------------------------------------
-- 6e. LTV: report_export power users vs everyone else
-- Ties the feature signal from 05_feature_analysis.sql (power users
-- convert more AND churn less) to actual dollars: do they also
-- generate more lifetime revenue per paying user?
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
sub_revenue AS (
    SELECT
        a.user_id,
        COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'succeeded'), 0) AS lifetime_revenue
    FROM subscriptions s
    JOIN accounts a ON a.account_id = s.account_id
    JOIN payments p ON p.subscription_id = s.subscription_id
    GROUP BY a.user_id
)
SELECT
    p.is_power_user,
    COUNT(sr.user_id) AS paying_users,
    ROUND(AVG(sr.lifetime_revenue), 2) AS avg_ltv
FROM power_users p
JOIN sub_revenue sr ON sr.user_id = p.user_id
GROUP BY p.is_power_user
ORDER BY p.is_power_user DESC;
