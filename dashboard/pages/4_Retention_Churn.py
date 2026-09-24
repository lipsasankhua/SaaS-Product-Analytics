"""Retention & Churn -- cohort retention, DAU/MAU stickiness, and churn."""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

from charts import bar_chart, heatmap, line_chart
from db import run_query

st.set_page_config(page_title="Retention & Churn", layout="wide")
st.title("Retention & Churn")
st.info(
    "Absolute retention % runs high across the board because sessions are "
    "spread uniformly across a user's whole tenure rather than decaying over "
    "time (see `sessions.py`). Treat the relative power-user lift below as "
    "the signal, not the exact percentages.",
    icon="ℹ️",
)

st.subheader("Cohort retention")
cohort = run_query("""
    WITH cohorts AS (
        SELECT user_id, DATE_TRUNC('month', signup_date)::DATE AS cohort_month
        FROM users
    ),
    cohort_sizes AS (
        SELECT cohort_month, COUNT(*) AS cohort_size FROM cohorts GROUP BY cohort_month
    ),
    user_weeks AS (
        SELECT DISTINCT
            s.user_id,
            c.cohort_month,
            FLOOR(EXTRACT(EPOCH FROM (s.started_at - c.cohort_month)) / (7 * 86400))::INT AS week_number
        FROM sessions s
        JOIN cohorts c ON c.user_id = s.user_id
        WHERE s.started_at >= c.cohort_month
    )
    SELECT
        c.cohort_month,
        uw.week_number,
        ROUND(100.0 * COUNT(DISTINCT uw.user_id) / cs.cohort_size, 1) AS retention_pct
    FROM cohort_sizes cs
    JOIN cohorts c ON c.cohort_month = cs.cohort_month
    JOIN user_weeks uw ON uw.user_id = c.user_id AND uw.cohort_month = c.cohort_month
    WHERE uw.week_number BETWEEN 0 AND 8
    GROUP BY c.cohort_month, cs.cohort_size, uw.week_number
    ORDER BY c.cohort_month, uw.week_number
""")
pivot = cohort.pivot(index="cohort_month", columns="week_number", values="retention_pct")
st.plotly_chart(
    heatmap(pivot, "Monthly Cohort Retention (% active by week)", "Weeks since signup", "Signup cohort", "Retention %"),
    width="stretch",
)

st.subheader("DAU/MAU stickiness")
stickiness = run_query("""
    WITH daily_actives AS (
        SELECT DATE(started_at) AS day, COUNT(DISTINCT user_id) AS dau
        FROM sessions GROUP BY DATE(started_at)
    ),
    avg_dau_by_month AS (
        SELECT DATE_TRUNC('month', day)::DATE AS month, AVG(dau) AS avg_dau
        FROM daily_actives GROUP BY DATE_TRUNC('month', day)::DATE
    ),
    monthly_actives AS (
        SELECT DATE_TRUNC('month', started_at)::DATE AS month, COUNT(DISTINCT user_id) AS mau
        FROM sessions GROUP BY DATE_TRUNC('month', started_at)::DATE
    )
    SELECT m.month, ROUND(100.0 * a.avg_dau / m.mau, 1) AS stickiness_pct
    FROM monthly_actives m
    JOIN avg_dau_by_month a ON a.month = m.month
    ORDER BY m.month
""")
st.plotly_chart(
    line_chart(stickiness, "month", "stickiness_pct", "DAU/MAU Stickiness", "Stickiness %"),
    width="stretch",
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Churn by plan")
    st.caption("Post-conversion churn only -- excludes trials that expired without ever converting")
    churn_by_plan = run_query("""
        SELECT
            plan,
            ROUND(100.0 * COUNT(*) FILTER (WHERE canceled_at > trial_end_at) / COUNT(*), 1) AS churn_rate_pct
        FROM subscriptions
        WHERE status = 'active' OR canceled_at > trial_end_at
        GROUP BY plan
    """)
    st.plotly_chart(
        bar_chart(churn_by_plan, "plan", "churn_rate_pct", "Post-Conversion Churn Rate by Plan", "Churn %"),
        width="stretch",
    )

with col2:
    st.subheader("Churn: power users vs everyone else")
    st.caption("Power user = >= 5 total report_export uses")
    power_user_churn = run_query("""
        WITH key_feature_totals AS (
            SELECT user_id, COUNT(*) AS kf_uses FROM events
            WHERE event_type = 'feature_used' AND feature = 'report_export'
            GROUP BY user_id
        ),
        paid_users AS (
            SELECT
                a.user_id, s.canceled_at, s.trial_end_at,
                COALESCE(k.kf_uses, 0) >= 5 AS is_power_user
            FROM subscriptions s
            JOIN accounts a ON a.account_id = s.account_id
            LEFT JOIN key_feature_totals k ON k.user_id = a.user_id
            WHERE s.status = 'active' OR s.canceled_at > s.trial_end_at
        )
        SELECT
            CASE WHEN is_power_user THEN 'power user' ELSE 'everyone else' END AS segment,
            ROUND(100.0 * COUNT(*) FILTER (WHERE canceled_at > trial_end_at) / COUNT(*), 1) AS churn_rate_pct
        FROM paid_users
        GROUP BY is_power_user
    """)
    st.plotly_chart(
        bar_chart(power_user_churn, "segment", "churn_rate_pct", "Churn: Power Users vs Everyone Else", "Churn %"),
        width="stretch",
    )
