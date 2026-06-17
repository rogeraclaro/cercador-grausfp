-- Migration 003: Afegeix is_active a users (gestió admin de comptes)

ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1;

INSERT INTO schema_version (version) VALUES (3);
