# Phase 5: Frontend — Cercador - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 05-frontend-cercador
**Areas discussed:** Tech Stack, Paginació, Layout Visual, URL API, Càrrega/Errors, Columnes, Pla Antic

---

## Tech Stack

| Option | Description | Selected |
|--------|-------------|----------|
| Vanilla JS | Zero deps, compatible amb restricció original | |
| Alpine.js via CDN | Reactiu, ~15kb, sense build step | ✓ |

**User's choice:** Alpine.js permès. L'usuari va aclarir que la restricció de "zero dependències" és flexible si millora el rendiment.
**Notes:** La restricció original al PROJECT.md era "requisit explícit del propietari" però l'usuari (el propietari) la va modificar explícitament.

---

## Paginació

| Option | Description | Selected |
|--------|-------------|----------|
| Pàgines clàssiques | Botons 1, 2, 3... 50 files/pàgina | ✓ |
| Infinite scroll | Files s'afegeixen en fer scroll | |
| "Mostra més" manual | Botó al final per carregar bloc | |

**User's choice:** Pàgines clàssiques, 50 resultats per pàgina.
**Notes:** La restricció original SRCH-09 deia "sense paginació". Revisada explícitament per l'usuari.

---

## Layout Visual

| Option | Description | Selected |
|--------|-------------|----------|
| Funcional i net | Fons blanc, tipografia sistema, colors mínims | ✓ |
| Amb capçalera de marca | Header amb color corporatiu | |

**User's choice:** Funcional i net.

---

## URL de l'API

| Option | Description | Selected |
|--------|-------------|----------|
| Variable JS al fitxer | `const API_BASE = 'http://localhost:5000'` | ✓ |
| Mateixa origen (relatiu) | Crides relatives `/api/ofertes` | |

**User's choice:** Variable JS configurable.

---

## Estats de Càrrega

| Option | Description | Selected |
|--------|-------------|----------|
| Spinner + missatge | "Carregant dades del catàleg FP..." | ✓ |
| Taula buida fins que carrega | Sense indicació visual | |
| Missatge discret | Text pla sense animació | |

**User's choice:** Spinner + missatge.

---

## Error 503

| Option | Description | Selected |
|--------|-------------|----------|
| Missatge clar amb acció | "⚠️ Les dades no estan disponibles. Contacteu l'administrador." | ✓ |
| Missatge tècnic | "Error 503: ofertes.json no trobat" | |
| Taula buida | Sense diferenciar error de cerca buida | |

**User's choice:** Missatge clar per a l'usuari final.

---

## Columnes de la Taula

| Option | Description | Selected |
|--------|-------------|----------|
| Essencials ordenades | Denominació \| Codi \| Família \| Grado \| Nivell | ✓ |
| Inclou Observaciones | Afegeix columna Observaciones | |

**User's choice:** Essencials ordenades. Observaciones descartada per llegibilitat.

---

## Badge Pla Antic

| Option | Description | Selected |
|--------|-------------|----------|
| Badge a la columna Denominació | Al costat del nom, dins la cel·la | ✓ |
| Columna separada | Columna "Estat" dedicada | |
| Color de fila | Fila en gris/cursiva | |

**User's choice:** Badge inline a la cel·la Denominació.

---

## Claude's Discretion

- Debounce exacte per a la cerca de text
- Nombre de botons de pàgina visibles
- Colors del badge "Pla antic"
- Estil del spinner

## Deferred Ideas

- Filtres a la URL (query params)
- Botó reset de filtres
- Exportació CSV (V2)
