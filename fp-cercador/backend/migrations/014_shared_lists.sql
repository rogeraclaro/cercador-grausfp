-- 014_shared_lists.sql
-- Pla 084: llistes de graus compartibles. Les llistes existents queden com a
-- 'favorites' pel valor per defecte; les noves llistes amb nom són 'shared'.

ALTER TABLE lists ADD COLUMN kind TEXT NOT NULL DEFAULT 'favorites';  -- 'favorites' | 'shared'
ALTER TABLE lists ADD COLUMN message TEXT;
ALTER TABLE lists ADD COLUMN updated_at TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_lists_share_token ON lists(share_token) WHERE share_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_lists_user_kind ON lists(user_id, kind);

INSERT INTO schema_version (version) VALUES (14);
