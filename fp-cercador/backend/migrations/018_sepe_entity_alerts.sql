-- Migration 018: alertes d'entitats autoritzades noves del SEPE (Pla 102)
-- Un usuari demana avís quan una entitat nova queda autoritzada per impartir una
-- especialitat del catàleg SEPE. provincia NULL = qualsevol; nomes_teleformacio 0 = qualsevol modalitat.
-- La instantània desa, per especialitat, els identificadors d'entitat ja coneguts
-- (JSON: ["<id>|<tipus>", ...]) per detectar-ne de noves en cada refresc setmanal.

CREATE TABLE IF NOT EXISTS sepe_entity_alerts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    codi               TEXT NOT NULL,
    provincia          TEXT,                       -- NULL = qualsevol
    nomes_teleformacio INTEGER NOT NULL DEFAULT 0,
    active             INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    last_sent_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_sepe_entity_alerts_user ON sepe_entity_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_sepe_entity_alerts_codi ON sepe_entity_alerts(codi);

CREATE TABLE IF NOT EXISTS sepe_entity_snapshots (
    codi         TEXT PRIMARY KEY,
    entitat_keys TEXT NOT NULL,                    -- array JSON
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO schema_version (version) VALUES (18);
