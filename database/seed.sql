-- ============================================
-- Seed script: loads data/raw/*.csv into Postgres
-- ============================================
-- Prerequisite: run schema.sql first to create the tables.
-- Prerequisite: run simulator/event_generator.py first to generate the CSVs.
--
-- NOTE: \copy is a psql meta-command (client-side), not server-side SQL.
-- It works even if Postgres itself doesn't have filesystem access to your
-- machine — which matters if you're running Postgres in Docker.
-- Run this file with:  psql -U <user> -d <dbname> -f database/seed.sql
-- (paths below are relative to WHERE YOU RUN psql FROM, i.e. repo root)

-- Clear existing data first (safe to re-run this file repeatedly)
TRUNCATE TABLE payments, events, sessions, subscriptions, accounts, users
    RESTART IDENTITY CASCADE;

\copy users (user_id, signup_date, country, device, acquisition_channel) \
    FROM 'data/raw/users.csv' WITH (FORMAT csv, HEADER true);

\copy accounts (account_id, user_id, plan, account_created_at) \
    FROM 'data/raw/accounts.csv' WITH (FORMAT csv, HEADER true);

\copy subscriptions (subscription_id, account_id, plan, status, started_at, trial_end_at, canceled_at) \
    FROM 'data/raw/subscriptions.csv' WITH (FORMAT csv, HEADER true);

\copy events (event_id, user_id, event_timestamp, event_type, feature, device, country, plan) \
    FROM 'data/raw/events.csv' WITH (FORMAT csv, HEADER true);

\copy sessions (session_id, user_id, started_at, ended_at, device) \
    FROM 'data/raw/sessions.csv' WITH (FORMAT csv, HEADER true);

\copy payments (payment_id, subscription_id, amount, payment_date, status) \
    FROM 'data/raw/payments.csv' WITH (FORMAT csv, HEADER true);

-- Reset sequences to match the max id loaded, so any future INSERTs
-- (outside this script) don't collide with existing primary keys
SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users));
SELECT setval('accounts_account_id_seq', (SELECT MAX(account_id) FROM accounts));
SELECT setval('subscriptions_subscription_id_seq', (SELECT MAX(subscription_id) FROM subscriptions));
SELECT setval('events_event_id_seq', (SELECT MAX(event_id) FROM events));
SELECT setval('sessions_session_id_seq', (SELECT MAX(session_id) FROM sessions));
SELECT setval('payments_payment_id_seq', (SELECT MAX(payment_id) FROM payments));

-- ============================================
-- Sanity check counts after load
-- ============================================
SELECT 'users' AS table_name, COUNT(*) FROM users
UNION ALL
SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL
SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL
SELECT 'events', COUNT(*) FROM events
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL
SELECT 'payments', COUNT(*) FROM payments;