# Pla 055 — Centres per a Grau C LOMLOE (pla nou)

Origen: `plans/outputs/spike_centres_abc_results.md` (2026-09-06). Executable
per un agent sense context: tot el que cal saber és aquí o als fitxers citats.

## Context

`backend/scrapers/centres_scraper.py` consulta el Registre Estatal
d'Entitats de Formació per a C LOE (`plan_antiguo=True`, per `ofertaCodigo`),
D i E (per `ofertaDenominacion`+`gradoProfesional`). Les **397 ofertes C amb
`plan_antiguo=False`** (codis `FAM_C_NNN_NL`, ex. `ADG_C_001_3B`) no es
consulten mai, tot i que el spike ha verificat que el mateix endpoint
respon amb `ofertaCodigo={codi complet}` i el mateix format de 13 columnes
que ja parseja `_parse_centre`.

Fets verificats (no cal tornar-los a comprovar):
- `ofertaCodigo=ADG_C_001_3B` → 35 centres. Mostra de 25 codis: 16 amb
  centres, 9 amb 0 (ofertes noves sense acreditació — és normal, no error).
- El filtre és `LIKE`: cal el codi complet; `ofertaCodigo=ADG_C` retornaria
  66 files barrejades. Cercar per denominació **no** funciona per C-nou.
- Graus A i B **no** existeixen al registre. Fora d'abast d'aquest pla.

## Decisió de disseny: clau a `oferta_centres.json`

**Clau = `str(oferta['id'])`** (com D/E), **no** el `codigo`.

Motiu: `frontend/index.html:1595,1600,1613` i `frontend/perfil.html:657,698`
ja decideixen `row.grado === 'C' && row.plan_antiguo ? codigo : String(id)`.
Amb clau per `id`, C LOMLOE cau automàticament al cas `id=` i **no cal
tocar cap fitxer del frontend**, ni `/api/centres`, ni `centres-watch`.
El spike suggeria `codigo`; aquesta evidència del frontend ho descarta.

## Fase 1 — Test primer (TDD estricte)

