---
status: resolved
trigger: "Els links dels Graus A i B apunten a IDs incorrectes. Exemple: 'Preparación de los equipos' genera id=5480 però l'ID correcte a todofp.es és 5497."
created: 2026-05-04
updated: 2026-05-04
---

# Debug: links-id-incorrectes-graus-ab

## Symptoms

- **Expected:** El link de cada registre dels Graus A i B ha d'apuntar a la fitxa correcta a todofp.es (p.ex. ?grado=A&id=4350)
- **Actual:** El link generat apunta a un ID diferent (p.ex. ?grado=A&id=5480) que existeix però correspon a un altre curs
- **Error messages:** Cap error visible; el link simplement porta a la fitxa equivocada
- **Timeline:** Descobert en revisió manual; no se sap si sempre ha estat així
- **Reproduction:** Cercar "Preparación de los equipos" al cercador → clicar el link → porta a la fitxa equivocada a todofp.es

## Context

- Els IDs provenen de l'API REST buscadorgradosfp (scraper A/B/C via API)
- L'ID incorrecte (5480) existeix a todofp.es però pertany a un altre curs
- Afecta Graus A i B (abast real desconegut, podria ser tots o alguns)
- Memòria projecte: scraper A/B/C fa 9 crides a l'API, 12.537 registres, UUID pot caducar

## Current Focus

hypothesis: L'API del buscadorgradosfp retorna múltiples camps d'ID. El camp `id` que captura _map_record (item.get('id')) NO és el camp correcte per a la URL ?id= de la fitxa. Probablement hi ha un altre camp (p.ex. idCertificacion, idOferta, etc.) que conté el valor correcte (4350 en comptes de 5480).
next_action: Verificar els camps exactes que retorna l'API inspeccionant una resposta real.

## Evidence

- timestamp: 2026-05-04
  finding: |
    ofertes.json actual (12.768 registres) NO té camp ficha_id. Claus presents per A/B/C:
    ['codigo', 'denominacion', 'familia', 'grado', 'id', 'nivel', 'observaciones', 'plan_antiguo']
    Això significa que en l'últim scraping exitós, item.get('id') va retornar None per a tots els registres.
    
- timestamp: 2026-05-04
  finding: |
    buscador_scraper.py _map_record usa item.get('id') → guarda com a ficha_id.
    pipeline.py afegeix id seqüencial (1,2,3...) amb enumerate — NO sobreescriu ficha_id
    perquè ficha_id és una clau diferent d'id.
    El problema: l'API potser usa un nom de camp diferent (no 'id') per l'ID de la fitxa.
    
- timestamp: 2026-05-04
  finding: |
    El frontend (index.html línies 834-843) usa row.ficha_id per construir l'URL:
    https://www.todofp.es/buscadorgradosfp/ficha?grado={row.grado}&id={row.ficha_id}
    Si ficha_id és null/absent → no es mostra cap link (row-link class no s'aplica).
    Si ficha_id conté el valor incorrecte de l'API → el link porta a la fitxa equivocada.

- timestamp: 2026-05-04
  finding: |
    L'usuari confirma id=5480 per "Preparación de los equipos" però l'ID correcte és 4350.
    Conclusió: l'API retorna un camp 'id' amb valor 5480, però aquest no és l'ID de la ficha URL.
    Cal inspeccionr la resposta real de l'API per trobar el camp amb valor 4350.

## Root Cause

**El codi és correcte. El problema és de dades desfasades.**

El camp `id` de l'API del buscadorgradosfp SÍ és el camp correcte per construir la URL de fitxa (confirmat inspeccionant el JS de todofp.es: `item.id` és el que usa per generar els links). El scraper el captura correctament a `ficha_id: item.get('id')`.

El problema real: el ministeri ha actualitzat la seva base de dades i els IDs han canviat entre l'últim scraping del VPS i ara. El desfasament NO és uniforme:

| Codi | ID al VPS | ID API ara | Diferència |
|------|-----------|------------|------------|
| ADG_A_3001_01 | 5480 | 5497 | +17 |
| ADG_A_3001_02 | 5481 | 5498 | +17 |
| ADG_A_3001_03 | 5482 | 5499 | +17 |
| ADG_A_3002_01 | 1926 | 2594 | +668 |

No hi ha fórmula per corregir-ho: cal un refresh complet.

**Fitxers afectats:** cap — el codi és correcte.
**Dades afectades:** `ofertes.json` al VPS — IDs desfasats per actualització del ministeri.

## Resolution

root_cause: >
  Els ficha_id guardats a ofertes.json del VPS van ser capturats en un scraping anterior.
  El ministeri ha actualitzat la seva BBDD des d'aleshores i els IDs han canviat (de forma
  no uniforme entre registres). El codi és correcte; les dades necessiten un refresh.

fix: >
  Executar un refresh al VPS amb BUSCADOR_COOKIES fresques (resolent el CAPTCHA al navegador
  i copiant les cookies). Això regenerarà ofertes.json amb els ficha_id actuals de l'API.

verification: pendent — l'usuari executarà el refresh i verificarà que els links funcionen.
