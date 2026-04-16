# Phase 1: Project Setup - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Crear l'esquelet complet del projecte `fp-cercador/` amb l'estructura de directoris, dependències Python, fitxers de configuració i dades de mostra. El resultat ha de ser un repositori que qualsevol desenvolupador pugui clonar, instal·lar i executar sense configuració addicional (excepte definir `ADMIN_TOKEN`).

</domain>

<decisions>
## Implementation Decisions

### Estructura de Directoris

- **D-01:** La carpeta arrel `fp-cercador/` es crea dins del directori actual (`Cercador Graus/`), no a cap altra ubicació. Estructura final: `Cercador Graus/fp-cercador/backend/` + `Cercador Graus/fp-cercador/frontend/`
- **D-02:** `backend/` té les subcarpetes `scrapers/` i `data/`, a més de `app.py`, `requirements.txt` i `.env.example` directament
- **D-03:** `frontend/` conté `index.html` i `admin.html`

### Completesa de l'Esquelet Flask

- **D-04:** `app.py` és un stub mínim: importa Flask, flask_cors i dotenv; crea l'app amb `CORS(app)`; inclou `if __name__ == '__main__': app.run(debug=True)`. **Sense cap ruta** — les rutes es fan a la Fase 4
- **D-05:** `index.html` i `admin.html` a `frontend/` són HTML vàlids estructurats (DOCTYPE, `<html lang="ca">`, `<head>` amb charset i title, `<body>` buit amb comentari `<!-- TODO: Phase 5/6 -->`). No són fitxers buits de 0 bytes

### Documentació del Token

- **D-06:** S'inclouen **ambdós**: `.env.example` (dins `backend/`) i `README.md` (a l'arrel de `fp-cercador/`)
- **D-07:** `.env.example` conté: `ADMIN_TOKEN=canvia-aquest-token-per-un-de-segur`
- **D-08:** `README.md` és mínim: nom del projecte, descripció breu, i pasos de setup (cp .env.example .env → editar ADMIN_TOKEN → pip install → python app.py). Sense seccions de docs extenses

### ofertes.json i .gitignore

- **D-09:** `backend/data/ofertes.json` **s'inclou al repositori** (NO s'exclou del .gitignore). Conté un conjunt petit de registres de mostra representatius (~5-10 registres) per facilitar el desenvolupament del frontend sense necessitat d'executar el scraping
- **D-10:** `.gitignore` exclou: `.env`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `.Python`, `venv/`, `.venv/`, `*.egg-info/`

### Claude's Discretion

- Estructura exacta del `.gitignore` (les entrades concretes per Python/venv)
- Contingut exacte dels registres de mostra a `ofertes.json` (5-10 registres representatius dels 5 Grados)
- Títol exacte del README

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Requirements rellevants
- PROJ-01: estructura `fp-cercador/backend/` i `fp-cercador/frontend/` amb tots els fitxers necessaris
- PROJ-02: `.gitignore` exclou `.env`, cache Python (ofertes.json NO s'exclou — D-09)
- PROJ-03: `requirements.txt` conté: flask, flask-cors, pdfplumber, requests, beautifulsoup4, python-dotenv

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

Cap codi existent — projecte de zero.

### Established Patterns

Cap patró establert — primera fase.

### Integration Points

- `fp-cercador/backend/app.py` serà el punt d'entrada que les fases posteriors (Fase 4) completaran amb rutes
- `fp-cercador/backend/data/ofertes.json` serà llegit per l'API (Fase 4) i sobreescrit pel pipeline de scraping (Fases 2-3)
- `fp-cercador/frontend/index.html` i `admin.html` seran completats a les Fases 5 i 6

</code_context>

<specifics>
## Specific Ideas

- `app.py` stub ha de carregar dotenv explícitament (`load_dotenv()`) perquè les fases posteriors puguin accedir a `ADMIN_TOKEN` via `os.getenv()`
- Els registres de mostra a `ofertes.json` han de cobrir els 5 Grados (A, B, C, D, E) per permetre provar tots els filtres del frontend

</specifics>

<deferred>
## Deferred Ideas

Cap — la discussió es va mantenir dins de l'abast de la fase.

</deferred>

---

*Phase: 01-project-setup*
*Context gathered: 2026-04-16*
