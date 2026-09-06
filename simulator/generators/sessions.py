"""
Generates the sessions table.

Sessions are independent of the funnel/subscription journey logic —
they represent ongoing product usage (browsing, idle time, etc.) rather
than milestone events. Frequency is higher for engaged/power users,
which gives your DAU/MAU and stickiness queries something realistic
to chew on.
"""

import random
import pandas as pd
from datetime import timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    AVG_SESSIONS_PER_ACTIVE_WEEK,
    SESSION_DURATION_MIN_MINUTES,
    SESSION_DURATION_MAX_MINUTES,
    RANDOM_SEED,
)

random.seed(RANDOM_SEED)


def generate_sessions(users_df: pd.DataFrame, journeys: dict) -> pd.DataFrame:
    """
    For every user who at least verified their email, generate session
    rows across their "active window" (signup/verification through churn
    or a fixed horizon if still active).

    Power users get roughly 2x the session frequency of regular users,
    reinforcing the same behavioral signal seeded in events.py.

    Returns a DataFrame with columns:
    session_id, user_id, started_at, ended_at, device
    """
    records = []
    session_id = 1

    for row in users_df.itertuples(index=False):
        journey = journeys[row.user_id]

        if "email_verified" not in journey["timestamps"]:
            continue  # never verified -> effectively never used the product

        window_start = journey["timestamps"]["email_verified"]
        window_end = journey["canceled_at"] or (window_start + timedelta(days=180))
        total_weeks = max((window_end - window_start).days / 7, 1)

        sessions_per_week = AVG_SESSIONS_PER_ACTIVE_WEEK
        if journey["is_power_user"]:
            sessions_per_week *= 2

        n_sessions = max(int(random.gauss(sessions_per_week * total_weeks, total_weeks)), 0)

        for _ in range(n_sessions):
            offset_days = random.uniform(0, (window_end - window_start).days or 1)
            started_at = window_start + timedelta(days=offset_days)
            duration_minutes = random.uniform(
                SESSION_DURATION_MIN_MINUTES, SESSION_DURATION_MAX_MINUTES
            )
            ended_at = started_at + timedelta(minutes=duration_minutes)

            records.append({
                "session_id": session_id,
                "user_id": row.user_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "device": row.device,
            })
            session_id += 1

    df = pd.DataFrame(records)
    df = df.sort_values("started_at").reset_index(drop=True)
    df["session_id"] = range(1, len(df) + 1)  # re-sequence after sort
    return df


if __name__ == "__main__":
    from users import generate_users
    from accounts import generate_accounts
    from subscriptions import generate_subscriptions

    users_df = generate_users()
    accounts_df = generate_accounts(users_df)
    subs_df, journeys = generate_subscriptions(users_df, accounts_df)
    sessions_df = generate_sessions(users_df, journeys)

    print(sessions_df.head(10))
    print(f"\nGenerated {len(sessions_df)} sessions for {len(users_df)} users")
    print(f"\nAvg sessions per user: {len(sessions_df) / len(users_df):.2f}")