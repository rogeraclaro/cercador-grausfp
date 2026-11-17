# Pla 091 — Correspondència UC ↔ mòdul professional des del BOE (dades)

Origen: correus d'un usuari (docent d'FPO, 2026-11) que vol saber, mòdul a mòdul, què convalida cada
certificat de professionalitat en un cicle de grau mitjà o superior. Anàlisi del 2026-11-17. Les
decisions tècniques d'aquest pla són del redactor i es poden discutir abans d'executar-lo.
Executable per un agent sense context, en una sessió nova. Depèn de: 090. Pla mitjà-gran, només de
dades i API; la interfície és el pla 092.

## Què fa

Genera un índex nou, `backend/data/d_uc_corr.json`, amb la correspondència oficial entre unitats de
competència (UC) i mòduls professionals de cada cicle D, treta dels reials decrets dels títols, i
l'exposa per API.

## Fets verificats (2026-11-17, no repetir)

- Avui la relació certificat LOE → cicle és `ciclos_fp.json` (buscador de todofp): només el nom del
  cicle, sense mòduls; 338 dels 588 certificats en tenen algun.
- Cada fitxa de cicle a todofp enllaça els seus decrets al BOE (`href="https://www.boe.es/…"`; de
  vegades `txt.php?id=BOE-A-…`, de vegades adreça ELI, que cal resoldre a l'identificador).
- L'XML obert del BOE (`https://www.boe.es/diario_boe/xml.php?id=<BOE-A-…>`) porta dues taules:
  - **Annex V A)** «Correspondencia de las unidades de competencia acreditadas … con los módulos
    profesionales para su convalidación»: columnes «Unidades de competencia acreditadas» i «Módulos
    profesionales convalidables».
  - **Annex V B)** «Correspondencia de los módulos profesionales con las unidades de competencia para
    su acreditación»: «Módulos profesionales superados» i «Unidades de competencia acreditables».
  Una fila pot agrupar diverses UC i diversos mòduls (totes les UC de la fila donen tots els mòduls de
  la fila). Els mòduls porten codi de quatre xifres («0235. Instalaciones eléctricas interiores.»).
- El títol de l'annex és **fora** de la taula; cal reconèixer la taula per les capçaleres de columna.
  Els decrets antics fan servir `<td>` a la capçalera i els nous `<th>`; hi ha files amb `rowspan`.
  Variants de format del codi de mòdul vistes: «0624.Comercialización» (sense espai), «0902 .Planificación»,
  «O856.» (lletra O per zero).
- Cobertura amb el lector de prova (`plans/outputs/analisi-20261117/scripts/fetch_rd.py` i
  `parse_rd.py`; sortida `rd_final.json`), comptant només el decret propi de cada títol:

  | Tipus | Total | Amb V A | Amb V B |
  |---|---|---|---|
  | Grau mitjà | 67 | 59 | 56 |
  | Grau superior | 94 | 83 | 80 |
  | Grau bàsic | 34 | 0 | 1 |
  | Grau E | 38 | 9 | 8 |

- Amb això, 418 dels 584 certificats LOE tenen almenys una UC amb mòdul convalidable i 218 les tenen
  totes; 120 certificats que avui no mostren cap cicle en passarien a tenir. Hi ha 40 certificats que
  todofp relaciona amb un cicle i que no surten per aquesta via (probablement per títols bàsics o
  decrets modificats; cal mirar-ho).
- **Decrets que substitueixen annexos.** Els RD 498/2024 (`BOE-A-2024-10683`, bàsics), 499/2024
  (`BOE-A-2024-10684`, mitjans) i 500/2024 (`BOE-A-2024-10685`, superiors), i `BOE-A-2024-10682`,
  modifiquen molts títols alhora. Llegit al 500/2024: «En el Real Decreto 1685/2007 … por el que se
  establece el título de … se sustituyen los anexos V A) y V B) por la siguiente redacción». Porten
  149, 192, 201 i 48 files V A respectivament. Sense aplicar-los es publicarien taules derogades.
- **Títols bàsics.** Comparteixen decret d'establiment (`BOE-A-2014-2360` 14 títols, `BOE-A-2014-5591`
  7, `BOE-A-2015-9462` 6); aquests només porten taula V B. El RD 498/2024 hi afegeix un apartat
  «6 bis. Correspondencia de las unidades de competencia acreditadas con los módulos profesionales
  para su convalidación» per títol. Cal atribuir cada taula al seu títol pel text que la precedeix.
- **Notes fora de taula**, del tipus «quien tenga acreditadas todas las unidades de competencia … tendrá
  convalidado el módulo profesional "1233. …"». No són files i s'han de recollir a part.
- 17 cicles de grau mitjà i superior sense taula detectada (`cicles_sense_taula.json`): uns són
  anteriors al sistema d'UC (1995–2003: Cuidados Auxiliares de Enfermería, Dietética, Joyería, Óptica),
  d'altres del 2007 (Mecanizado, Cocina y Gastronomía, Panadería) i algun de nou. Cal mirar-los un per un.
