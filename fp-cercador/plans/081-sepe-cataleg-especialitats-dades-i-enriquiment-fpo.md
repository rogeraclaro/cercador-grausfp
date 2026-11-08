# Pla 081 — Catàleg d'Especialitats Formatives del SEPE: dades + enriquiment de l'FPO

Origen: investigació 2026-11-08 (sessió amb el propietari). Objectiu doble del propietari:
(1) enriquir i completar l'FPO de Catalunya; (2) mostrar el catàleg estatal a part (→ pla 082).
Aquest pla fa la part de dades (scraper + JSON + pipeline) i l'enriquiment de l'FPO.
Depèn de: 059–061 (FPO SOC) DONE. Executable per un agent sense context.

## Marc conceptual (verificat, no repetir)

- **No és un Grado.** LO 3/2022 = Grados A–E (sistema de FP). El Catàleg d'Especialitats
  Formatives és la **formació en el treball** (Llei 3/2023 d'Ocupació; RD 438/2024 art. 24):
  "recogerá todas las ofertas formativas de la formación en el trabajo, sin que las mismas
  puedan estar asociadas a cualificaciones profesionales ni duplicadas con [...] el Catálogo
  Nacional de Ofertas de FP". Regulat per l'Ordre TMS/283/2019.
- **Els certificats de professionalitat (= Grado C) ja NO hi són.** Comprovat: el filtre per
  codi retorna 0 resultats per a ADGD0108 i IFCT0109 (amb i sense "última versión"),
  i 1 per a COMM0006 (el filtre funciona).
- **L'FPO del SOC barreja els dos mons.** Creuament amb `backend/data/soc_especs.json`
  (2.974 especialitats):
  - 585 `esCertProf=true` → 0 al catàleg SEPE (són Grado C, ja integrats via `/api/fpo/by-cert`).
  - 2.213 no vinculades → **totes** al catàleg SEPE.
  - 176 no vinculades que no hi són: 145 `CTR*` (probablement pròpies del SOC) + variants
    (`AGAO0308M`, `COMM20`…).

## Diagnosi tècnica de la font (verificada 2026-11-08, no repetir)

Cercador: `https://sede.sepe.gob.es/FOET_CATALOGO_EEFF_SEDE/flows/main` (JSF/MyFaces + DataTables).

**Llistat complet — endpoint REST intern, sense captcha ni login:**
1. `GET /FOET_CATALOGO_EEFF_SEDE/flows/main` → redirigeix a `?execution=e1s1` i posa cookies
   (`JSESSIONID_formacion_cl`, `TS0141…`). Sense aquest GET previ → 302 a `/flows/error`.
2. `POST /FOET_CATALOGO_EEFF_SEDE/rest/paginacionEspecialidades`, `Content-Type: application/json`:
   ```json
   {"dtInfo":[{"name":"draw","value":1},
              {"name":"columns","value":[{"data":0,"name":"","searchable":true,"orderable":false,"search":{"value":"","regex":false}}, ... data 0..10 ...]},
              {"name":"order","value":[{"column":1,"dir":"asc"}]},
              {"name":"start","value":0},{"name":"length","value":2000},
              {"name":"search","value":{"value":"","regex":false}}],
    "filtro":[{"name":"formulario:ultimaVersionCuadrado","value":"true"},
              {"name":"formulario_SUBMIT","value":"1"},
              {"name":"javax.faces.ViewState","value":"e1s1"},
              {"name":"formulario:acordeonPrincipal:tabOpcionesAvanzadas:tutoriaPresencialWrapper:tutoriaPresencial","value":"000"},
              ... igual per aulaVirtualSeleccionada, vinculacion, centroMovil, otrosRequisitos (tots "000") ...],
    "enAltaIF":false,"enSEDE":true,"tipoBuscador":"buscadorEspecialidades"}
   ```
   (El filtre per codi és `formulario:codigoWrapper:codigoEsp`.)
3. **La resposta és Latin-1, no UTF-8**: `resp.content.decode('latin-1')` abans de `json.loads`.
4. `recordsFiltered` = total (7.544 el 2026-11-08). `length=2000` funciona → 4 peticions, ~4 s.
   Parar quan `len(data) < length`.

**Cada fila (`data[i]`) és una llista d'11 cel·les, algunes amb HTML:**

| idx | contingut | com extreure'l |
|---|---|---|
| 0 | HTML amagat amb `FECHA INICIO VIGENCIA: dd/mm/aaaa`, `FECHA FIN VIGENCIA: dd/mm/aaaa` | regex |
| 1 | codi (`ADGA12DCP`) | text |
| 2 | `<a onclick='getProgramaFormativoEspecialidad(107)'>…title='DENOMINACIÓ'` | id intern = regex `\((\d+)\)`; denominació = text sense tags + `html.unescape` |
| 3 | versió (int) | |
| 4 | família (text, ES, majúscules) | |
| 5 | àrea (text) | |
| 6 | competència transversal (`-` si no n'hi ha) | |
| 7 | nivell (`1`–`5` o `Sin especificar`) | |
| 8 | modalitat (`Presencial`, `Teleformación`, `Mixta`, `Presencial y teleformación`, `Presencial y mixta`) | |
| 9 | hores | |
| 10 | botó entitats (`getEntidadesFormacion(107)`) | ignorar |

Distribució (2026-11-08): nivell `Sin especificar` 2.119; competència transversal ≠ `-` 404;
sufixos de codi `PO` 2.124 (tots amb vigència des del 19/07/2016), `EXP` 105, `DCP` 28, `CCC` 23.
El significat dels sufixos **no està verificat**: no el mostris a la UI.

**Programa formatiu (PDF)**, verificat amb l'id 107:
```
POST /FOET_CATALOGO_EEFF_SEDE/flows/main?execution=e1s1   (multipart/form-data, mateixa sessió)
  formulario_SUBMIT=1
  javax.faces.ViewState=e1s1
  formulario:codigoPropuesta=<id intern>
  formulario:invisibleClickTargetProgramaFormativoEspecialidad=
→ 200, Content-type: pdf, Content-disposition: attachment; filename=<CODI>.pdf
```
El PDF té text (no és escanejat). Els camps van numerats: "1. Familia Profesional", "5. Objetivo
general", "7. Criterios de acceso", "9. Relación secuencial de módulos formativos"… Si no hi ha
document, el servidor torna l'HTML amb el modal "no tiene documento asociado" i no un PDF: cal
comprovar el `Content-type`.

**Entitats de formació** (`getEntidadesFormacion(id)`): és un flux JSF amb estat (passa a
`execution=e1s2`, pàgina "Entidades de formación", 82 entitats per a l'id 107: id, nom, modalitat,
província). **Fora d'abast**: caldrien 7.544 navegacions amb estat. Es pot reprendre en un pla futur.

Scripts del spike (només de referència, no al repo): `fetch.py` i `clean.py` a l'scratchpad de la sessió 2026-11-08.

## Fase 1 — Scraper `backend/scrapers/sepe_scraper.py`

- Patró: el de `soc_scraper.py` (`build_*_data()` + `write_*_data()` amb escriptura atòmica via `tempfile`).
- Fer servir `requests.Session()` (dependència ja permesa), amb `User-Agent` de navegador i un timeout de 30 s.
- `build_sepe_data() -> list[dict]`, un dict per especialitat:
  ```
  {codi, idSepe:int, titol_es, versio:int, familia_es, area_es,
   competenciaTransversal: str|None, nivell: int|None, modalitat, hores: float,
   vigenciaInici: 'AAAA-MM-DD'|None, vigenciaFi: 'AAAA-MM-DD'|None}
  ```
  `familia_codi` = els 3 primers caràcters del codi, `area_codi` = els 4 primers. Són els mateixos codis que el SOC (`ADG`/`ADGD`).
- Validació fail-soft: si hi ha menys de 5.000 registres o algun codi duplicat, s'aixeca una excepció i **no s'escriu**: es conserva el JSON anterior.
- `write_sepe_data(rows, data_dir)` → `backend/data/sepe_especs.json`.
- Tests a `backend/tests/test_sepe_scraper.py` amb fixtures desades (una resposta JSON
  de 3 files reals, en Latin-1). Han de cobrir el parseig de cada cel·la, el decode Latin-1, la paginació (parar quan
  `len < length`) i que, si el resultat té menys de 5.000 registres, no s'escrigui. **Sense xarxa** (`gotcha`: els tests de scrapers amb xarxa
  s'ignoren; aquest no n'ha de dependre).

## Fase 2 — Pipeline i refresc

- `backend/scrapers/pipeline.py`: afegir un pas no fatal després del SOC (vora la línia 440). Ha de seguir el
  mateix patró `try/except` amb `logger.warning` i `_notify_admin_soc_failure(..., source='SEPE',
  stamp_name='last_sepe_alert.json')`.
- El catàleg canvia poc: **només refrescar si `sepe_especs.json` té més de 7 dies**. Són 4 peticions.
- Respectar `feedback`: no reiniciar el servei durant el refresc del diumenge (11:10–11:45).

## Fase 3 — Enriquiment de l'FPO (backend)

A `backend/app.py`:
- Afegir `SEPE_ESPECS_PATH` i `_get_sepe_especs()` amb `_read_soc_list` i una cache pròpia,
  més un índex `{codi: row}`.
- A `_soc_espec_index()` (≈ línia 1652), afegir a cada entrada:
  - `vinculacio`: `'grauC'` si `esCertProf`; `'sepe'` si el codi és a l'índex SEPE; si no, `'propiaSoc'`.
  - `vigenciaFi`, `competenciaTransversal`, `modalitatOficial` (del SEPE, `None` si no hi és).
  - La cache s'ha d'invalidar també pel mtime de `sepe_especs.json`, que s'afegeix a la `key`.
- A `api_fpo_especialitat`: afegir `sepe: {idSepe, vigenciaInici, vigenciaFi, versio}` o `null`.
  Si `programaUrl` és buit i hi ha `idSepe`, afegir `programaSepeUrl: '/api/sepe/programa/<codi>'` (l'endpoint és del pla 082; si el 082 encara no és fet, ometre aquest camp).
- Tests a `test_fpo_api.py`: un fixture SEPE mínim; les tres classes de `vinculacio`; i que, sense
  `sepe_especs.json`, tot continuï funcionant igual que ara (camps a `None`).

## Fase 4 — Enriquiment de l'FPO (UI, `frontend/index.html`)

- Al panell de l'especialitat (≈ línia 4397, al costat de `fpo.badge.certprof`):
  - Badge `fpo.badge.grauC` per a `vinculacio==='grauC'`: reaprofitar el badge actual, que ja ho fa.
  - Badge `fpo.badge.formacioTreball` per a `'sepe'`, amb tooltip `fpo.tooltip.formacioTreball`:
    "Formació en el treball (catàleg estatal del SEPE). No condueix a cap certificat oficial del
    sistema de FP".
  - Badge `fpo.badge.propiaSoc` per a `'propiaSoc'`.
  - Si `competenciaTransversal`, un xip amb el text.
  - Si `vigenciaFi` cau en menys de 6 mesos, un avís petit `fpo.avis.vigencia`.
- Filtre nou "Tipus de formació" (Grado C / Formació en el treball / Pròpia del SOC). Ha de conviure amb el
  toggle actual `certprof` (línia 3245): el toggle es manté i el filtre nou l'amplia.
- i18n: totes les claus noves a `frontend/i18n.js` en CA i ES. Zona de risc coneguda: res de
  literals dins `x-text`.
- Si es toca `site.css`, fer bump de `?v=`.

## Fora d'abast

- Mostrar especialitats sense curs a Catalunya dins el mode FPO: és el pla 082 (catàleg a part).
- Entitats de formació (veure la diagnosi).
- Traduir al català els títols SEPE: l'FPO ja té `titol.ca` del SOC per a les 2.213 coincidents.

## Verificació

- `pytest backend/tests -k "sepe or fpo"` en verd.
- Execució real local: `sepe_especs.json` amb ≥ 7.000 registres i codis únics.
- Al navegador: una especialitat SOC no vinculada (p. ex. `ADGD0001`) mostra el badge "Formació en el
  treball"; una de CP mostra el badge actual; una `CTR*` mostra "Pròpia del SOC".
- Deploy segons `reference_deploy_procedure` (amb un primer refresc manual al VPS per generar el JSON).
