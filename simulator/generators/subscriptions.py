"""
Generates the subscriptions table, built directly on top of the shared
per-user journey from funnel.py so it's consistent with events.py.
"""

import pandas as pd
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from funnel import simulate_user_journey


def generate_subscriptions(users_df: pd.DataFrame, accounts_df: pd.DataFrame) -> pd.DataFrame:
    """
    For every account that reaches "trial_started" or beyond in its
    simulated journey, create a subscription record.

    Returns a DataFrame with columns:
    subscription_id, account_id, plan, status, started_at, trial_end_at, canceled_at

    Also returns (as a module-level side output via generate_journeys)
    the per-user journey dict, since events.py will need the exact same
    timestamps to build consistent event rows.
    """
    records = []
    journeys = {}  # user_id -> journey dict, reused by events.py
    subscription_id = 1

    accounts_by_user = accounts_df.set_index("user_id")

    for row in users_df.itertuples(index=False):
        account = accounts_by_user.loc[row.user_id]
        signup_datetime = datetime.combine(row.signup_date, datetime.min.time())

        journey = simulate_user_journey(
            user_id=row.user_id,
            signup_datetime=signup_datetime,
            plan=account["plan"],
        )
        journeys[row.user_id] = journey

        if "trial_started" not in journey["timestamps"]:
            continue  # never reached trial -> no subscription record

        trial_start = journey["timestamps"]["trial_started"]
        trial_end = trial_start + timedelta(days=14)
        converted = journey["converted_to_paid"]

        if converted:
            status = "canceled" if journey["canceled_at"] else "active"
        else:
            status = "canceled"  # trial expired without converting

        records.append({
            "subscription_id": subscription_id,
            "account_id": account["account_id"],
            "plan": account["plan"] if account["plan"] != "free" else "pro",
            "status": status,
            "started_at": trial_start,
            "trial_end_at": trial_end,
            "canceled_at": journey["canceled_at"],
        })
        subscription_id += 1

    df = pd.DataFrame(records)
    return df, journeys


if __name__ == "__main__":
    from users import generate_users
    from accounts import generate_accounts

    users_df = generate_users()
    accounts_df = generate_accounts(users_df)
    subs_df, journeys = generate_subscriptions(users_df, accounts_df)

    print(subs_df.head(10))
    print(f"\nGenerated {len(subs_df)} subscriptions out of {len(users_df)} users")
    print(f"\nStatus breakdown:\n{subs_df['status'].value_counts()}")
    print(f"\nConversion rate (trial -> subscription created): "
          f"{len(subs_df) / len(users_df):.2%}")