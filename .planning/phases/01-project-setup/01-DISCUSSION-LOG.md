# Phase 1: Project Setup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 01-project-setup
**Areas discussed:** Ubicació arrel del projecte, Completesa de l'esquelet, Documentació del token, ofertes.json al .gitignore

---

## Ubicació arrel del projecte

| Option | Description | Selected |
|--------|-------------|----------|
| Dins del dir actual | fp-cercador/ dins de Cercador Graus/ — tot auto-contingut | ✓ |
| Directament a l'arrel | backend/ i frontend/ a l'arrel del repo, sense fp-cercador/ | |

**User's choice:** Dins del dir actual
**Notes:** backend/ amb subcarpetes scrapers/ i data/

---

## Completesa de l'esquelet

| Option | Description | Selected |
|--------|-------------|----------|
| Stub mínim (app.py) | Flask + CORS + load_dotenv, sense rutes | ✓ |
| Amb rutes placeholder | 4 endpoints com stubs que retornen 501 | |
| HTML buits estructurats | DOCTYPE, head, body buits vàlids | ✓ |
| Fitxers completament buits | 0 bytes | |

**User's choice:** Stub mínim per app.py + HTML estructurats per frontend
**Notes:** Cap ruta a app.py en aquesta fase

---

## Documentació del token

| Option | Description | Selected |
|--------|-------------|----------|
| .env.example + README | Ambdós fitxers | ✓ |
| Només .env.example | Sense README | |
| README mínim | Nom, descripció breu, passos de setup | ✓ |
| README + context tècnic | Arquitectura, scrapers, desplegament | |

**User's choice:** .env.example + README mínim (setup i configuració)
**Notes:** README sense seccions de docs extenses

---

## ofertes.json al .gitignore

| Option | Description | Selected |
|--------|-------------|----------|
| Excloure del repo | ofertes.json generada en runtime | |
| Incloure al repo | ofertes.json commitat com a referència | ✓ |
| Array buit [] | Fitxer vàlid però buit | |
| Mostra amb registres | 5-10 registres representatius dels 5 Grados | ✓ |

**User's choice:** Incloure al repo amb registres de mostra (~5-10 que cobreixen els 5 Grados)
**Notes:** Facilita el desenvolupament del frontend sense executar el scraping

---

## Claude's Discretion

- Estructura exacta del .gitignore
- Contingut concret dels registres de mostra a ofertes.json
- Títol exacte del README

## Deferred Ideas

Cap idea deferred — la discussió es va mantenir dins de l'abast de la fase.
