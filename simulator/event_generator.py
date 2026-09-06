"""
Main orchestrator for the data simulation pipeline.

Run this file directly to generate the full synthetic dataset:
    python simulator/event_generator.py

Produces six CSVs in data/raw/:
    users.csv, accounts.csv, subscriptions.csv,
    events.csv, sessions.csv, payments.csv
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "generators"))

from config import N_USERS
from generators.users import generate_users
from generators.accounts import generate_accounts
from generators.subscriptions import generate_subscriptions
from generators.events import generate_events
from generators.sessions import generate_sessions
from generators.payments import generate_payments

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")


def run_pipeline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start = time.time()

    print(f"Generating {N_USERS} users...")
    users_df = generate_users()

    print("Generating accounts...")
    accounts_df = generate_accounts(users_df)

    print("Simulating user journeys and generating subscriptions...")
    subscriptions_df, journeys = generate_subscriptions(users_df, accounts_df)

    print("Generating events...")
    events_df = generate_events(users_df, accounts_df, journeys)

    print("Generating sessions...")
    sessions_df = generate_sessions(users_df, journeys)

    print("Generating payments...")
    payments_df = generate_payments(subscriptions_df)

    print("\nWriting CSVs to data/raw/ ...")
    users_df.to_csv(os.path.join(OUTPUT_DIR, "users.csv"), index=False)
    accounts_df.to_csv(os.path.join(OUTPUT_DIR, "accounts.csv"), index=False)
    subscriptions_df.to_csv(os.path.join(OUTPUT_DIR, "subscriptions.csv"), index=False)
    events_df.to_csv(os.path.join(OUTPUT_DIR, "events.csv"), index=False)
    sessions_df.to_csv(os.path.join(OUTPUT_DIR, "sessions.csv"), index=False)
    payments_df.to_csv(os.path.join(OUTPUT_DIR, "payments.csv"), index=False)

    elapsed = time.time() - start

    print("\n" + "=" * 50)
    print("PIPELINE SUMMARY")
    print("=" * 50)
    print(f"Users:         {len(users_df):,}")
    print(f"Accounts:      {len(accounts_df):,}")
    print(f"Subscriptions: {len(subscriptions_df):,}")
    print(f"Events:        {len(events_df):,}")
    print(f"Sessions:      {len(sessions_df):,}")
    print(f"Payments:      {len(payments_df):,}")
    print(f"\nTime elapsed: {elapsed:.1f}s")
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    run_pipeline()