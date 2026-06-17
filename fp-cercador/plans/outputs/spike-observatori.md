# Spike Observatori: document de disseny

> **Estat**: document de disseny — NO codi de producció  
> **Autor**: spike pla 018  
> **Data**: 2026-06-17

---

## 1. Persistència de la sèrie temporal

### El problema

`HISTORY_MAX = 20` a `history.py` trunca l'historial a 20 entrades. Amb refreshos setmanals, 20 entrades cobreixen **~5 mesos**. Per a un observatori visual útil (tendències anuals, comparatives de curs) cal persistència indefinida. La sèrie temporal és la dada central del producte.

### Decisió: taula SQLite `observatory_snapshots` al `fp_cercador.db` existent

**Justificació de triar SQLite sobre `observatory.json`:**

| Criteri | SQLite | JSON |
|---|---|---|
| Estructura | Tipat, indexable, consultable | Array creixent, tot carrega a memòria |
| Creixement | Constant (1 fila/setmana) | Fitxer creix linealment (no truncable sense lògica) |
| Consultes | `WHERE ts > ?`, agregats, ORDER BY | Iteració manual en Python/JS |
| Coherència | Transaccional amb les taules d'alertes/usuaris | Fitxer separat, sense transaccions |
| Infraestructura | `fp_cercador.db` ja existeix, `db.py` ja gestiona migracions | Fitxer nou, lògica nova |
| Mida a 10 anys | ~520 files × ~200 bytes = ~100 KB | Equivalent, però difícil de consultar |

El projecte ja té SQLite amb `fp_cercador.db`, migracions via `migrations/*.sql`, i `db.py` com a capa d'accés. Afegir una taula nova és el camí natural.

### Esquema de la taula

```sql
-- Migration 002: taula de l'Observatori FP
CREATE TABLE IF NOT EXISTS observatory_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,           -- ISO 8601 UTC, e.g. "2026-06-17T03:00:00+00:00"
    total           INTEGER NOT NULL,
    total_a         INTEGER NOT NULL DEFAULT 0,
    total_b         INTEGER NOT NULL DEFAULT 0,
    total_c         INTEGER NOT NULL DEFAULT 0,
    total_d         INTEGER NOT NULL DEFAULT 0,
    total_e         INTEGER NOT NULL DEFAULT 0,
    n_altes         INTEGER NOT NULL DEFAULT 0, -- total new_denominacions del refresh
    n_baixes        INTEGER NOT NULL DEFAULT 0, -- total removed_denominacions
    families_amb_altes TEXT,                   -- JSON array: llista de famílies amb altes
    source          TEXT    NOT NULL DEFAULT 'refresh'
);
CREATE INDEX IF NOT EXISTS idx_observatory_ts ON observatory_snapshots(ts);
INSERT INTO schema_version (version) VALUES (2);
```

**Camps derivats dels existents:**

| Camp taula | Font a `history.py` |
|---|---|
| `ts` | `entry["ts"]` |
| `total` | `result.get("total")` |
| `total_a/b/c/d/e` | `result.get("by_grado", {}).get("A/B/C/D/E")` |
| `n_altes` | `len(changes["new_denominacions"])` |
| `n_baixes` | `len(changes["removed_denominacions"])` |
| `families_amb_altes` | `json.dumps(sorted(set(changes["new_by_grado"].keys())))` |

### On enganxar: `history.append()`

A `history.py`, funció `append()`, **just després** de `_write_atomic(full, SNAPSHOT_PATH)`:

```python
# Persistència a l'Observatori (taula SQLite, no truncada)
try:
    from db import get_db
    _persist_observatory(entry, result.get("changes") or {})
except Exception as exc:
    logger.warning("observatory_persist failed: %s", exc)
```

Funció auxiliar `_persist_observatory(entry, changes)` al mateix fitxer, que fa l'INSERT a `observatory_snapshots`. L'error és no-fatal: si el SQLite falla, l'historial JSON continua funcionant.

### Migració des de l'historial existent

En el primer deploy del pla 030, executar un script one-shot de migració:

```python
# scripts/migrate_history_to_observatory.py
# Llegeix refresh_history.json i insereix files a observatory_snapshots
# Idempotent: comprovació per ts UNIQUE
```

Les **10 entrades actuals** a producció es poden migrar. Com que `n_altes`/`n_baixes` ja estan als `changes` de l'historial JSON, la migració és completa.

---

## 2. Visualitzacions proposades

