-- ============================================
-- SaaS Product Analytics — Database Schema
-- ============================================

-- Drop tables if they exist (useful while iterating)
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- USERS
-- ============================================
CREATE TABLE users (
    user_id             SERIAL PRIMARY KEY,
    signup_date         DATE NOT NULL,
    country             VARCHAR(50),
    device              VARCHAR(20),          -- e.g. 'desktop', 'mobile', 'tablet'
    acquisition_channel VARCHAR(50)            -- e.g. 'organic', 'paid_ads', 'referral'
);

-- ============================================
-- ACCOUNTS
-- (one account can technically map to one user here,
--  but modeled separately so it mirrors real SaaS billing entities)
-- ============================================
CREATE TABLE accounts (
    account_id          SERIAL PRIMARY KEY,
    user_id             INT NOT NULL REFERENCES users(user_id),
    plan                VARCHAR(20) NOT NULL,   -- 'free', 'pro', 'enterprise'
    account_created_at  TIMESTAMP NOT NULL
);

-- ============================================
-- SUBSCRIPTIONS
-- ============================================
CREATE TABLE subscriptions (
    subscription_id     SERIAL PRIMARY KEY,
    account_id          INT NOT NULL REFERENCES accounts(account_id),
    plan                VARCHAR(20) NOT NULL,
    status              VARCHAR(20) NOT NULL,   -- 'trialing', 'active', 'canceled'
    started_at          TIMESTAMP NOT NULL,
    trial_end_at        TIMESTAMP,
    canceled_at         TIMESTAMP
);

-- ============================================
-- EVENTS  (the heart of the project)
-- ============================================
CREATE TABLE events (
    event_id            BIGSERIAL PRIMARY KEY,
    user_id             INT NOT NULL REFERENCES users(user_id),
    event_timestamp     TIMESTAMP NOT NULL,
    event_type          VARCHAR(50) NOT NULL,   -- signup, email_verified, onboarding_completed,
                                                 -- feature_used, session_started, trial_started,
                                                 -- subscription_started, payment_completed, cancellation
    feature             VARCHAR(50),            -- populated when event_type = 'feature_used'
    device              VARCHAR(20),
    country             VARCHAR(50),
    plan                VARCHAR(20)
);

-- ============================================
-- SESSIONS
-- ============================================
CREATE TABLE sessions (
    session_id          BIGSERIAL PRIMARY KEY,
    user_id             INT NOT NULL REFERENCES users(user_id),
    started_at          TIMESTAMP NOT NULL,
    ended_at            TIMESTAMP,
    device              VARCHAR(20)
);

-- ============================================
-- PAYMENTS
-- ============================================
CREATE TABLE payments (
    payment_id          BIGSERIAL PRIMARY KEY,
    subscription_id     INT NOT NULL REFERENCES subscriptions(subscription_id),
    amount              NUMERIC(10, 2) NOT NULL,
    payment_date        DATE NOT NULL,
    status              VARCHAR(20) NOT NULL    -- 'succeeded', 'failed', 'refunded'
);

-- ============================================
-- INDEXES (for the joins/filters your SQL analysis will hammer)
-- ============================================
CREATE INDEX idx_events_user_id        ON events(user_id);
CREATE INDEX idx_events_timestamp      ON events(event_timestamp);
CREATE INDEX idx_events_type           ON events(event_type);
CREATE INDEX idx_sessions_user_id      ON sessions(user_id);
CREATE INDEX idx_accounts_user_id      ON accounts(user_id);
CREATE INDEX idx_subscriptions_account ON subscriptions(account_id);
CREATE INDEX idx_payments_subscription ON payments(subscription_id);