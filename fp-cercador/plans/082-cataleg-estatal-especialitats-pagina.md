# Pla 082 — Pàgina "Catàleg estatal d'especialitats formatives" (SEPE)

Origen: sessió 2026-11-08. El propietari vol el catàleg estatal **a part**, sense barrejar-lo amb
els Grados A–E ni amb el mode FPO, que mostra cursos concrets.
Depèn de: **081 fases 1–2** (`backend/data/sepe_especs.json`). Llegir la secció "Marc conceptual" i
"Diagnosi tècnica" del pla 081: no es repeteixen aquí.
Executable per un agent sense context.

## Canvi de decisió (2026-11-26) — DONE, no desplegat

El propietari vol que **tots els codis surtin al cercador principal**, no en una pàgina a part. D1 queda
substituïda; la resta de l'API (fase 1) es manté tal com s'havia previst.

Fet:
- `GET /api/sepe/especialitats` (format compacte + `families`/`arees` + `actualitzat`) i
  `GET /api/sepe/programa/<codi>` (proxy amb cache en disc a `backend/data/sepe_programes/`, 30 dies; marcador
  `.nopdf` 7 dies; 10 descàrregues no cachejades per IP i minut; 502 si el SEPE falla, amb PDF caducat si n'hi ha).
  `sepe_scraper.fetch_programa_pdf()` fa el POST JSF. Tests: `backend/tests/test_sepe_api.py`.
- `api_fpo_especialitat`: `programaSepeUrl` quan el SOC no dona `programaUrl` (botó al panell FPO).
- `index.html`, mode per nom: pestanya «Especialitats SEPE» (`?grado=SEPE`, paginada a 50) i bloc
  «També al catàleg estatal del SEPE (N)» sota els graus quan hi ha ≥2 caràcters de cerca (10 primers +
  «Veure les N especialitats»). Càrrega mandrosa del JSON (~1,8 MB sense gzip). Filtres de família (nom
  normalitzat + àlies) i nivell; sense favorits, alertes ni centres. Enllaç «Veure els cursos a Catalunya»
  → `?mode=fpo&esp=<codi>` (paràmetre que ja existia).
- Documentació: `per-que-grausfp.html#sepe` (+ FAQ 7) i `docs/per-que-grausfp.md`; `fonts.html#sepe` amb
  la font i la freqüència d'actualització.

Pendent de parlar amb el propietari: com diferenciar visualment les especialitats SEPE dels graus (ara: etiqueta
«Especialitat SEPE» + bloc separat). Al VPS cal que `backend/data/sepe_programes/` sigui escrivible per
l'usuari del site (el codi el crea si pot).

## Decisions (preses a la sessió; el propietari les pot revisar)

| # | Decisió |
|---|---|
| D1 | Pàgina pròpia `frontend/cataleg-especialitats.html`, enllaçada des del footer (`footer.js`) i des del mode FPO ("Veure tot el catàleg estatal"). No és un mode d'`index.html`. |
| D2 | Text introductori curt i clar: és **formació en el treball** (Llei 3/2023 i RD 438/2024), **no** condueix a cap Grado A–E ni a cap certificat oficial, i l'imparteixen entitats acreditades a tot l'Estat. |
| D3 | 7.544 registres: superen el límit de rendiment de 1.500 sense paginació (CLAUDE.md). Es farà **paginació al client** (50 per pàgina) sobre el JSON complet, amb filtratge al client. |
| D4 | Si l'especialitat té cursos FPO actius a Catalunya (codi a `_soc_espec_index()`), es mostra l'enllaç "N cursos a Catalunya" → `index.html` en mode FPO filtrat per codi. Això és el pont amb el pla 081. |
| D5 | Programa formatiu: proxy backend amb cache en disc, perquè el PDF del SEPE només s'obté amb un POST JSF amb sessió i no es pot enllaçar directament. |
| D6 | v1 **sense** favorits, alertes ni entitats de formació. |
| D7 | Títols en castellà (la font no té català). Si el SOC té `titol.ca` per al mateix codi, en CA es mostra aquest. |

## Fase 1 — API

A `backend/app.py`:
- `GET /api/sepe/especialitats` → `{especialitats: [...], actualitzat: <mtime ISO>, warning?}`.
  Cada element ha de ser compacte per reduir pes (7.544 × ~200 B ≈ 1,5 MB; amb gzip de nginx, ~200 KB):
  `{c: codi, t: titol_es, tca: titol_ca|null, f: familia_codi, a: area_codi, n: nivell|null,
  m: modalitat, h: hores, ct: competenciaTransversal|null, vf: vigenciaFi, nc: nCursosCat}`.
  El diccionari de famílies i àrees (codi → desc) es retorna a part, a `families`.
  Cache per mtime de `sepe_especs.json` i dels SOC.
- `GET /api/sepe/programa/<codi>` → PDF:
  - El codi s'ha de validar contra l'índex SEPE (404 si no hi és). **No s'accepta cap id lliure** de l'usuari:
    l'`idSepe` surt de l'índex.
  - Cache en disc a `backend/data/sepe_programes/<codi>.pdf`, amb TTL de 30 dies. Escriptura atòmica.
  - Si no hi és, la descàrrega segueix la diagnosi del pla 081: GET `flows/main` + POST multipart amb
    `formulario:codigoPropuesta=<idSepe>`. Si el `Content-type` no és PDF → 404 amb `{error:
    'sense_programa'}`, i es desa un marcador negatiu de 7 dies per no tornar a picar al SEPE.
  - Rate limit per IP: reaprofitar el patró de `_auth_rate_ok` (≈ línia 2436) amb un bucket propi, p. ex.
    10 descàrregues no cachejades/minut. Respondre amb `Content-Disposition: inline; filename=<codi>.pdf`.
  - Afegir `sepe_programes/` al `.gitignore`.
- Tests (`backend/tests/test_sepe_api.py`): el llistat i el seu format compacte; `nc` creuat amb un fixture SOC;
  el programa amb cache encertada i el SEPE mockejat; el codi desconegut (404); la resposta no-PDF (404 + marcador);
  i que el rate limit s'apliqui.

## Fase 2 — Pàgina `frontend/cataleg-especialitats.html`

- Mateixa estructura que `observatori.html`: `site.css` + barra superior comuna, `i18n.js`, Alpine
  vendoritzat i `footer.js`. GSAP és opcional; si s'usa, ha d'anar darrere de `gsap.matchMedia()`.
- Capçalera + bloc explicatiu (D2), amb enllaços a les fonts oficials (BOE RD 438/2024, cercador SEPE).
- Filtres al client: text (codi o títol, sense accents), família → àrea (selects dependents, com a FPO),
  nivell (1–5 / sense especificar), modalitat, competència transversal, "només amb cursos a Catalunya".
- Resultats: llista paginada (D3) amb codi, títol, família, nivell, hores, modalitat, xip de
  competència transversal i enllaç de cursos a Catalunya (D4).
- Desplegable per especialitat: vigència, versió, botó "Programa formatiu (PDF)" →
  `/api/sepe/programa/<codi>` (nova pestanya) i enllaç "Veure al cercador del SEPE" (URL base del
  cercador, perquè no té enllaç profund per especialitat).
- Estat del filtre a la URL (`?q=&f=&a=…`) per poder compartir-lo.
- i18n: claus `cataleg.*` en CA i ES. Sense literals dins `x-text`.
- Afegir l'enllaç a `footer.js` i, al mode FPO d'`index.html`, l'enllaç "Veure tot el catàleg estatal".
- SEO: `<title>`, `meta description` i que la pàgina s'incorpori al sitemap (veure el pla 077).

## Fase 3 — Pont amb l'FPO

- `index.html`: acceptar `?mode=fpo&espec=<codi>` (si encara no existeix) per obrir l'FPO amb el text
  de cerca = codi i el panell desplegat. Comprovar primer si ja hi ha un paràmetre equivalent i reaprofitar-lo.
- Si el pla 081 fase 3 ja és fet: afegir `programaSepeUrl` a `api_fpo_especialitat` i mostrar el botó
  al panell FPO quan `programaUrl` (Conforcat) sigui buit.

## Fora d'abast

- Entitats de formació per especialitat: és un flux JSF amb estat; caldria un pla propi.
- Extreure camps del PDF del programa (objectiu, requisits d'accés, mòduls). És viable, perquè el text és
  numerat, però queda per a més endavant.
- Versions antigues de les especialitats (`ultimaVersionCuadrado=false`).

## Verificació

- `pytest backend/tests -k sepe` en verd.
- Al navegador (local): càrrega inicial < 1 s amb 7.544 registres; els filtres responen sense lag;
  el PDF d'`ADGA12DCP` s'obre i el segon cop surt de la cache; un codi amb cursos SOC porta a
  l'FPO filtrat.
- a11y: focus visible, labels als filtres, paginació navegable amb el teclat.
- Deploy: el bloc nginx no ha de canviar, perquè és una pàgina estàtica més. Crear `backend/data/sepe_programes/`
  al VPS amb els permisos de l'usuari del site.
