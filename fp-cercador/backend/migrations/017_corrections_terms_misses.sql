-- Migration 017: correccions i equivalències des del panell (Pla 098)

-- 1. Correccions de títol d'especialitats (SEPE i FPO/SOC). NULL = aquest idioma no es corregeix.
--    original_* = el títol que es veia quan es va desar la correcció (només informatiu).
CREATE TABLE IF NOT EXISTS title_overrides (
    codi        TEXT PRIMARY KEY,
    titol_ca    TEXT,
    titol_es    TEXT,
    original_ca TEXT,
    original_es TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by  TEXT
);

-- Primera correcció, vista pel propietari: el SOC escriu «JAVASCRIP».
INSERT OR IGNORE INTO title_overrides (codi, titol_ca, titol_es, original_ca, original_es, updated_by)
VALUES ('IFCD0025',
        'Fonaments de programació amb HTML, CSS i JavaScript',
        'Fundamentos de programación con HTML, CSS y JavaScript',
        'Fonaments de programació amb HTML, CSS i JAVASCRIP',
        'Fundamentos de programación con HTML, CSS y JavaScript',
        'pla 098');

-- 2. Equivalències de cerca català → castellà (claus i valors normalitzats).
--    db.py la sembra amb ca_es_terms.SEED_TERMS en aplicar aquesta migració.
CREATE TABLE IF NOT EXISTS search_terms (
    ca         TEXT PRIMARY KEY,
    es         TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 3. Cerques sense resultat, agregades i anònimes: cap dada de qui ha cercat.
CREATE TABLE IF NOT EXISTS empty_searches (
    q         TEXT PRIMARY KEY,
    n         INTEGER NOT NULL DEFAULT 1,
    last_seen TEXT NOT NULL
);

-- 4. Un comentari pot anar lligat a una especialitat (codi SEPE/SOC), com oferta_ref (016).
ALTER TABLE feedback ADD COLUMN espec_codi TEXT;

INSERT INTO schema_version (version) VALUES (17);
