"""
Generates the events table — the heart of the project.

Turns each user's simulated journey (from funnel.py, via subscriptions.py)
into concrete event rows, and adds feature_used / session_started /
payment_completed / cancellation events on top.
"""

import random
import pandas as pd
from datetime import timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    FEATURES,
    KEY_FEATURE,
    POWER_USER_THRESHOLD,
    RANDOM_SEED,
)

random.seed(RANDOM_SEED)

# Maps a funnel timestamp key to the event_type recorded in the events table.
# ("activated" isn't a real product event on its own — it's a derived state —
# so it does NOT get its own event row. It's computed later in SQL from
# feature_used events, same as a real analytics team would do.)
STAGE_TO_EVENT_TYPE = {
    "signup": "signup",
    "email_verified": "email_verified",
    "onboarding_completed": "onboarding_completed",
    "trial_started": "trial_started",
    "subscription_started": "subscription_started",
}


def _feature_used_events(user_id, journey, device, country, plan):
    """
    Generate feature_used events for a single user.

    Power users get many uses of KEY_FEATURE (>= POWER_USER_THRESHOLD),
    non-power users get occasional, lighter usage across random features.
    All feature usage happens after onboarding_completed (can't use
    features before finishing onboarding) and before churn/cancellation
    if applicable.
    """
    events = []

    if "onboarding_completed" not in journey["timestamps"]:
        return events  # never onboarded -> never used a feature

    window_start = journey["timestamps"]["onboarding_completed"]
    window_end = journey["canceled_at"] or (window_start + timedelta(days=180))

    total_window_days = max((window_end - window_start).days, 1)

    if journey["is_power_user"]:
        n_key_feature_uses = random.randint(POWER_USER_THRESHOLD, POWER_USER_THRESHOLD + 15)
        n_other_uses = random.randint(2, 10)
    else:
        n_key_feature_uses = random.randint(0, POWER_USER_THRESHOLD - 1)
        n_other_uses = random.randint(0, 8)

    for _ in range(n_key_feature_uses):
        offset_days = random.uniform(0, total_window_days)
        ts = window_start + timedelta(days=offset_days)
        events.append({
            "event_type": "feature_used",
            "feature": KEY_FEATURE,
            "event_timestamp": ts,
            "device": device,
            "country": country,
            "plan": plan,
        })

    other_features = [f for f in FEATURES if f != KEY_FEATURE]
    for _ in range(n_other_uses):
        offset_days = random.uniform(0, total_window_days)
        ts = window_start + timedelta(days=offset_days)
        events.append({
            "event_type": "feature_used",
            "feature": random.choice(other_features),
            "event_timestamp": ts,
            "device": device,
            "country": country,
            "plan": plan,
        })

    return events


def generate_events(users_df: pd.DataFrame, accounts_df: pd.DataFrame, journeys: dict) -> pd.DataFrame:
    """
    Build the full events table from users, accounts, and the per-user
    journeys produced by generate_subscriptions().

    Returns a DataFrame with columns:
    event_id, user_id, event_timestamp, event_type, feature, device, country, plan
    """
    records = []
    accounts_by_user = accounts_df.set_index("user_id")

    for row in users_df.itertuples(index=False):
        journey = journeys[row.user_id]
        account = accounts_by_user.loc[row.user_id]
        device = row.device
        country = row.country
        plan = account["plan"]

        # 1. Funnel milestone events (signup, verified, onboarded, trial, paid)
        for stage_key, event_type in STAGE_TO_EVENT_TYPE.items():
            if stage_key in journey["timestamps"]:
                records.append({
                    "user_id": row.user_id,
                    "event_timestamp": journey["timestamps"][stage_key],
                    "event_type": event_type,
                    "feature": None,
                    "device": device,
                    "country": country,
                    "plan": plan,
                })

        # 2. Cancellation event, if churned
        if journey["canceled_at"]:
            records.append({
                "user_id": row.user_id,
                "event_timestamp": journey["canceled_at"],
                "event_type": "cancellation",
                "feature": None,
                "device": device,
                "country": country,
                "plan": plan,
            })

        #