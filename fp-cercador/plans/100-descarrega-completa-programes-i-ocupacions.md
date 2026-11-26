# Pla 100 — Descàrrega completa dels programes formatius i les ocupacions del SEPE

Prioritat P2 · Mida L · Depèn de: 096 · Idees 6 i 17 (dades) i part de la 16.
Executable per un agent sense context. En depenen els plans 101 i 103.

## Context comú (llegir abans de començar)

- Origen: sessió del 2026-11-26, després de desplegar el pla 082 (especialitats del SEPE al cercador
  principal). El propietari va repassar 21 idees una per una; aquest pla en recull les decisions.
  Llegir primer `plans/082-cataleg-estatal-especialitats-pagina.md` (secció «Canvi de decisió») i la
  «Diagnosi tècnica» de `plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md`.
- Peces que ja existeixen (pla 082): `backend/scrapers/sepe_scraper.py` (`build_sepe_data`,
  `fetch_programa_pdf`), `backend/app.py` (`_sepe_index`, `_sepe_llista`, `/api/sepe/especialitats`,
  `/api/sepe/programa/<codi>`), `frontend/index.html` (estat `sepe*`, getter `filteredSepe`, bloc
  `<section class="sepe-block">`, pestanya `filterGrado === 'SEPE'`), claus `sepe.*` a `frontend/i18n.js`.
- Convencions: codi, comentaris i commits en anglès (commits convencionals, sense atribució d'IA); text
  d'interfície en català i castellà a `i18n.js` (sense literals dins `x-text`); `x-if` amb una sola arrel.
- En tocar `i18n.js` cal pujar `?v=` a **totes** les pàgines de `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`. En tocar `site.css`,
  `search-tools.js`, `footer.js` o `feedback.js`, pujar el seu `?v=`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
  (tot verd el 2026-11-26: 737) i `python3 -m pytest -q tests/test_sepe_scraper.py`. Frontend:
  `node scripts/test_search_tools.js`.
- `rg` no mira `backend/data/` (és a `.gitignore`): per buscar a les dades cal `rg -uu`.
- Deploy: `git push cercador-grausfp master`; `ssh contabo`, `git pull --ff-only` al directori del site;
  si hi ha canvis de backend, `systemctl restart fp-cercador`. **Mai reiniciar durant un refresc**
  (`curl localhost:8033/api/refresh-status`). Confirmar sempre amb el propietari abans de desplegar.

## Diagnosi (mostra de 7 programes baixats el 2026-11-26)

Tots els PDF tenen text (pdfplumber els llegeix), però hi ha **tres formats**:

| Format | Vigència d'inici | Especialitats (aprox.) | Com és |
|---|---|---|---|
| Modern | 2021–2026 | ~5.050 (67 %) | Apartats amb títol: «Objetivo general», «Relación de módulos de formación» (Módulo N · nom · hores), «Modalidades de impartición», «Duración de la formación» (inclou «Duración total de las tutorías presenciales: N horas»), «Requisitos de acceso del alumnado», «Prescripciones de formadores y tutores», «Ocupaciones y puestos de trabajo relacionados» (codi de 8 dígits + nom), «Vinculaciones con capacitaciones profesionales» (no sempre), i «DESARROLLO MODULAR» amb objectiu i continguts per mòdul |
| «PO» | 2016–2018 | ~2.200 (29 %) | Camps numerats: «4. Objetivo General:», «6. Duración: Horas totales … Distribución de horas: Presencial … Teleformación …», continguts |
| Antic | abans del 2015 | ~100 (1 %) | Numerat i variable: «4. Nivel de cualificación», «5. Objetivo general:», continguts |

Mostres: SSCE22 (modern, 11 pàg.), SSCE0001 (modern, 14), ADGN0023 (modern, 37 pàg.), SSCE29EXP (modern),
`CTRL0068` (modern), SSCE001PO («PO», 4 pàg.), ADGA12DCP (antic, 8 pàg.), AGAN01CCC i FMEC05EXP (antic).
Les xifres per format surten de l'any d'inici de vigència, no d'obrir els 7.544.

**Ocupacions**: millor el botó del cercador que el PDF (estructurat i cobreix formats antics):

```
POST …/flows/main?execution=e1s1  (mateix patró que el PDF; veure pla 099)
  formulario:invisibleClickTargetShowOcupaciones=
→ HTML amb el modal `modalOcupaciones`: taula «Código Ocupación | Denominación»
```
SSCE22 → 23291010 Formadores de formación no reglada, 23211034 Formadores de formadores, 23291029
Formadores de formación para el empleo. IFCD0025 → 2. ADGA12DCP → 1. SSCE001PO → cap (les «PO»
probablement no en tenen; només una mostra).

PDF: mateix POST amb `formulario:invisibleClickTargetProgramaFormativoEspecialidad=`
(`sepe_scraper.fetch_programa_pdf`, ~4–5 s per programa).

## Decisions preses amb el propietari

- **Descàrrega completa**, no a demanda, perquè en depenen les pàgines públiques (101), la cerca per
  ocupació (103) i els graus relacionats.
- Es fa **des de l'ordinador del propietari**, no des del VPS, i el resultat es copia al servidor (com
  `sepe_especs.json` al pla 081). Així, si el SEPE bloqueja una IP, no és la de producció.