Totes les visualitzacions citen exactament els camps que les alimenten. "Possible AVUI" = amb les dades actuals (10 entrades, ~1 mes de cobertura real). "Millora amb sèrie llarga" = valor addicional quan hi hagi ≥52 setmanes.

| # | Nom | Camps que l'alimenten | Possible AVUI? | Millora amb sèrie llarga |
|---|---|---|---|---|
| V1 | **Evolució total titulacions** (línia) | `observatory_snapshots.ts`, `total` | Sí, amb 10 punts | Tendència anual clara, canvis de curs visibles |
| V2 | **Evolució per grado** (línies múltiples A/B/C/D/E) | `ts`, `total_a`, `total_b`, `total_c`, `total_d`, `total_e` | Sí, amb 10 punts | Quins grados creixen vs estabilitzen |
| V3 | **Distribució actual per grado** (barres horitzontals o donut) | Última fila: `total_a/b/c/d/e` | Sí (1 snapshot) | No millora — és una foto del moment present |
| V4 | **Altes acumulades per setmana** (barres verticals) | `ts`, `n_altes` | Sí, però pocs pics | Estacionalitat: quins mesos publica el ministeri |
| V5 | **Famílies professionals més actives** (barres, top-10) | `last_snapshot.json → families`, `changes.new_by_grado` | Parcial — cal agregar l'historial | Ranking anual de famílies que publiquen més |
| V6 | **Últimes novetats** (llista, no gràfic) | `changes.new_denominacions`, `changes.new_by_grado` | Sí, immediatament | Més historial = llista més llarga navigable |

**Visualitzacions recomanades per al primer increment (pla 031):** V1 + V3 + V6. Tres panells, dades disponibles AVUI, render ràpid, prou contingut per a SEO.

V2 i V4 s'afegeixen en el segon increment (pla 032) quan l'observatori ja tingui ≥4 setmanes de dades pròpies. V5 requereix una consulta d'agregació més elaborada i es pot deixar per a una tercera iteració.

**Limitació honesta**: amb 10 entrades actuals —i moltes d'elles proves del mateix dia— les línies de tendència tindran molt pocs punts. La pàgina ha de comunicar-ho ("dades des de X, actualitzades cada setmana") sense fingir una sèrie que no existeix.

---

## 3. Decisió de gràfics

### Avaluació de les 3 opcions

#### Opció A: SVG generat a mà en JS vanilla

**Trade-offs:**
- Zero dependències noves. 100% coherent amb la constraint del projecte.
- Codi: ~100-200 línies per gràfic (escala, eixes, tooltips).
- Tooltips i interactivitat requereixen gestió manual d'events de ratolí.
- No reutilitzable fàcilment per a nous gràfics futurs.
- Adequat per a: gràfics senzills (línies simples, barres estàtiques) sense interactivitat complexa.

#### Opció B: Microllibreria vendoritzada

Candidates concretes avaluades:

| Candidata | Mida (minified+gzipped) | Llicència | Gràfics suportats | Notes |
|---|---|---|---|---|
| **Chart.js 4.x** | ~65 KB | MIT | Línies, barres, donut, radar | Molt completa, però força gran per a 2-3 gràfics |
| **uPlot** | ~15 KB | MIT | Línies, àrea, barres bàsiques | Ultra lleugera, molt ràpida, API de baix nivell |
| **Frappe Charts** | ~60 KB | MIT | Línies, barres, donut, heatmap | Bona API, disseny net, però menys mantinguda |
| **ECharts (core only)** | ~45-80 KB | Apache 2.0 | Tot, molt configurable | Potent però API complexa |

**Candidata recomanada si s'escull opció B: uPlot** per a gràfics de sèries temporals (V1, V2, V4), **+ SVG a mà** per a la distribució actual (V3, gràfic de barres simples). Mida total: ~15 KB vendoritzat + ~50 línies SVG manual.

Alternativa acceptable: **Chart.js 4.x** si es prioritza simplicitat d'integració sobre mida. S'hauria de vendoritzar a `frontend/vendor/chart.min.js` i `chart.min.js.map`.

#### Opció C: SVG/PNG generat al backend en el refresh

**Trade-offs:**
- Zero JS al frontend per als gràfics. Fitxers estàtics, cachejables (CDN-friendly).
- Requereix `matplotlib` o `svgwrite` com a nova dependència Python.
- Generació síncrona durant el refresh (afegeix latència) o en un job separat.
- Gràfics estàtics: sense tooltips ni zoom. Menys informatius per a l'usuari.
- Ideal per a Open Graph images i pre-renders per a crawlers.

