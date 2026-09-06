"""
Central configuration for the SaaS analytics data simulator.
All generators import from here so assumptions stay consistent
across users, events, subscriptions, and payments.
"""

from datetime import date

# ============================================
# SCALE
# ============================================
N_USERS = 5000

# ============================================
# DATE RANGE
# ============================================
START_DATE = date(2024, 1, 1)
END_DATE   = date(2025, 12, 31)

# ============================================
# ACQUISITION
# ============================================
COUNTRIES = ["US", "UK", "India", "Canada", "Germany", "Australia", "Brazil"]
COUNTRY_WEIGHTS = [0.35, 0.12, 0.18, 0.08, 0.10, 0.07, 0.10]

DEVICES = ["desktop", "mobile", "tablet"]
DEVICE_WEIGHTS = [0.55, 0.35, 0.10]

ACQUISITION_CHANNELS = ["organic", "paid_ads", "referral", "content"]
ACQUISITION_WEIGHTS = [0.40, 0.30, 0.15, 0.15]

# ============================================
# PLANS
# ============================================
PLANS = ["free", "pro", "enterprise"]

# ============================================
# FUNNEL DROP-OFF RATES
# Probability a user who reached stage N advances to stage N+1.
# These compound, so an 0.75 * 0.70 * 0.60 chain gives a realistic
# "steep top-of-funnel, narrowing" shape rather than uniform noise.
# ============================================
FUNNEL_CONVERSION = {
    "signup_to_verified":       0.80,   # 80% of signups verify email
    "verified_to_onboarded":    0.65,   # 65% of verified users finish onboarding
    "onboarded_to_activated":   0.55,   # 55% of onboarded users hit an "activation" event
    "activated_to_trial":       0.45,   # 45% of activated users start a trial
    "trial_to_paid":            0.30,   # 30% of trials convert to paid
}

# "Activation" is defined as using a core feature at least ACTIVATION_THRESHOLD
# times within ACTIVATION_WINDOW_DAYS of signup. Document this exact definition
# in docs/metrics_glossary.md later — interviewers will ask how you defined it.
ACTIVATION_THRESHOLD = 3
ACTIVATION_WINDOW_DAYS = 7

# ============================================
# FEATURES
# One of these is the "key feature" used for the centerpiece
# conversion/retention investigation (Phase 3, query 05).
# ============================================
FEATURES = [
    "dashboard_view",
    "report_export",     # <- KEY_FEATURE: power users of this convert/retain more
    "team_invite",
    "integration_setup",
    "api_usage",
    "custom_alert",
]
KEY_FEATURE = "report_export"

# Multiplier applied to conversion/retention odds for users who become
# "power users" of KEY_FEATURE (defined as using it >= POWER_USER_THRESHOLD
# times). This is the deliberately seeded signal your SQL will "discover."
POWER_USER_THRESHOLD = 5
POWER_USER_CONVERSION_LIFT = 1.8   # power users are 1.8x more likely to convert
POWER_USER_RETENTION_LIFT  = 1.5   # and 1.5x more likely to retain at 30 days

# ============================================
# SESSIONS
# ============================================
AVG_SESSIONS_PER_ACTIVE_WEEK = 3.5
SESSION_DURATION_MIN_MINUTES = 2
SESSION_DURATION_MAX_MINUTES = 45

# ============================================
# CHURN
# Monthly churn probability for paid users, varies by plan.
# ============================================
MONTHLY_CHURN_RATE = {
    "free":       0.15,   # "churn" for free = goes inactive, no billing event
    "pro":        0.06,
    "enterprise": 0.02,
}

# ============================================
# PRICING (for revenue analysis)
# ============================================
PLAN_PRICE = {
    "free":       0.0,
    "pro":        29.0,
    "enterprise": 199.0,
}

# ============================================
# PAYMENT FAILURE RATE
# ============================================
PAYMENT_FAILURE_RATE = 0.03

# ============================================
# RANDOM SEED
# Keep this fixed so the dataset is reproducible — anyone cloning
# the repo and re-running the simulator gets identical data.
# ============================================
RANDOM_SEED = 42