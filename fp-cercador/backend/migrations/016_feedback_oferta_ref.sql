-- Migration 016: «Reporta un error en aquesta fitxa» (Pla 089)
-- Un comentari pot anar lligat a un grau: se'n desa el ref estable (Pla 076).
-- NULL = comentari general, com fins ara.

ALTER TABLE feedback ADD COLUMN oferta_ref TEXT;

INSERT INTO schema_version (version) VALUES (16);
