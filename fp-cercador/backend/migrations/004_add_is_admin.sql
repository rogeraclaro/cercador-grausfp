-- Migration 004: Afegeix is_admin a users (autenticació admin via sessió)

ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;

INSERT INTO schema_version (version) VALUES (4);
