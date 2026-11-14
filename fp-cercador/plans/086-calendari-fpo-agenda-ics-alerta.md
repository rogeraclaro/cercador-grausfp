# Pla 086 — Calendari FPO: agenda «Comencen aviat», `.ics` i alerta de cursos nous

Origen: auditoria 2026-11-14, idea 5 de 9; disseny validat pel propietari el mateix dia.
Executable per un agent sense context, en una sessió nova. Depèn de: FPO (059–061), FPO extern
backend (063), alertes (028) i login, tots DONE. Independent dels plans 083–085.

## Què fa

Dins del mode FPO del cercador, una vista nova que ordena els cursos per data d'inici, amb botó
per afegir-los al calendari i, amb compte, una alerta per correu quan surt un curs nou que
encaixa amb el que l'usuari busca.

## Decisions del propietari (tancades, no reobrir)

| Tema | Decisió |
|---|---|
| Abast | Agenda + `.ics` + alerta per correu. |
| «A prop meu» | Vol dir «a la meva comarca». No hi ha coordenades ni càlcul de distància. |
| Alerta | Avisa quan **apareix** un curs nou. **No** hi ha recordatori «15 dies abans»: el fa el calendari de l'usuari. |

Fora d'aquesta versió: distància en quilòmetres, recordatoris, calendari subscrit que
s'actualitzi sol (`webcal`).

## Fets verificats (2026-11-14, no repetir)

- `backend/data/soc_cursos.json` (llista) i `ext_cursos.json` (llista): 1.684 cursos en local
  (1.035 SOC, 412 PIMEC, 142 Foment, 70 CCOO, 25 Cecot). Les dades locals són antigues
  (setembre); per provar, copieu-les del VPS.
- Camps d'un curs del SOC: `idCurs, titol{ca,es}, familia{codi,desc}, area, especialitat{codi,
  desc}, esCertProf, nivell, hores, modalitat, estat, dataInici, dataFi, comarca, municipi,
  provincia, centre{nom,carrer,cp,municipi,comarca,telefon,email,web…}, programaUrl, …`.
  Els externs porten a més `font` i `tipus`, i **no porten `comarca`** (656 cursos sense).
- `dataInici` (format `AAAA-MM-DD`) hi és en 1.512 de 1.684 cursos (90 %).
- 30 comarques diferents. `modalitat`: `PRESENCIAL` 1.285, `TELEFORMACIÓ` 125,
  `VIDEOCONFERÈNCIA` 102, `MIXTA` 12, buida 160.
- `estat`: `informacio`, `gestio`, `inscripcio`, o buit (externs).
- **L'FPO es refresca per dos camins**, com passava amb el catàleg abans del 2026-11-14:
  - setmanal, dins `scrapers/pipeline.py::run` (~línies 500–523: `build_soc_data`,
    `write_soc_data`, `refresh_ext_cursos`);
  - manual, `backend/app.py::_run_fpo_refresh` (~línia 889), cridat per
    `/api/admin/refresh-fpo`.
  Els cursos nous es calculen a `pipeline._soc_diff_entry` (`curr_ids - prev_ids` per
  `idCurs`), però només se'n desa el recompte, no la llista.
- No existeix cap alerta d'FPO. Les alertes de graus són a `backend/alerts_service.py`
  (patró de token de baixa amb caducitat renovable, un correu per alerta) i el seguiment de
  centres a `centres_watch_service.py`.
- Favorits d'FPO: taules de les migracions 009 i 010; pestanya `#fpo` de `perfil.html`.
- Estat del mode FPO al frontend: `fpoFilters`, `fpoEspecs`, `fetchFpoEspecs()` a
  `frontend/index.html`. Fitxa d'un curs: `_SOC_FITXA_CURS_URL` a `backend/app.py`.
- `email_service.send_email` ja té `timeout=30`.

## Agenda

