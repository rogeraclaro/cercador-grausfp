-- Migration 015: alertes de cursos FPO nous (Pla 086)
-- Un usuari demana avís quan apareix un curs nou que encaixa amb una comarca, una
-- família i/o una especialitat. NULL = qualsevol. CASCADE com la resta de taules d'usuari.

CREATE TABLE IF NOT EXISTS fpo_alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comarca      TEXT,            -- NULL = qualsevol
    familia_codi TEXT,            -- NULL = qualsevol
    espec_codi   TEXT,            -- NULL = qualsevol
    inclou_en_linia INTEGER NOT NULL DEFAULT 1,
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    last_sent_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_fpo_alerts_user ON fpo_alerts(user_id);

INSERT INTO schema_version (version) VALUES (15);