### Recomanació final

**Opció B (uPlot vendoritzat) + SVG a mà per a distribucions simples.**

Justificació:
1. **Coherència amb la constraint**: vendoritzat a `frontend/vendor/`, sense CDN. El precedent és Alpine.js 3.x, ja vendoritzat.
2. **Mida justificada**: uPlot a ~15 KB és proporcional a l'ús (gràfics de sèries temporals). Chart.js a 65 KB seria desproporcionat per a 2-3 gràfics.
3. **Mantenibilitat**: l'API d'uPlot és més propera a "configuració declarativa" que a "codi imperatiu", reduint el codi de col·la.
4. **Fallback**: V3 (distribució per grado) és tan simple que un SVG generat a mà (5 barres amb percentatge) és millor que carregar una llibreria per això.

**Llicència**: uPlot és MIT. Compatibble amb el projecte.

**Si el revisor prefereix zero dependències noves**: Opció A és viable per a 3 gràfics senzills. Cost estimat: +250-350 línies JS vs. +15 KB de binari vendoritzat. La decisió final és del revisor.

---

## 4. Pàgina i SEO

### Estructura de la pàgina

`frontend/observatori.html` — seguint el patró d'`historial.html`:

1. **Topbar** (idèntic a totes les pàgines)
2. **Hero**: h1 en DM Serif Display + subtítol orientat a SEO
3. **Stats hero** (3-4 números grans estàtics): "X titulacions actives", "Y grados", "última actualització: data"  
   → Renderitzats server-side o al JS al primer paint — **crítics per a crawlers**
4. **Panell V1**: Evolució del total (línia)
5. **Panell V3**: Distribució per grado (barres o donut)
6. **Panell V6**: Últimes novetats (llista amb links al cercador filtrat)
7. **Footer**: nota metodològica, font de les dades (Ministerio de Educación, todofp.es)

### Meta tags recomanats

```html
<title>Observatori de l'oferta FP espanyola — Cercador Graus FP</title>
<meta name="description" content="Evolució setmanal de les titulacions de Formació Professional a Espanya (Grados A–E). Estadístiques actualitzades automàticament cada setmana des del Ministerio de Educación.">

<!-- Open Graph -->
<meta property="og:title" content="Observatori FP: X.XXX titulacions actives">
<meta property="og:description" content="Evolució de l'oferta FP espanyola des de YYYY. Grados A–E, famílies professionals, novetats setmanals.">
<meta property="og:type" content="website">
```

### Keywords objectiu (long-tail)

- "cuántas titulaciones FP hay en España"
- "evolución oferta formación profesional"
- "estadísticas FP España 2024 2025"
- "familias profesionales más titulaciones"
- "novedades FP España"
- "titulaciones FP nuevas"

### Estratègia per a crawlers (limitació important)

**Problema**: tot el frontend actual és client-side (fetch + render JS). Els crawlers de Google, Bing i Googlebot han millorat molt en indexar JS, però els valors numèrics clau (total titulacions, distribució per grado) no apareixen al HTML inicial.

**Solució recomanada**: pre-renderitzar els **números clau** al HTML via un endpoint nou `/api/observatory-summary` que retorni un fragment HTML mínim, o bé incloure'ls com a atributs `data-` llegibles per crawlers. 

Alternativa simple i suficient: **afegir un `<noscript>` block** amb els números en text pla — Googlebot l'indexa i el cost de manteniment és baix.

Alternativa completa: afegir Flask-Jinja template per a `observatori.html` que serveixi el HTML pre-renderitzat. Millor per a SEO, però requereix canviar l'arquitectura (frontend deixaria de ser 100% estàtic). **Fora d'escope del primer increment; decidir en fase de SEO avançat (F8 del roadmap).**

**Recomanació pràctica**: primer increment amb JS pur + `<noscript>` per als numbers crítics. Suficient per a indexació. Millora incremental possible sense bloquejar el lliurament.

---

## 5. Pla de construcció

### Plans seqüenciats

