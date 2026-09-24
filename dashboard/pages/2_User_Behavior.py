"""User Behavior -- acquisition, activation, and feature adoption."""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

from charts import bar_chart, line_chart
from db import run_query

st.set_page_config(page_title="User Behavior", layout="wide")
st.title("User Behavior")

st.subheader("Signup growth")
signups = run_query("""
    SELECT DATE_TRUNC('month', signup_date)::DATE AS signup_month, COUNT(*) AS new_users
    FROM users
    GROUP BY signup_month
    ORDER BY signup_month
""")
st.plotly_chart(line_chart(signups, "signup_month", "new_users", "Monthly Signups"), width="stretch")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Acquisition channel")
    channels = run_query("""
        SELECT acquisition_channel, COUNT(*) AS users
        FROM users
        GROUP BY acquisition_channel
        ORDER BY users DESC
    """)
    st.plotly_chart(
        bar_chart(channels, "acquisition_channel", "users", "Signups by Channel"),
        width="stretch",
    )

with col2:
    st.subheader("Activation rate by channel")
    st.caption("Activated = >= 3 report_export uses within 7 days of signup")
    activation = run_query("""
        WITH signup_ts AS (
            SELECT user_id, event_timestamp AS signup_at FROM events WHERE event_type = 'signup'
        ),
        key_feature_uses AS (
            SELECT user_id, event_timestamp FROM events
            WHERE event_type = 'feature_used' AND feature = 'report_export'
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
            ROUND(100.0 * COUNT(*) FILTER (WHERE a.is_activated) / COUNT(*), 1) AS activation_rate_pct
        FROM users u
        JOIN activation a ON a.user_id = u.user_id
        GROUP BY u.acquisition_channel
        ORDER BY activation_rate_pct DESC
    """)
    st.plotly_chart(
        bar_chart(activation, "acquisition_channel", "activation_rate_pct", "Activation Rate by Channel", "Activation %"),
        width="stretch",
    )

st.subheader("Feature adoption")
st.caption("report_export is the key feature seeded with a power-user conversion/retention lift")
feature_usage = run_query("""
    SELECT feature, COUNT(DISTINCT user_id) AS distinct_users
    FROM events
    WHERE event_type = 'feature_used'
    GROUP BY feature
    ORDER BY distinct_users DESC
""")
st.plotly_chart(
    bar_chart(feature_usage, "feature", "distinct_users", "Feature Adoption (Distinct Users)"),
    width="stretch",
)
