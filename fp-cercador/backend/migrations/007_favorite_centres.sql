-- Migration 007: centres seleccionats dins d'un favorit

CREATE TABLE IF NOT EXISTS list_item_centres (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    list_item_id  INTEGER NOT NULL REFERENCES list_items(id) ON DELETE CASCADE,
    centre_id     TEXT    NOT NULL,
    added_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_list_item_centres_unique
    ON list_item_centres(list_item_id, centre_id);

INSERT INTO schema_version (version) VALUES (7);
