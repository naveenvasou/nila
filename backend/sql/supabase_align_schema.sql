-- Run once in Supabase SQL Editor if tables existed before new columns were added.
-- SQLAlchemy create_all() does not ALTER existing tables.

ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS age_confirmed BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS vibe VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR DEFAULT 'free';

UPDATE users SET age_confirmed = COALESCE(age_confirmed, FALSE);
UPDATE users SET subscription_tier = COALESCE(subscription_tier, 'free');

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_id ON users (telegram_id) WHERE telegram_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS telegram_sessions (
    id SERIAL PRIMARY KEY,
    telegram_id INTEGER NOT NULL UNIQUE,
    onboarding_step VARCHAR NOT NULL DEFAULT 'none',
    display_name VARCHAR,
    age_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    vibe VARCHAR,
    pending_age_text VARCHAR(2000),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_telegram_sessions_telegram_id ON telegram_sessions (telegram_id);

ALTER TABLE telegram_sessions ADD COLUMN IF NOT EXISTS pending_age_text VARCHAR(2000);

CREATE TABLE IF NOT EXISTS incident_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source VARCHAR(64) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    telegram_user_id INTEGER,
    telegram_chat_id INTEGER,
    error_type VARCHAR(128) NOT NULL,
    summary VARCHAR(2000) NOT NULL,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS ix_incident_logs_created_at ON incident_logs (created_at DESC);
