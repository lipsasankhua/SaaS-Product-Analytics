"""
Generates the payments table.

Built on top of the subscriptions table (not journeys directly) since
payments are billing events tied to a specific subscription_id, not a
user_id. One payment row per ~30-day billing cycle the subscription
was active, with a small chance of failure per config.PAYMENT_FAILURE_RATE.
"""

import random
import pandas as pd
from datetime import timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PLAN_PRICE, PAYMENT_FAILURE_RATE, RANDOM_SEED

random.seed(RANDOM_SEED)


def generate_payments(subscriptions_df: pd.DataFrame) -> pd.DataFrame:
    """
    For every subscription that started (status in {'active', 'canceled'}
    and has a started_at), generate one payment per billing cycle between
    started_at and canceled_at (or "now"/end-of-simulation if still active).

    Returns a DataFrame with columns:
    payment_id, subscription_id, amount, payment_date, status
    """
    records = []
    payment_id = 1

    for row in subscriptions_df.itertuples(index=False):
        amount = PLAN_PRICE.get(row.plan, PLAN_PRICE["pro"])
        if amount == 0:
            continue  # free plan -> no billing events

        start = row.started_at
        end = row.canceled_at if pd.notna(row.canceled_at) else start + timedelta(days=180)

        cycle_start = start
        while cycle_start < end:
            failed = random.random() < PAYMENT_FAILURE_RATE
            records.append({
                "payment_id": payment_id,
                "subscription_id": row.subscription_id,
                "amount": amount,
                "payment_date": cycle_start.date(),
                "status": "failed" if failed else "succeeded",
            })
            payment_id += 1
            cycle_start += timedelta(days=30)

    df = pd.DataFrame(records)
    return df


if __name__ == "__main__":
    from users import generate_users
    from accounts import generate_accounts
    from subscriptions import generate_subscriptions

    users_df = generate_users()
    accounts_df = generate_accounts(users_df)
    subs_df, journeys = generate_subscriptions(users_df, accounts_df)
    payments_df = generate_payments(subs_df)

    print(payments_df.head(10))
    print(f"\nGenerated {len(payments_df)} payments")
    print(f"\nStatus breakdown:\n{payments_df['status'].value_counts()}")
    print(f"\nTotal revenue (succeeded only): "
          f"${payments_df[payments_df['status']=='succeeded']['amount'].sum():,.2f}")