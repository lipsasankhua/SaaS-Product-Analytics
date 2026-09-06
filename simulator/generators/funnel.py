"""
Shared per-user journey simulation.

Both subscriptions.py and events.py need to agree on which funnel stage
each user reached and when — otherwise the events table and subscriptions
table will contradict each other. This module is the single source of
truth for that decision, computed once per user and reused everywhere.
"""

import random
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    FUNNEL_CONVERSION,
    KEY_FEATURE,
    POWER_USER_THRESHOLD,
    POWER_USER_CONVERSION_LIFT,
    POWER_USER_RETENTION_LIFT,
    MONTHLY_CHURN_RATE,
    RANDOM_SEED,
)

random.seed(RANDOM_SEED)

FUNNEL_ORDER = [
    "signup",
    "email_verified",
    "onboarding_completed",
    "activated",
    "trial_started",
    "subscription_started",
]


def _roll(probability: float) -> bool:
    return random.random() < probability


def simulate_user_journey(user_id: int, signup_datetime: datetime, plan: str) -> dict:
    """
    Decide, once per user, how far down the funnel they get, whether they
    become a "power user" of the key feature, and — if they convert to
    paid — whether/when they eventually churn.

    Returns a dict describing the outcome. Downstream generators
    (subscriptions.py, events.py) read from this instead of re-rolling
    their own probabilities, so the two tables stay consistent.
    """
    stage_reached = "signup"
    timestamps = {"signup": signup_datetime}

    # Decide, up front, whether this user will be a power user of the
    # key feature. This is independent of the funnel chain — power users
    # can exist even among free/trial users — but it LIFTS their odds of
    # advancing at each subsequent stage, which is the seeded signal that
    # query 05_feature_analysis.sql should later "discover."
    is_power_user = random.random() < 0.15  # ~15% of all users become power users

    def lifted(prob: float) -> float:
        return min(prob * POWER_USER_CONVERSION_LIFT, 0.98) if is_power_user else prob

    t = signup_datetime

    # signup -> email_verified
    if _roll(lifted(FUNNEL_CONVERSION["signup_to_verified"])):
        t = t + timedelta(hours=random.uniform(0.1, 48))
        timestamps["email_verified"] = t
        stage_reached = "email_verified"

        # verified -> onboarded
        if _roll(lifted(FUNNEL_CONVERSION["verified_to_onboarded"])):
            t = t + timedelta(hours=random.uniform(0.5, 72))
            timestamps["onboarding_completed"] = t
            stage_reached = "onboarding_completed"

            # onboarded -> activated
            if _roll(lifted(FUNNEL_CONVERSION["onboarded_to_activated"])):
                t = t + timedelta(hours=random.uniform(1, 96))
                timestamps["activated"] = t
                stage_reached = "activated"

                # activated -> trial
                if _roll(lifted(FUNNEL_CONVERSION["activated_to_trial"])):
                    t = t + timedelta(hours=random.uniform(1, 48))
                    timestamps["trial_started"] = t
                    trial_end = t + timedelta(days=14)
                    stage_reached = "trial_started"

                    # trial -> paid
                    if _roll(lifted(FUNNEL_CONVERSION["trial_to_paid"])):
                        paid_at = trial_end - timedelta(days=random.randint(0, 3))
                        timestamps["subscription_started"] = paid_at
                        stage_reached = "subscription_started"

    converted_to_paid = "subscription_started" in timestamps

    # ---- Churn simulation (only relevant if converted to paid) ----
    canceled_at = None
    if converted_to_paid:
        base_monthly_churn = MONTHLY_CHURN_RATE.get(plan, MONTHLY_CHURN_RATE["pro"])
        # Power users churn less — apply the retention lift as a REDUCTION
        # in monthly churn probability.
        effective_churn = (
            base_monthly_churn / POWER_USER_RETENTION_LIFT
            if is_power_user
            else base_monthly_churn
        )

        # Roll month by month from paid start until churn or "still active"
        month_cursor = timestamps["subscription_started"]
        months_survived = 0
        while True:
            months_survived += 1
            month_cursor = month_cursor + timedelta(days=30)
            if _roll(effective_churn):
                canceled_at = month_cursor
                break
            if months_survived > 24:  # cap simulation horizon at 2 years
                break

    return {
        "user_id": user_id,
        "stage_reached": stage_reached,
        "timestamps": timestamps,
        "is_power_user": is_power_user,
        "converted_to_paid": converted_to_paid,
        "canceled_at": canceled_at,
    }                                                                                                                                                                                                                                                