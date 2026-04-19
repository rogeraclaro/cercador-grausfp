---
status: resolved
trigger: "Grado A té tots els nivells null al cercador, però todofp.es mostra nivells 1, 2 i 3 per exemple a Actividades Físicas y Deportivas"
created: 2026-04-19
updated: 2026-04-19
---

# Debug: grado-a-nivell-null

## Symptoms

- **Expected:** Registres Grado A amb nivells 1, 2 o 3 (visible a todofp.es/buscadorgradosfp/buscador)
- **Actual:** Tots els registres Grado A tenen `nivel: null` al cercador
- **Error messages:** Cap error visible
- **Timeline:** Descobert avui després del deploy
- **Reproduction:** Filtrar per Grado A al cercador — columna Nivell mostra '—' per tots

## Current Focus

hypothesis: CONFIRMED — `_nivel_grado_a` retorna hardcoded `None`; el nivell es pot deduir del rang numèric del codi CNCP (segment 3 del codi nou pla)
next_action: fix applied

## Evidence

- timestamp: 2026-04-19T00:00:00
  finding: >
    `_nivel_grado_a` (pdf_scraper.py:65-67) té el cos `return None` amb docstring
    "Grado A no té distinció de nivel". Tots els 8.537 registres Grado A tenen nivel=None al JSON.
- timestamp: 2026-04-19T00:00:01
  finding: >
    Codis nou pla tenen format FAM_A_NNNN_XX. El segment NNNN és un codi CNCP:
    1–999 → Nivel 1 (3.199 registres), 1000–1999 → Nivel 2 (1.933 registres),
    2000+ → Nivel 3 (611 registres, concretament 3001–3151).
    Distribució: {1: 3199, 2: 1933, 3: 611}. Coherent amb el que mostra todofp.es.
- timestamp: 2026-04-19T00:00:02
  finding: >
    Codis pla antic (UF0001–UF4000, 2.794 registres): no hi ha prou informació
    als codis per deduir el nivell sense una taula de referència externa.
    Es deixarà nivel=None per als codis UF (pla antic), consistent amb el
    comportament actual de Grado B per al pla antic.

## Eliminated

- Problema de parsing de família (PREFIX_MAP): no rellevant, les famílies s'extreuen correctament
- Columna de nivell existent al PDF ignorada: el PDF no té columna explícita de nivell (confirmat per STATE.md)

## Resolution

root_cause: >
  `_nivel_grado_a` estava hardcoded a `return None`. El nivell per als codis
  nou pla (FAM_A_NNNN_XX) es dedueix del segment numèric NNNN seguint els rangs
  del Catàleg Nacional de Qualificacions Professionals (CNCP):
  1–999=Nivel 1, 1000–1999=Nivel 2, 2000+=Nivel 3.

fix: >
  Implementada deducció de nivell per segment NNNN a `_nivel_grado_a`.
  Codis UF (pla antic) continuen retornant None (no deduïble sense taula externa).
  Tests actualitzats per reflectir el nou comportament.