### API — `GET /api/fpo/agenda` (pública)
- Paràmetres opcionals: `dies` (per defecte 90, màxim 180).
- Torna els cursos del SOC i externs amb `dataInici` entre avui i avui + `dies`, ordenats per
  `dataInici`, amb només els camps que la vista necessita:
  `idCurs, font, tipus, titol, especialitat{codi}, familia{codi,desc}, hores, modalitat,
  estat, dataInici, dataFi, comarca, municipi, centreNom, fitxaUrl, enLinia`.
- `enLinia = modalitat in {TELEFORMACIÓ, VIDEOCONFERÈNCIA}`.
- A més: `{"sense_data": N, "comarques": [...ordenades...], "generat": "AAAA-MM-DD"}`.
- Memòria cau per mtime dels dos fitxers **i pel dia** (la finestra es mou cada dia).
- Lògica pura a `backend/fpo_agenda.py::build_agenda(cursos, avui, dies)`.

### Vista (dins `index.html`, mode FPO)
- Commutador «Per especialitat» / «Comencen aviat» (grup de botons amb `aria-pressed`,
  mateix patró que el commutador de mode). L'adreça ho reflecteix: `?mode=fpo&vista=agenda`.
- Filtres: comarca, modalitat, família, tipus. Tots al navegador sobre la resposta.
  - Comarca triada: surten els cursos d'aquella comarca **i** els `enLinia` (marcats
    «en línia»). Els externs sense comarca només surten amb «Totes les comarques» o si són
    en línia.
  - La comarca es recorda a `localStorage['fpoComarca']`.
- Cursos agrupats per setmana («Aquesta setmana», «Setmana del 23 de novembre»…), amb data,
  títol, centre, municipi, hores, modalitat, estat i distintiu de tipus.
- Línia al peu: «N cursos no tenen data d'inici publicada» amb enllaç a la vista per
  especialitat.
- Estats: carregant, error amb reintent, cap curs amb aquests filtres (amb el botó «Treu els
  filtres»).
- Paginació: 50 cursos i «Mostra'n més».

## Calendari (`.ics`)

- Fitxer nou `frontend/ics.js` amb una funció pura `buildIcs(curs, lang)` i
  `downloadIcs(curs, lang)`. Sense backend ni llibreria.
- Esdeveniment de dia sencer el dia de `dataInici` (`DTSTART;VALUE=DATE`), `SUMMARY` el
  títol, `LOCATION` centre i adreça, `DESCRIPTION` hores, modalitat, data de fi i enllaç a la
  fitxa, `UID` estable (`<idCurs>@grausfp.es`), `DTSTAMP`.
