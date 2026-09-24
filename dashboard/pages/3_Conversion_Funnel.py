"""Conversion Funnel -- signup-to-paid drop-off, overall and by channel."""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

from charts import funnel_chart
from db import run_query

st.set_page_config(page_title="Conversion Funnel", layout="wide")
st.title("Conversion Funnel")
st.caption(
    "\"Activated\" is a derived state (>= 3 report_export uses within 7 days "
    "of signup), computed from feature_used events -- not a stored event."
)

FUNNEL_CTE = """
    WITH funnel_events AS (
        SELECT
            user_id,
            MAX(event_timestamp) FILTER (WHERE event_type = 'signup')               AS signup_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'email_verified')       AS verified_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'onboarding_completed') AS onboarded_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'trial_started')        AS trial_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'subscription_started') AS paid_at
        FROM events
        GROUP BY user_id
    ),
    key_feature_uses AS (
        SELECT user_id, event_timestamp FROM events
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
            f.verified_at IS NOT NULL  AS reached_verified,
            f.onboarded_at IS NOT NULL AS reached_onboarded,
            a.is_activated             AS reached_activated,
            f.trial_at IS NOT NULL     AS reached_trial,
            f.paid_at IS NOT NULL      AS reached_paid
        FROM funnel_events f
        JOIN activation a ON a.user_id = f.user_id
    )
"""

st.subheader("Overall funnel")
funnel = run_query(FUNNEL_CTE + """
    SELECT 1 AS stage_order, 'signup' AS stage, COUNT(*) AS users FROM funnel
    UNION ALL SELECT 2, 'email_verified', COUNT(*) FILTER (WHERE reached_verified) FROM funnel
    UNION ALL SELECT 3, 'onboarding_completed', COUNT(*) FILTER (WHERE reached_onboarded) FROM funnel
    UNION ALL SELECT 4, 'activated', COUNT(*) FILTER (WHERE reached_activated) FROM funnel
    UNION ALL SELECT 5, 'trial_started', COUNT(*) FILTER (WHERE reached_trial) FROM funnel
    UNION ALL SELECT 6, 'subscription_started', COUNT(*) FILTER (WHERE reached_paid) FROM funnel
    ORDER BY stage_order
""")
st.plotly_chart(funnel_chart(funnel, "stage", "users", "Signup-to-Paid Funnel"), width="stretch")

st.subheader("Funnel by acquisition channel")
by_channel = run_query(FUNNEL_CTE + """
    SELECT
        u.acquisition_channel,
        COUNT(*)                                   AS signups,
        COUNT(*) FILTER (WHERE f.reached_verified)  AS verified,
        COUNT(*) FILTER (WHERE f.reached_onboarded) AS onboarded,
        COUNT(*) FILTER (WHERE f.reached_activated) AS activated,
        COUNT(*) FILTER (WHERE f.reached_trial)     AS trial_started,
        COUNT(*) FILTER (WHERE f.reached_paid)      AS subscription_started,
        ROUND(100.0 * COUNT(*) FILTER (WHERE f.reached_paid) / COUNT(*), 2) AS signup_to_paid_pct
    FROM funnel f
    JOIN users u ON u.user_id = f.user_id
    GROUP BY u.acquisition_channel
    ORDER BY signup_to_paid_pct DESC
""")
st.dataframe(by_channel, width="stretch", hide_index=True)

st.subheader("Funnel velocity")
st.caption("Median time spent between consecutive stages")
velocity = run_query("""
    WITH funnel_events AS (
        SELECT
            user_id,
            MAX(event_timestamp) FILTER (WHERE event_type = 'signup')               AS signup_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'email_verified')       AS verified_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'onboarding_completed') AS onboarded_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'trial_started')        AS trial_at,
            MAX(event_timestamp) FILTER (WHERE event_type = 'subscription_started') AS paid_at
        FROM events
        GROUP BY user_id
    )
    SELECT
        ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (verified_at - signup_at)) / 3600
        ))::NUMERIC, 1) AS median_hours_signup_to_verified,
        ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (onboarded_at - verified_at)) / 3600
        ))::NUMERIC, 1) AS median_hours_verified_to_onboarded,
        ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (trial_at - onboarded_at)) / 86400
        ))::NUMERIC, 1) AS median_days_onboarded_to_trial,
        ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (paid_at - trial_at)) / 86400
        ))::NUMERIC, 1) AS median_days_trial_to_paid
    FROM funnel_events
""")
st.dataframe(velocity, width="stretch", hide_index=True)