Crear `backend/tests/test_centres_scraper.py`. No hi ha tests previs del
mòdul. Patró d'aïllament: `monkeypatch.setattr(centres_scraper,
'_OFERTES_PATH', str(tmp_path / 'ofertes.json'))` (mateix estil que
`test_pipeline.py:69`).

Tests a escriure (han de FALLAR abans de la Fase 2):

1. `test_load_ofertes_separa_c_lomloe`: amb un `ofertes.json` de 5
   registres (C LOE, C LOMLOE, D, E, A), `_load_ofertes()` retorna **4**
   llistes `(c_loe, c_lomloe, d_list, e_list)` i la C LOMLOE conté només
   el registre amb `grado='C', plan_antiguo=False`.
2. `test_scrape_centres_c_lomloe_usa_ofertaCodigo_i_clau_id`: monkeypatch
   `_bootstrap` → sessió dummy, `_fetch` → funció que registra els `params`
   rebuts i retorna una fila de 13 columnes fake, `RATE_LIMIT_SEC` → 0,
   `_save` → no-op. Amb un únic registre C LOMLOE `{id: 11683, codigo:
   'ADG_C_001_3B', …}`, comprovar:
   - s'ha cridat `_fetch` amb `params['ofertaCodigo'] == 'ADG_C_001_3B'` i
     **sense** `gradoProfesional`;
   - `oferta_centres` té la clau `'11683'` (string) i no `'ADG_C_001_3B'`.
3. `test_report_phase_c_lomloe`: amb `on_progress` capturador, apareix una
   fase amb etiqueta `'Grau C (pla nou)'` (inici i final).

Executar: `cd backend && python -m pytest tests/test_centres_scraper.py -v`
→ tots vermells (el 1 per `ValueError: too many values to unpack`).

## Fase 2 — Implementació (`backend/scrapers/centres_scraper.py`)

Canvis quirúrgics, seguint exactament el patró dels blocs existents:

1. `_load_ofertes()` → retorna `tuple[list, list, list, list]`:
   ```python
   c_lomloe = [r for r in all_ofertes if r.get('grado') == 'C' and not r.get('plan_antiguo')]
   return c_loe, c_lomloe, d_list, e_list
   ```
   Actualitzar el desempaquetat a `scrape_centres()`.
2. Nou bloc **entre C LOE i D** (per mantenir l'ordre "C → D → E" al
   progress de l'admin):
   ```python
   # ── Grado C LOMLOE (per ofertaCodigo, clau = id intern) ──
   logger.info('=== Grado C LOMLOE: %d ofertes ===', len(c_lomloe))
   _report('Grau C (pla nou)', 0, len(c_lomloe))
   for i, oferta in enumerate(c_lomloe):
       key = str(oferta['id'])
       ids = _do_fetch({
           'ofertaCodigo': oferta['codigo'],
           'iDisplayLength': PAGE_SIZE,
           'iDisplayStart': 0,
           'draw': 1,
       })
       oferta_centres[key] = ids
       if (i + 1) % 50 == 0:
           logger.info('C LOMLOE %d/%d — centres únics: %d', i + 1, len(c_lomloe), len(centres_by_id))
           _save(centres_by_id, oferta_centres)
           _report('Grau C (pla nou)', i + 1, len(c_lomloe))
   logger.info('C LOMLOE complet: %d centres únics', len(centres_by_id))
   _save(centres_by_id, oferta_centres)
   _report('Grau C (pla nou)', len(c_lomloe), len(c_lomloe))
   ```
3. Docstring del mòdul: afegir la línia del flow
   `Per cada oferta C LOMLOE: GET /datosTablaPublico?ofertaCodigo={code}` i
   a "Clau dels resultats": `Grado C LOMLOE: clau = id intern (com D/E)`.
   Rate-limit: `~1.212 consultes` (815 + 397), `~20 min`.

Executar tests → verds. Executar tota la suite `python -m pytest` per
confirmar que res més trenca (`test_api.py` toca `/api/centres`).

## Fase 3 — Verificació real (local, sense desplegar)

```bash
cd backend && python3 -c "
from scrapers import centres_scraper as cs
c_loe, c_lomloe, d, e = cs._load_ofertes()
print(len(c_loe), len(c_lomloe), len(d), len(e))   # esperat: 584 397 195 36
s = cs._bootstrap()
rows = cs._fetch(s, {'ofertaCodigo': c_lomloe[0]['codigo'], 'iDisplayLength': 10000, 'iDisplayStart': 0, 'draw': 1})
print(c_lomloe[0]['codigo'], len(rows), cs._parse_centre(rows[0])['nombre'] if rows else '-')
"
```
Esperat: `ADG_C_001_3B 35 TAJAMAR` (o similar; el nombre pot variar).

**No** executar el scraping complet en local: triga ~20 min i el
`oferta_centres.json` local no és el de producció.

## Fase 4 — Desplegament i scraping a producció

1. Commit convencional: `feat(centres): scrape centres for grado C LOMLOE
   offers`.
2. Abans de `git pull` al VPS, **comprovar drift** (hi ha precedent de
   feina feta per SSH sense commit — veure memòria del projecte): `git
   status` + `git log -3` al VPS. Si hi ha canvis locals, aturar-se i
   preguntar.
3. Reiniciar el backend amb el procediment habitual del projecte (PM2;
   usar `pm2-safe-save`, mai `pm2 save` a seques).
4. Llançar el scraping des de `admin.html` (botó de refresc de centres →
   `POST /api/admin/refresh-centres`). Observar que apareix la fase
   "Grau C (pla nou)" i que el resum final reporta `total_ofertes` ≈ 1.212
   (abans 815).
5. Comprovar a `index.html` una oferta C-nou coneguda (ex. `ADG_C_001_3B`,
   `IFC_C_005_5B`) → el comptador de centres > 0 i el desplegable llista
   centres. Comprovar també una amb 0 (ex. `AGA_C_002_4B`) → sense botó /
   comptador 0, sense error.

## Fase 5 — Documentació

- `.planning/quick/20260614-centres-scraper/SUMMARY.md`: afegir secció
  "Ampliació 2026-09 (Pla 055)" amb el nombre real de relacions noves i
  centres únics nous obtinguts a la Fase 4.
- `plans/README.md`: entrada del pla 055 si el fitxer manté un índex.

## Fora d'abast (explícitament)

- Graus A i B: cap font pública. Requereix primer el spike 043 (B LOMLOE →
  C LOMLOE) i decidir com mostrar "centres heretats del C pare". Pla a part.
- Canvis al frontend: cap. Si en algun moment es volgués mostrar el codi
  del certificat al desplegable de centres, seria un altre pla.
- `centres_url_enricher.py`: els centres nous que aparegui n'heretaran el
  flux d'enriquiment existent al següent run; no cal tocar-lo.

## Riscos

- **Volum de sessió**: +397 consultes; `SESSION_REFRESH_EVERY=200` ja
  cobreix el re-bootstrap. Cap canvi.
- **Fals positiu per `LIKE`**: només si algun codi C-nou fos prefix d'un
  altre. Format `FAM_C_NNN_NL` de longitud fixa → no passa. Igualment,
  el test 2 verifica que s'envia el codi complet.
- **Detecció de "centres nous"** (`get_centres_nous`, snapshot): el primer
  run després del desplegament marcarà com a "nous" tots els centres de
  C-nou que no fossin ja al catàleg per altres ofertes. És el comportament
  esperat i coherent amb el Pla 054; avisar-ho a l'usuari al resum.