- RFC 5545: finals de línia CRLF, escapar `\`, `;`, `,` i salts de línia, plegar les línies
  a 75 octets.
- Botó «Afegeix al calendari» a l'agenda i a les llistes de cursos que ja hi ha al detall
  d'una especialitat. Nom del fitxer: `curs-<slug>.ics`.
- Test del format amb Node (`node --test`) o, si el projecte no té proves de JS, un script a
  `scripts/` que n'importi la funció i validi una mostra: títol amb comes i accents, línia
  de més de 75 octets, curs sense centre.

## Alerta de cursos nous

### Dades — migració `0NN_fpo_alerts.sql` (el número següent lliure)
```sql
CREATE TABLE IF NOT EXISTS fpo_alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comarca      TEXT,            -- NULL = qualsevol
    familia_codi TEXT,            -- NULL = qualsevol
    espec_codi   TEXT,            -- NULL = qualsevol
    inclou_en_linia INTEGER NOT NULL DEFAULT 1,
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    last_sent_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_fpo_alerts_user ON fpo_alerts(user_id);
```
Cal almenys un de `comarca`, `familia_codi`, `espec_codi`. Màxim 10 **files** per usuari
(comptant les inactives, per no repetir el forat de les alertes de graus). Validació de
tipus i longitud al backend.

### API (amb sessió)
`GET /api/fpo/alerts`, `POST /api/fpo/alerts`, `PATCH /api/fpo/alerts/<id>` (activa o pausa),
`DELETE /api/fpo/alerts/<id>`, i la baixa sense sessió
`GET /api/fpo/alerts/<id>/unsubscribe?token=…`, que redirigeix a `/?unsubscribed=1` (l'avís
ja existeix a `auth.js`) i, si el token no val, també redirigeix amb un avís d'error en lloc
de tornar JSON cru.

### Enviament — `backend/fpo_alerts_service.py`
- `match(alert, curs) -> bool` (pura): comarca igual, o curs `enLinia` si
  `inclou_en_linia`; família i especialitat iguals si l'alerta les porta.
- `dispatch(nous_cursos, base_url) -> int`: agrupa per usuari i envia **un sol correu per
  usuari i refresc**, amb els cursos agrupats per alerta, enllaç a la fitxa de cada curs i
  enllaç de baixa. Usuaris `verified = 1`, `is_active = 1`, `deleted_at IS NULL`.
  Un error en una alerta no atura les altres (`try/except` per usuari).
- **Un sol punt d'entrada per als dos camins de refresc.** Funció nova a
  `scrapers/pipeline.py`, per exemple `fpo_new_courses(prev, curr) -> list`, i una crida a
  `fpo_alerts_service.dispatch` des del refresc setmanal i des de `_run_fpo_refresh`. Si
  convé, extreu el refresc de l'FPO a una sola funció compartida, com es va fer amb
  `scheduler_service.run_refresh_job` per al catàleg.
- **No s'envia res** si el refresc de la font ha fallat o si el snapshot anterior era buit
  (primer refresc o fitxer perdut: tots els cursos semblarien nous).
- Una alerta acabada de crear no rep els cursos que ja existien: només compten els `idCurs`
  nous d'un refresc posterior.

### Interfície
- A l'agenda, botó «Avisa'm de cursos nous» que crea l'alerta amb els filtres actius; sense
  sessió, obre el modal d'accés que ja existeix. Si no hi ha cap filtre, el botó demana
  triar-ne un.
- A `perfil.html#fpo`: llista de les alertes d'FPO amb pausa i esborrat.

## Fases

Cada fase acaba amb els tests verds i un commit (`feat(fpo): …`, sense atribució d'IA).

1. `fpo_agenda.py` + tests (límits de dates inclosos, sense data, en línia, externs sense
   comarca) + endpoint amb tests.
2. Vista «Comencen aviat» i filtres.
3. `ics.js` + botons + prova del format.
4. Migració + API d'alertes + tests (aïllament entre usuaris, límits, validació, baixa).
5. `fpo_alerts_service` + ganxo als dos camins de refresc + tests: coincidència, un sol
   correu per usuari, cap enviament amb refresc fallit o snapshot anterior buit, token de
   baixa caducat que es renova.
6. Interfície de l'alerta (agenda i perfil).
7. Textos `fpo.agenda.*` i `fpo.alert.*` (ca i es), línia a `politica-privacitat.html` (la
   comarca i els filtres de l'alerta es desen al compte), `?v=` i `I18N_VERSION`.
8. Verificació: suite verda; al navegador en ca i es amb dades fresques del VPS; importar un
   `.ics` a un calendari real; 375 px.

## STOP — atura't i pregunta

- Si amb dades fresques l'agenda té menys de 50 cursos dins de 90 dies, ensenya el recompte
  per mes abans de construir la vista: potser cal una finestra més llarga.
- Si unificar els dos camins de refresc de l'FPO toca més de ~80 línies de `pipeline.py`,
  descriu el canvi abans de fer-lo.
- No enviïs cap correu real durant les proves: `email_service.send_email` sempre substituït.
- No desplegar sense aprovació explícita. Mai reiniciar diumenge 11:10–11:45.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
