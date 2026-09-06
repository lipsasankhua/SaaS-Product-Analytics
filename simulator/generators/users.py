"""
Generates the base users table.
Every other generator (accounts, events, sessions...) builds on top of this.
"""

import random
import pandas as pd
from faker import Faker
from datetime import timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    N_USERS,
    START_DATE,
    END_DATE,
    COUNTRIES,
    COUNTRY_WEIGHTS,
    DEVICES,
    DEVICE_WEIGHTS,
    ACQUISITION_CHANNELS,
    ACQUISITION_WEIGHTS,
    RANDOM_SEED,
)

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def random_signup_date():
    """
    Pick a signup date between START_DATE and END_DATE, weighted so that
    signups grow over time (mimics a product gaining traction) rather than
    being uniformly random.
    """
    total_days = (END_DATE - START_DATE).days

    # Weight later days more heavily: growth curve, not flat distribution
    day_offset = int(random.triangular(0, total_days, total_days))
    return START_DATE + timedelta(days=day_offset)


def generate_users(n_users: int = N_USERS) -> pd.DataFrame:
    """
    Generate the users table.

    Returns a DataFrame with columns:
    user_id, signup_date, country, device, acquisition_channel
    """
    records = []

    for user_id in range(1, n_users + 1):
        signup_date = random_signup_date()
        country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
        device = random.choices(DEVICES, weights=DEVICE_WEIGHTS, k=1)[0]
        channel = random.choices(ACQUISITION_CHANNELS, weights=ACQUISITION_WEIGHTS, k=1)[0]

        records.append({
            "user_id": user_id,
            "signup_date": signup_date,
            "country": country,
            "device": device,
            "acquisition_channel": channel,
        })

    df = pd.DataFrame(records)
    df = df.sort_values("signup_date").reset_index(drop=True)
    return df


if __name__ == "__main__":
    # Quick standalone test: run `python simulator/generators/users.py`
    # to sanity-check output without running the full pipeline.
    df = generate_users()
    print(df.head(10))
    print(f"\nGenerated {len(df)} users")
    print(f"Date range: {df['signup_date'].min()} to {df['signup_date'].max()}")
    print(f"\nCountry distribution:\n{df['country'].value_counts(normalize=True)}")