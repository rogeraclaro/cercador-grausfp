-- Migration 002: Taula de l'Observatori FP (sèrie temporal indefinida)

CREATE TABLE IF NOT EXISTS observatory_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  TEXT    NOT NULL,
    total               INTEGER NOT NULL,
    total_a             INTEGER NOT NULL DEFAULT 0,
    total_b             INTEGER NOT NULL DEFAULT 0,
    total_c             INTEGER NOT NULL DEFAULT 0,
    total_d             INTEGER NOT NULL DEFAULT 0,
    total_e             INTEGER NOT NULL DEFAULT 0,
    n_altes             INTEGER NOT NULL DEFAULT 0,
    n_baixes            INTEGER NOT NULL DEFAULT 0,
    families_amb_altes  TEXT,
    source              TEXT    NOT NULL DEFAULT 'refresh'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_observatory_ts ON observatory_snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_observatory_ts_lookup ON observatory_snapshots(ts DESC);

INSERT INTO schema_version (version) VALUES (2);
