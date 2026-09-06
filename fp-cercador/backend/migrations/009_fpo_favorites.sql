-- Migration 009: favorits d'especialitat FPO (Pla 061)

CREATE TABLE IF NOT EXISTS fpo_favorites (
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    especialitat_codi TEXT    NOT NULL,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, especialitat_codi)
);

INSERT INTO schema_version (version) VALUES (9);
