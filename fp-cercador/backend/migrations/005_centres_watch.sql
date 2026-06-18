-- Migration 005: F4 — Seguiment de centres per oferta

CREATE TABLE IF NOT EXISTS centres_watch (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    oferta_key      TEXT    NOT NULL,
    oferta_denom    TEXT    NOT NULL,
    provincia_filter TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    last_sent_at    TEXT,
    snapshot_json   TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_centres_watch_user_oferta
    ON centres_watch(user_id, oferta_key);

INSERT INTO schema_version (version) VALUES (5);
