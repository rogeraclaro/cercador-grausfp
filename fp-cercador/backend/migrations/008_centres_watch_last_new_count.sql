-- Migration 008: recorda quants centres nous es van enviar al darrer avís

ALTER TABLE centres_watch ADD COLUMN last_new_count INTEGER;

INSERT INTO schema_version (version) VALUES (8);
