"""
Generates the accounts table — one account per user, assigned a plan.
Depends on: users.py output (needs user_id and signup_date).
"""

import random
import pandas as pd
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PLANS, RANDOM_SEED

random.seed(RANDOM_SEED)

# Most accounts start on 'free' — plan gets upgraded later via subscriptions.py
# based on trial-to-paid conversion. Only a small slice start directly on a
# paid plan (e.g. enterprise deals that skip a trial).
INITIAL_PLAN_WEIGHTS = {
    "free": 0.90,
    "pro": 0.07,
    "enterprise": 0.03,
}


def generate_accounts(users_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate one account per user, created shortly after signup.

    Parameters
    ----------
    users_df : DataFrame with at least user_id, signup_date

    Returns
    -------
    DataFrame with columns:
    account_id, user_id, plan, account_created_at
    """
    records = []

    for account_id, row in enumerate(users_df.itertuples(index=False), start=1):
        # Account is created within a few minutes to a few hours of signup
        signup_datetime = datetime.combine(row.signup_date, datetime.min.time())
        created_at = signup_datetime + timedelta(minutes=random.randint(1, 240))

        plan = random.choices(
            list(INITIAL_PLAN_WEIGHTS.keys()),
            weights=list(INITIAL_PLAN_WEIGHTS.values()),
            k=1,
        )[0]

        records.append({
            "account_id": account_id,
            "user_id": row.user_id,
            "plan": plan,
            "account_created_at": created_at,
        })

    df = pd.DataFrame(records)
    return df


if __name__ == "__main__":
    # Standalone test — depends on users.py, so generate users first
    from users import generate_users

    users_df = generate_users()
    accounts_df = generate_accounts(users_df)

    print(accounts_df.head(10))
    print(f"\nGenerated {len(accounts_df)} accounts")
    print(f"\nPlan distribution:\n{accounts_df['plan'].value_counts(normalize=True)}")