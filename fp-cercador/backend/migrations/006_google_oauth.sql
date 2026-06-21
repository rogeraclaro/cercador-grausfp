-- Migration 006: Google OAuth — afegeix google_id a users

ALTER TABLE users ADD COLUMN google_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;

INSERT OR IGNORE INTO schema_version (version) VALUES (6);
