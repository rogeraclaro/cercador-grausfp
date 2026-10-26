-- Migration 012: clau estable `ref` dels graus (Pla 076)
-- Els id d'ofertes.json es reassignen a cada refresc. Els favorits passen a
-- guardar el ref (oferta_id i oferta_codigo es mantenen com a llegat).
-- centres_watch.oferta_key passa a contenir el ref (mateixa columna).
-- L'emplenat es fa en Python amb el catàleg actual: db.backfill_refs().

ALTER TABLE list_items ADD COLUMN oferta_ref TEXT;

CREATE INDEX IF NOT EXISTS idx_list_items_list_ref ON list_items(list_id, oferta_ref);

INSERT INTO schema_version (version) VALUES (12);
