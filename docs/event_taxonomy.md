# Event Taxonomy

Full list of `event_type` values found in the `events` table, what triggers
them, and which funnel stage they represent.

| event_type | Funnel stage | Triggered when | Notes |
|---|---|---|---|
| `signup` | 1 | User creates an account | First event for every user |
| `email_verified` | 2 | User clicks the verification link | ~80% of signups reach this |
| `onboarding_completed` | 3 | User finishes the onboarding flow | ~65% of verified users reach this |
| `feature_used` | — | User interacts with any product feature | See `feature` column for which one; can occur many times per user |
| `session_started` | — | Represented in the separate `sessions` table, not as an `events` row | See `sessions` table instead |
| `trial_started` | 5 | User begins a 14-day trial | ~45% of activated users reach this |
| `subscription_started` | 6 | Trial converts to a paid subscription | ~30% of trials convert |
| `payment_completed` | — | Recurring billing charge succeeds | One row per ~30-day billing cycle while subscribed |
| `cancellation` | — | User cancels an active subscription | Terminal event for churned paid users |

## Derived states (NOT raw events)

Some important product states are intentionally **not** stored as raw
events, because in a real analytics stack they'd be computed metrics,
not tracked actions. This distinction matters and is called out here on
purpose — it's a common trap in analytics interviews.

- **Activated** — defined as: a user who performed the key feature action
  at least `ACTIVATION_THRESHOLD` (3) times within `ACTIVATION_WINDOW_DAYS`
  (7 days) of signup. Computed from `feature_used` events in SQL, not
  stored directly. See `docs/metrics_glossary.md` for the exact query
  pattern.
- **Power user** — a user who used the key feature (`report_export`)
  at least 5 times total. Also computed in SQL from `feature_used` events.
- **DAU / MAU / Active user** — derived from the presence of *any* event
  or session on a given day/month, not a stored flag.

## Funnel order (for reference)

```
signup
  → email_verified
    → onboarding_completed
      → (activated — derived, not a raw event)
        → trial_started
          → subscription_started
            → (churn: cancellation, if it happens)
```