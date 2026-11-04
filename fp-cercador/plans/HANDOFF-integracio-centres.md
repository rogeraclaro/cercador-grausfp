# Handoff — Integració GrausFP ↔ cercador de centres

Data: 2026-11-04

## Context

- GrausFP (`fp-cercador/`, Flask + HTML/JS vanilla + Alpine) i el cercador de centres (`fp-centres-cercador/`, repo germà, FastAPI + SQLite FTS5 + Jinja, en marxa a `centres.grausfp.es`).
- Decisió: **no fusionar codi** (stacks diferents; centres té ~182k parelles i filtra al servidor). Integració per enllaços creuats; es manté el subdomini.
- Decisió del propietari: el panell de centres de GrausFP és **obert a anònims**. Favorits, selecció de centres, seguiment de centres i alertes continuen requerint login.

## Fet en aquesta sessió (repo `Cercador Graus`, branca `master`, NO pujat ni desplegat)

Quick task GSD `261104-prj` (`.planning/quick/261104-prj-open-centres-panel-to-everyone-and-link-/`):

| Commit | Canvi |
|--------|-------|
| `5bed0b0` | `index.html`: panell de centres obert (fora límit de 3, gating de filtre CCAA/cerca i enllaç d'upsell). Graus C: enllaç a `https://centres.grausfp.es/{lang}/search?cert={row.ref}` + `&ccaa={slug}` si hi ha filtre CCAA (taula `CENTRES_APP_CCAA`, 19 CCAA, ESTATAL exclòs) |
| `02556fc` | Entrada "Centres"/"Centros" a la topbar d'`index.html`; tret "veure centres" dels beneficis del modal de registre (CA/ES, `index.html` i `itinerari.html`) |
| `2b1a745` | `grau_page.py`: tret "requereix compte" de la nota de centres de `/grau/<ref>` + test `test_centres_sense_compte` |
| `92ee124` | Docs de la quick task (PLAN, SUMMARY, STATE.md) |

Verificació: tests backend 413 OK (sense scrapers ni test_pipeline). `/api/centres*` ja eren públiques (el gating era només frontend). **No s'ha fet prova manual al navegador.**

## Pendent

1. **Prova manual al navegador** (anònim): panell de centres d'un grau C, filtre CCAA, enllaç al cercador de centres, entrada "Centres" a la topbar, CA i ES.
2. **Desplegar**: push a `cercador-grausfp/master` + `ssh contabo` git pull + **reiniciar backend** (per `grau_page.py`). No reiniciar diumenge 11:10–11:45 (refresc).
3. **Codi mort** (preguntar abans d'esborrar): clau i18n `index.centres.upsell` (CA/ES) i regla CSS `.centres-separator` a `index.html`.
4. **Seguretat**: passar `centre.url_web` per `safeHttpUrl()` al panell de centres (ara molts més visitants veuen aquests enllaços).
5. **Topbar a les altres pàgines**: afegir l'entrada "Centres" a la resta de pàgines amb la barra de `site.css` (bump `?v=` si es toca `site.css`).
6. **Repo `fp-centres-cercador`** (sessió/GSD propis allà):
   - Enllaç "← GrausFP" a la capçalera de `app/templates/base.html` i al peu.
   - Alinear tokens visuals amb `site.css` de GrausFP (copiar, no compartir fitxer).
   - Encara té pendent el tancament de la fase 04.1 (code review, regressió, verifier, push de commits locals) i la Fase 5 (llançament, treure noindex).
7. **Manteniment**: `CENTRES_APP_CCAA` depèn de `app/importer/normalise/geo.py` del repo germà; actualitzar-la si canvien els slugs.
