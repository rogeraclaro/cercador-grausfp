-- Migration 011: comentaris d'usuaris (Pla 069)
-- user_id NULL = comentari anònim. CASCADE com la resta de taules d'usuari:
-- esborrar un compte esborra també els seus comentaris (i l'email que hi consta).

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
    email      TEXT    NOT NULL,
    kind       TEXT    NOT NULL,
    message    TEXT    NOT NULL,
    context    TEXT,
    status     TEXT    NOT NULL DEFAULT 'new',
    admin_note TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);

INSERT INTO schema_version (version) VALUES (11);
