# 076 — Identificadors estables per als graus (favorits, enllaços, centres)

**Prioritat:** P1 (abans del llançament públic) · **Esforç:** M–L · **Depèn de:** — · **Estat:** TODO

## Problema

El pipeline reassigna `id` seqüencials a cada refresc del catàleg (`backend/scrapers/pipeline.py`, `record['id'] = i`). Tot el que guarda o comparteix un `id` pot acabar apuntant a un altre grau després d'un refresc:

- Favorits: `list_items.oferta_id` (80 files, 11 usuaris el 2026-10-26) i els centres desats que en depenen (`list_item_centres`). El catàleg ja ha passat de 12.894 a 13.006 registres, de manera que alguns favorits probablement ja estan desplaçats.
- Enllaços compartibles: `itinerari.html?grado=D|E&id=`, `index.html?oferta=<id>` (perfil), tornada `index.html?grado=&id=`.
- Avisos de centres nous: `centres_watch.oferta_key` = `codigo || String(id)` (D/E guarden l'id).
- Fitxers derivats per id: `oferta_centres.json` i `centres_nous_per_oferta.json` (C LOMLOE, D, E). Bug existent: el scrape de centres va a part del refresc del catàleg, i entre tots dos els recomptes de centres apunten a registres equivocats. Els avisos de C LOMLOE no coincideixen mai (`oferta_key` = codigo, fitxer per id).
- Ja resolt: `d_modulos.json` i `ce_acces.json` (`id_remap_by_ficha`, commit 7958472).

## Clau estable `ref`

Camp nou `ref` a cada registre d'`ofertes.json`, calculat al pipeline:

- A/B/C: `codigo`. Excepció: 21 codis A i 21 codis B de pla antic es repeteixen entre famílies (`MF0432_1` ×6). Per a aquests, `codigo~<prefix família>` (prefix de `PREFIX_MAP`, p. ex. `MF0432_1~ADG`).
  **Decisió del propietari:** sufix sempre que el codi estigui repetit (recomanat; no fusiona favorits de famílies diferents) o fusionar-los.
- D/E: l'últim segment de `ficha_url` sense `.html` (slug de todofp, únic als 233 registres).
- Test: `ref` únic a tot el catàleg; el pipeline falla (fail fast) si n'hi ha de repetits.

## Passos (TDD al backend)

1. **Pipeline:** `stable_ref(record, dup_codes)` + camp `ref`. Tests d'unicitat i de format.
2. **Migració 012:** `list_items.oferta_ref TEXT`, `centres_watch.oferta_key` → ref. Backfill amb el catàleg actual (`oferta_id` → `ref` vigent). Els favorits que ja estiguin desplaçats per refrescos anteriors no es poden recuperar: on hi hagi `oferta_codigo` i no coincideixi amb el registre actual, es prioritza el codi. Es compta i s'informa de quants se n'han corregit.
3. **API favorits:** body i rutes per `ref` (string validat contra el catàleg). Es manté un període acceptant `oferta_id` com a entrada.
4. **Centres:** `oferta_centres.json` i `centres_nous_per_oferta.json` per `ref` (scraper de centres + `centres_inherit.py` + `/api/centres?ref=`). Arregla el bug de desfasament.
5. **Itinerari:** `/api/itinerari/complet?grado=&ref=`; claus de node `D:<ref>`. Els fitxers derivats interns (`d_modulos`, `ce_acces`) poden seguir per id, ja que es regeneren o es remapen al mateix refresc.
6. **Frontend:**
   - `favorites.has(row.ref)` i `selectedCentres[ref]`;
   - enllaços `itinerari.html?grado=D&ref=…`, `index.html?ref=…`;
   - `perfil.html` uneix els favorits per `ref`.
7. **Enllaços antics:** `?id=` i `?oferta=<id>` es continuen acceptant (millor esforç: poden apuntar a un altre grau si n'hi ha hagut un refresc pel mig). Els enllaços nous ja surten amb `ref`.
8. **Deploy:**
   - fer una còpia de la BD (`scripts/backup_db.sh`) abans de migrar;
   - regenerar `ref` a `ofertes.json` del VPS sense un refresc complet (script d'un sol ús que reutilitza `stable_ref`);
   - reiniciar el servei.

## Verificació

- Tests nous: `ref` estable entre dos catàlegs amb registres inserits al mig; favorits i avisos sobreviuen a la renumeració; enllaç d'itinerari amb `ref`.
- A producció: els 80 favorits es resolen a un grau existent; recompte de centres idèntic abans i després per a una mostra de D/E/C.

## STOP conditions

- Si algun `ref` surt repetit amb dades reals, aturar i informar (no inventar sufixos nous).
- Si el backfill deixa més del 10 % de favorits sense resoldre, aturar abans de desplegar.
