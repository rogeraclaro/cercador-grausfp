# Phase 5: Frontend — Cercador - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Pàgina HTML estàtica amb filtratge en temps real de 12.374 registres FP. Cobreix cerca per text, dropdowns (Grado, Família, Nivell), checkbox "Ocultar pla antic", taula de resultats paginada i estats de càrrega/error. No inclou el panell admin (Fase 6).

</domain>

<decisions>
## Implementation Decisions

### Tech Stack

- **D-01:** Alpine.js via CDN permès. La restricció original de "zero dependències" és flexible si millora el rendiment o la mantenibilitat del codi.
- **D-02:** Paginació clàssica habilitada. La restricció original de "scroll sense paginació" s'ha revisat. 50 resultats per pàgina (configurable), botons Anterior / 1 2 3 ... N / Següent.

### Rendiment

- **D-03:** Estratègia de DOM: fetch únic al cargar la pàgina → array JS en memòria → filtratge en memòria → renderitzar només les files de la pàgina activa. Mai renderitzar els 12.374 registres al DOM simultàniament.
- **D-04:** Alpine.js és l'opció recomanada per gestionar la reactivitat dels filtres i la paginació amb codi net.

### Layout Visual

- **D-05:** Disseny funcional i net. Fons blanc/gris clar, tipografia del sistema, colors mínims. Sense capçalera de marca elaborada.
- **D-06:** Estructura de la pàgina:
  1. Títol "Cercador FP Espanya"
  2. Barra de cerca + dropdowns (Grado, Família, Nivell) en una fila
  3. Checkbox "Ocultar pla antic" + comptador de resultats
  4. Taula de resultats
  5. Controls de paginació

### Taula de Resultats

- **D-07:** Columnes en aquest ordre: Denominació | Codi | Família | Grado | Nivell. Observaciones NO es mostra a la taula.
- **D-08:** Badge "Pla antic" dins la cel·la Denominació, al costat del nom. No columna separada ni color de fila.

### Configuració API

- **D-09:** URL de l'API via constant JS al principi del fitxer: `const API_BASE = 'http://localhost:5000'`. Fàcil de canviar per a producció sense tocar la lògica.

### Estats de Càrrega i Errors

- **D-10:** Mentre es carreguen les dades: spinner CSS + text "Carregant dades del catàleg FP...".
- **D-11:** Si `/api/ofertes` retorna 503: missatge "⚠️ Les dades del catàleg no estan disponibles. Contacteu l'administrador del sistema." Sense botó de reintent.
- **D-12:** Estat buit (cap resultat coincideix amb els filtres): missatge discret dins la taula, diferenciat de l'error 503.

### Claude's Discretion

- Debounce exacte per a la cerca de text (recomanat: 200-300ms).
- Nombre de botons de pàgina visibles (recomanat: 5-7, amb el·lipsis).
- Colors exactes del badge "Pla antic" (recomanat: gris fosc o taronja suau).
- Estil exacte del spinner de càrrega.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements d'aquesta fase
- `SRCH-01` a `SRCH-10` a `.planning/REQUIREMENTS.md` — tots els requisits del cercador (nota: SRCH-09 "sense paginació" ha estat revisat per D-02)

### Fitxers existents
- `fp-cercador/frontend/index.html` — stub buit, és el fitxer a implementar
- `fp-cercador/frontend/admin.html` — stub per a Fase 6, NO tocar
- `fp-cercador/backend/app.py` — API Flask; endpoint rellevant: `GET /api/ofertes`

### Esquema de dades
- `.planning/REQUIREMENTS.md` §Generació de Dades — schema complet: `id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones`
- Volum real: 12.374 registres (A: 8.537, B: 2.786, C: 820, D: 195, E: 36)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `fp-cercador/frontend/index.html` — stub buit, implementació completa aquí
- `fp-cercador/backend/app.py` — Flask API ja operativa amb CORS habilitat

### Established Patterns

- API retorna JSON array directe des de `GET /api/ofertes` (no wrapping object)
- CORS habilitat per a totes les origins (flask-cors)
- `plan_antiguo` és booleà a l'esquema JSON

### Integration Points

- `index.html` carrega dades via `fetch(API_BASE + '/api/ofertes')` al DOMContentLoaded
- El frontend és estàtic; Flask serveix l'API a port 5000; en producció el frontend pot ser servit per nginx/CloudPanel

</code_context>

<specifics>
## Specific Ideas

- Layout mockup confirmat per l'usuari:
  ```
  +-----------------------------------------+
  | Cercador FP Espanya                     |
  +-----------------------------------------+
  | [Cerca...] [Grado v] [Família v] [Niv v]|
  | [ ] Ocultar pla antic    12.374 result. |
  +-----------------------------------------+
  | Denominació          | Codi  | Família | G | N |
  |----------------------|-------|---------|---|---|
  | Cuina i gastronomia  | HOT.. | ...     | B | 2 |
  | Titu·lació [Pla antic]| ...  | ...     | A | 1 |
  ```
- Paginació: `[ Anterior ]  1  2  3 ... 47  [ Següent ]`, 50 resultats per pàgina

</specifics>

<deferred>
## Deferred Ideas

- Sincronitzar filtres a la URL (query params) — útil per compartir cerques, però és una nova capacitat (Fase futura)
- Botó de reset de tots els filtres — no discutit, Claude pot decidir incloure'l
- Exportació a CSV — V2-02 als requirements, fora d'abast
- Columna Observaciones — descartada en aquesta fase per llegibilitat

</deferred>

---

*Phase: 05-frontend-cercador*
*Context gathered: 2026-04-19*
