-- Migration 010: cursos concrets marcats dins d'un favorit FPO (Pla 061)

CREATE TABLE IF NOT EXISTS fpo_favorite_courses (
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    especialitat_codi TEXT    NOT NULL,
    curs_id           TEXT    NOT NULL,
    centre_id         TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, especialitat_codi, curs_id)
);

INSERT INTO schema_version (version) VALUES (10);