| Pla | Títol | Fitxers afectats | Estimació | Dependències |
|---|---|---|---|---|
| **030** | Migració 002 SQLite + persistència observatory | `migrations/002_observatory.sql`, `history.py`, `scripts/migrate_history_to_observatory.py` | 3-4h | Cap (no bloqueja res) |
| **031** | Endpoint `/api/observatory` (dades agregades per a gràfics) | `app.py` (+1 endpoint públic), `db.py` (query helper) | 2-3h | Pla 030 |
| **032** | Pàgina `observatori.html` — primer increment (V1 + V3 + V6) | `frontend/observatori.html`, `frontend/vendor/uplot.min.js` (o SVG manual) | 4-6h | Pla 031 |
| **033** | Gràfics addicionals (V2 + V4) + SEO refinament | `frontend/observatori.html` | 2-3h | Pla 032 + 4 setmanes dades reals |

**Total estimat**: 11-16 hores de treball efectiu.

### Primer increment demostrable (després del pla 032)

Una pàgina pública a `/observatori` amb:
- 3 números estàtics al hero (total actual, data de l'última actualització, nombre de grados)
- 1 gràfic de línies (evolució del total — V1)
- 1 gràfic de distribució per grado (V3)
- 1 llista d'últimes novetats amb links al cercador filtrat (V6)

Completament funcional amb les 10 entrades actuals de `refresh_history.json` + la taula `observatory_snapshots` migrada.

### Endoll futur: dades de centres (post-pla 016b)

Quan el pla 016b (scraper de centres per grau) estigui completat i hi hagi dades fiables a `oferta_centres.json`:
- Afegir camp `n_centres` a `observatory_snapshots`
- Afegir V7 (visualització): "Centres per família professional" (mapa o barres)
- El endpoint `/api/observatory` retornarà `n_centres` per a cada snapshot

**No hi ha cap canvi d'arquitectura** necessari — és una columna afegida a la migració 003 i un camp addicional al JSON de resposta.

---

## Mockup d'estructura HTML (opcional)

```
observatori.html
├── <head> — meta SEO, fonts Google (=historial.html), +uPlot si s'escull
├── <body>
│   ├── .topbar (idèntic a historial.html)
│   ├── .hero
│   │   ├── <h1> "L'oferta FP espanyola en dades"
│   │   ├── .hero-sub "Actualitzat automàticament cada setmana des de todofp.es"
│   │   └── .stats-strip
│   │       ├── .stat-card "12.XXX titulacions actives"
│   │       ├── .stat-card "5 grados (A–E)"
│   │       └── .stat-card "Darrera actualització: DD/MM/YYYY"
│   ├── .content
│   │   ├── .chart-section
│   │   │   ├── h2 "Evolució del total de titulacions"
│   │   │   └── #chart-total (uPlot / SVG)
│   │   ├── .chart-section
│   │   │   ├── h2 "Distribució per grado"
│   │   │   └── #chart-grados (barres horitzontals SVG)
│   │   └── .novetats-section
│   │       ├── h2 "Darreres novetats"
│   │       └── .novetats-list (render JS, amb links ?grado=X&q=denominacio)
│   └── .footer-note "Font: Ministerio de Educación, FP.es..."
│   <noscript>Total: X titulacions. Grado A: X, B: X, C: X, D: X, E: X.</noscript>
└── <script>
    ├── fetch('/api/observatory') → render stats + gràfics
    └── fetch('/api/refresh-history') → render novetats
```

### Endpoint `/api/observatory` (resposta JSON)

```json
{
  "current": {
    "ts": "2026-06-17T03:00:00+00:00",
    "total": 12894,
    "by_grado": {"A": 8730, "B": 2952, "C": 981, "D": 195, "E": 36}
  },
  "series": [
    {"ts": "2026-06-17", "total": 12894, "A": 8730, "B": 2952, "C": 981, "D": 195, "E": 36},
    ...
  ],
  "recent_changes": {
    "n_altes_30d": 90,
    "n_baixes_30d": 0,
    "top_families": ["Madera y Mueble", "Artes Gráficas"]
  }
}
```

El frontend rep tot el necessari en una sola crida. No cal fer join al client.

---

## Decisions finals (tancades pel revisor, 2026-06-17)

1. **Gràfics**: **uPlot vendoritzat** (`frontend/vendor/uplot.min.js`) per a sèries temporals (V1, V2, V4). SVG manual per a la distribució per grado (V3, 5 barres simples).
2. **Idioma**: català com a idioma principal (`<html lang="ca">`), `<title>` i `<meta name="description">` en castellà per a SEO. Segueix el patró d'`historial.html`.
3. **Numeració plans**: 030 → 031 → 032 → 033 (029 ja existeix per a alertes F3).
