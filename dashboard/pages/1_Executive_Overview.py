"""Executive Overview -- top-line KPIs, MRR trend, and funnel snapshot."""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

from charts import funnel_chart, line_chart
from db import run_query

st.set_page_config(page_title="Executive Overview", layout="wide")
st.title("Executive Overview")

kpis = run_query("""
    WITH funnel_events AS (
        SELECT
            user_id,
            MAX(event_timestamp) FILTER (WHERE event_type = 'signup')               AS signup_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'subscription_started') AS paid_at
        FROM events
        GROUP BY user_id
    )
    SELECT
        (SELECT COUNT(*) FROM users) AS total_users,
        ROUND(100.0 * COUNT(*) FILTER (WHERE paid_at IS NOT NULL) / COUNT(*), 1) AS signup_to_paid_pct,
        (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE canceled_at > trial_end_at) / COUNT(*), 1)
         FROM subscriptions WHERE status = 'active' OR canceled_at > trial_end_at) AS churn_rate_pct,
        (SELECT COALESCE(SUM(amount), 0) FROM payments
         WHERE status = 'succeeded' AND payment_date >= (SELECT MAX(payment_date) FROM payments) - 30
        ) AS trailing_30d_revenue
    FROM funnel_events
""")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Users", f"{kpis['total_users'][0]:,}")
col2.metric("Signup -> Paid", f"{kpis['signup_to_paid_pct'][0]}%")
col3.metric("Post-Conversion Churn", f"{kpis['churn_rate_pct'][0]}%")
col4.metric("Trailing 30d Revenue", f"${kpis['trailing_30d_revenue'][0]:,.0f}")

st.divider()

mrr = run_query("""
    SELECT
        DATE_TRUNC('month', payment_date)::DATE AS month,
        SUM(amount) FILTER (WHERE status = 'succeeded') AS mrr
    FROM payments
    GROUP BY month
    ORDER BY month
""")
st.plotly_chart(line_chart(mrr, "month", "mrr", "Monthly Recurring Revenue", "MRR ($)"), width="stretch")

funnel = run_query("""
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
    SELECT 1 AS stage_order, 'signup' AS stage, COUNT(*) AS users FROM funnel_events
    UNION ALL SELECT 2, 'email_verified', COUNT(*) FILTER (WHERE verified_at IS NOT NULL) FROM funnel_events
    UNION ALL SELECT 3, 'onboarding_completed', COUNT(*) FILTER (WHERE onboarded_at IS NOT NULL) FROM funnel_events
    UNION ALL SELECT 4, 'trial_started', COUNT(*) FILTER (WHERE trial_at IS NOT NULL) FROM funnel_events
    UNION ALL SELECT 5, 'subscription_started', COUNT(*) FILTER (WHERE paid_at IS NOT NULL) FROM funnel_events
    ORDER BY stage_order
""")
st.plotly_chart(funnel_chart(funnel, "stage", "users", "Signup-to-Paid Funnel"), width="stretch")