- **A poc a poc**, amb aturada automàtica i represa.
- Es guarda **el contingut extret, no els PDF** (els PDF continuen a demanda amb la cache del pla 082).
- Cal un **avís al panell d'administració** quan toqui repetir-la, que digui exactament què s'ha de fer.

## Què s'ha de fer

### 1. Lector de programes (`backend/sepe_programa.py`, funcions pures)

- `parse_programa(text) -> dict | None` detecta el format i retorna:
  `{format, objectiu, moduls: [{nom, hores}], requisits_acces, tutories_presencials_h,
  vinculacions, hores_presencial, hores_teleformacio}` (els camps que no hi són, `None`).
- Primera versió: format modern complet + objectiu i distribució d'hores del format «PO» + objectiu del
  format antic. Text en castellà, tal qual (no es tradueix).
- **Validació**: si hi ha mòduls, la suma d'hores ha de coincidir amb les hores del catàleg (tolerància
  ±1). Si no quadra, es descarten els mòduls d'aquella especialitat (`moduls_ok: false`) i es conserva la
  resta. Un programa que no es pot llegir → `None` (la fitxa mostrarà només el PDF).

### 2. Script de descàrrega (`scripts/sepe_descarrega_programes.py`)

- Entrada: `backend/data/sepe_especs.json`. Sortida: `backend/data/sepe_programes.json`
  (`{codi: {versio, baixat, programa: {...}|null, ocupacions: [{codi, nom}], sense_pdf: bool}}`) i un
  informe a `plans/outputs/sepe-programes-<data>.md`.
- Per especialitat: una sessió (`GET flows/main`), POST del PDF, POST d'ocupacions. Pausa de 5–10 s entre
  especialitats (paràmetre), `User-Agent` de navegador.
- **Represa**: desa l'estat cada 25 especialitats (escriptura atòmica) i en tornar a arrencar salta les
  que ja té amb la mateixa `versio`.
- **Aturada automàtica**: 5 errors de xarxa seguits, o un 403/429 → atura't i digues-ho. Mai reintentar
  en bucle.
- Mode `--nomes-canvis`: només les noves o les que han canviat de `versio` (per a l'ús habitual).
- No s'executa al VPS ni durant el refresc del diumenge.
- Abans d'executar-lo sencer: provar-lo amb 50 especialitats i revisar l'informe.
- Abans de publicar res: llegir les condicions de reutilització de la seu del SEPE (són documents públics
  i se cita la font; risc baix, però no s'ha comprovat).

### 3. Informe final (el genera l'script)

- Per format: quants llegits bé, quants amb mòduls que no quadren, quants sense PDF, quants sense
  ocupacions. Llista dels 30 pitjors casos per revisar a mà. Objectiu orientatiu: ≥ 90 % del format modern
  amb mòduls validats.

### 4. Backend i fitxa

- `app.py`: carregar `sepe_programes.json` (cache per mtime) i exposar-lo a
  `GET /api/sepe/especialitat/<codi>` (detall d'una especialitat: dades del catàleg + programa +
  ocupacions). El llistat `/api/sepe/especialitats` **no** s'engreixa.
- `index.html`: en desplegar una especialitat, demanar el detall i mostrar objectiu, mòduls amb hores,
  requisits d'accés, hores de tutoria presencial (si és teleformació), «Per a què serveix» (vinculacions)
  i ocupacions. Indicar «Text del programa oficial del SEPE (en castellà)». Si no hi ha contingut, només
  el botó del PDF, com ara.

### 5. Avís de manteniment al panell

- `admin.html`: un bloc «Programes del SEPE» amb la data de l'última descàrrega, quantes especialitats del
  catàleg actual no tenen programa llegit o han canviat de versió, i — si fa més de 4 mesos de l'última
  repassada completa o n'hi ha més de 100 de pendents — un avís amb **l'ordre exacta** a executar des de
  l'ordinador del propietari i el pas de copiar el fitxer al VPS (`scp` + cap reinici: es llegeix per mtime).

### 6. Documentació

- `fonts.html#sepe`: què s'extreu del programa i de les ocupacions, i que es repassa cada pocs mesos.

## Tests (sense xarxa)

- `parse_programa` amb el text de 4 programes desats com a fixtures (modern SSCE22, modern llarg, «PO»,
  antic): camps esperats i validació d'hores (un cas que no quadra).
- Parseig del modal d'ocupacions (amb i sense files).
- Script: represa, aturada als 5 errors, `--nomes-canvis` (tot amb el SEPE mockejat).
- Endpoint de detall: amb programa, sense programa, codi desconegut.

## Riscos (parlats amb el propietari)

1. Bloqueig del SEPE → ritme lent, aturada automàtica, IP del propietari i no del VPS.
2. Errors de lectura invisibles → validació d'hores i informe.
3. Contingut antic si el SEPE canvia un programa sense canviar la versió → repassada completa cada pocs
   mesos (avís del punt 5).
4. Canvi de plantilla del PDF → el lector retorna `None` i la fitxa mostra només el PDF.
5. Memòria: pdfplumber amb PDF de 37 pàgines; l'script és un procés a part, no dins de gunicorn.

## Fora d'abast

- Traduir el contingut al català. Guardar els PDF. Continguts per mòdul («Desarrollo modular»).