- Graus E: la majoria dels 28 sense taula són cursos nous; en tres decrets mirats no hi ha cap UC (dos
  van per «estándares de competencia»). No s'hi pot extreure correspondència d'UC.
- `d_modulos.json` va per `id` de registre, i els `id` es reassignen a cada refresc
  (`backend/scrapers/pipeline.py`, línia ~111, amb `remap_d_modulos`). Els cicles tenen un `ref`
  estable (pla 076), per exemple `electricidad-electronica~instalaciones-electricas-automaticas`.
- Només 870 dels 3.206 mòduls de `d_modulos.json` porten número. Les taules del BOE el porten sempre.
- El Python del sistema d'aquest Mac falla amb `urllib` per certificats SSL; `requests` (que fa servir
  el projecte) i `curl` funcionen.

## Disseny

- Índex nou per `ref` de cicle (no per `id`), perquè sobrevisqui als refrescos:

  ```json
  {"<ref cicle>": {
     "decret": "BOE-A-2008-3957", "vigent": "BOE-A-2024-10684",
     "convalida":  [{"uc": ["UC0820_2", "UC0821_2"], "moduls": [{"num": "0235", "name": "…"}]}],
     "acredita":   [{"moduls": [{"num": "0235", "name": "…"}], "uc": ["UC0820_2", "UC0821_2"]}],
     "notes": ["…"]}}
  ```

  `vigent` és el decret d'on surt la taula que s'ha fet servir (el propi o el que la substitueix).
- Mòdul nou `backend/scrapers/boe_corr_scraper.py` amb funcions pures de lectura d'XML (testejables
  sense xarxa) i un script `scripts/build_d_uc_corr.py` que baixa i escriu. Execució manual, com
  `generate_bc_loe.py` i `build_c_modulos.py`; **no** s'afegeix al refresc setmanal en aquest pla.
- Ordre d'aplicació per títol: taula del decret propi; si un decret modificador posterior substitueix
  els annexos d'aquest títol, guanya el modificador. L'atribució es fa pel número de reial decret citat
  al text que precedeix la taula («En el Real Decreto NNNN/AAAA…»), casat amb el decret propi del títol.
- Informe d'auditoria a `plans/outputs/audit_d_uc_corr.md`: cicles sense taula i per què, files sense
  mòdul llegit, UC que no existeixen com a mòdul B LOE al nostre catàleg, i comparació amb
  `ciclos_fp.json` (certificats que todofp relaciona i el BOE no, i a l'inrevés).
- API: `GET /api/correspondencia?cicle=<ref>` (taules del cicle) i
  `GET /api/correspondencia?cp=<codi>` (per a un certificat LOE: per cada cicle amb alguna UC seva, els
  mòduls que convalida, quines UC del certificat hi intervenen i quants mòduls del cicle queden).
- Aprofitar per omplir el `num` dels mòduls de `d_modulos.json` quan el nom normalitzat
  (`cd_lomloe.normalize_module_name`) casi amb un mòdul de la taula. Si això toca massa el refresc,
  deixar-ho en una funció de lectura a `app.py` i no reescriure el fitxer.
- Regla de càlcul: una UC només convalida un mòdul quan **totes** les UC de la seva fila estan
  acreditades. La funció que ho calcula ha de ser pura i testejada.
- Graus E i títols anteriors al sistema d'UC: fora d'abast; han de quedar llistats a l'informe.

## Fases

1. Tests primer, amb fragments reals d'XML desats com a fixtures: decret antic (`<td>`), decret nou
   (`<th>`), fila amb `rowspan`, fila amb diverses UC i diversos mòduls, les tres variants de codi de
   mòdul, i una nota fora de taula.
2. Lector d'XML i resolució d'enllaços (inclosa l'adreça ELI).
3. Aplicació dels decrets modificadors amb atribució per títol; test amb el cas de l'RD 1685/2007
   (Audiología protésica) dins del 500/2024.
4. Títols bàsics: atribució de les taules dels decrets compartits i del «6 bis» del 498/2024.
5. Script generador, informe d'auditoria i revisió manual dels 17 cicles sense taula.
6. Regla de càlcul i API, amb tests. Cas de referència: ELEE0109 (UC0820_2 … UC0825_2) contra «Técnico
   en Instalaciones Eléctricas y Automáticas»: convalida 0232 i 0238 (per UC0822_2), 0240 (UC0825_2),
   0235 (UC0820_2 + UC0821_2) i 0236 (UC0823_2 + UC0824_2); queden fora 0237 i 0239. Comprovar abans
   si el 499/2024 ha substituït aquesta taula.

## STOP — atura't i pregunta

- Si la cobertura de grau mitjà i superior queda per sota del que dona el lector de prova (59 i 83).
- Si no es pot atribuir amb seguretat una taula d'un decret compartit a un títol: no endevinar; deixar
  el títol sense taula i dir-ho a l'informe.
- Abans de reescriure `d_modulos.json` o de tocar `pipeline.py`.
- Ritme de baixada: una petició per segon com a màxim, a todofp i al BOE.
- No desplegar sense aprovació explícita.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`. `d_uc_corr.json` s'ha de copiar al
VPS (no viatja amb el git).
