-- Migration 013: graus que l'usuari diu que ja té (Pla 083, «Què em falta?»)
-- Es desa el ref estable (Pla 076). CASCADE com la resta de taules d'usuari:
-- esborrar un compte n'esborra també la llista.

CREATE TABLE IF NOT EXISTS user_held (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    oferta_ref TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, oferta_ref)
);

INSERT INTO schema_version (version) VALUES (13);
