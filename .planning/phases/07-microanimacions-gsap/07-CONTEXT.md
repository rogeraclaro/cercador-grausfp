# Phase 7: Microanimacions GSAP - Context

**Gathered:** 2026-10-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add GSAP-driven micro-animations, inspired by the launch-video compositions, to three existing pages — `index.html`, `observatori.html` and `itinerari.html` — as pure enhancement. No new features, no behaviour or UX flow changes, no delay of results or interaction. GSAP is vendored as a new explicit dependency exception (like Cytoscape, plan 073).

Order: index.html first.

</domain>

<decisions>
## Implementation Decisions

### Dependency & loading (pre-decided by owner, locked)
- **D-01:** GSAP added as an explicit exception to the "no other dependency" rule. Update the project `CLAUDE.md` Constraints → Tech Stack line, mirroring the Cytoscape wording (vendored, no CDN, no plugins, only on the pages that use it). — **Reversibility:** reversible
- **D-02:** Vendored at `frontend/vendor/gsap-<version>.min.js` (core only, no CDN, no plugins). Launch compositions use GSAP 3.14.2 core — preferred version unless research finds a reason otherwise. Verify the license of that exact version (GSAP "Standard no-charge license" since 3.13 — confirm terms permit commercial self-hosting) and record it.
- **D-03:** Loaded only on pages that use it (index, observatori, itinerari). Follow the existing vendor naming pattern `<lib>-<semver>.min.js`.
- **D-04:** All animation set up inside `gsap.matchMedia()` with a `(prefers-reduced-motion: no-preference)` condition; reduced motion → no animation, final state immediately.
- **D-05:** If GSAP fails to load (`typeof gsap === 'undefined'`), the app works identically without animation. Animation code must be a guarded no-op; no content may start hidden in CSS/HTML waiting for GSAP (no FOUC-hiding that depends on JS).
- **D-06:** Content must be readable and clickable from the first frame. Animations never gate data rendering, focus, clicks or keyboard.

### Durations (discussed)
- **D-07:** Each individual tween is 150–250 ms. A whole sequence (stagger cascade, segment-by-segment line draw, counter) may total at most **600 ms**, with content already legible/clickable from frame one. Video-length timings (700 ms line draws, ≥1 s counters) are rejected.

### index.html — result rows (discussed)
- **D-08:** Cascade triggers when the result set changes due to the search text (after the existing 250 ms debounce) or a filter change. Does NOT trigger on pagination, row expand/collapse, favourite toggles, or initial data load.
- **D-09:** Only the first ~10 visible rows animate (50 rows/page, no virtualization). Motion: `opacity 0.4→1` + `y 8px→0`, 180 ms, `expo.out`, stagger 20 ms (≈360 ms total for 10 rows). Rows start at opacity 0.4, never 0.
- **D-10:** A new query kills any in-flight cascade before starting the next (no tween pile-up on fast typing).

### index.html — "Alerta desada correctament" (discussed)
- **D-11:** Keep the existing centred modal (`.centres-modal-overlay > .centres-modal`, focus handling, Esc/backdrop close) — NOT converted to a toast. Add: modal box `scale 0.96→1` on enter, and a small pop on the ✓ in `--path-ink` green (`back.out`, ~200 ms). Success state only; error state unchanged.

### observatori.html (scope decided, details to Claude)
- **D-12:** Animate "Distribució per grau": bars grow from 0 to their width and counters count up (proxy tween + `Math.round` into `textContent`, as in the compositions), within D-07 limits. Final numbers must be correct in the DOM/for screen readers even mid-animation or without GSAP.

### itinerari.html (discussed)
- **D-13:** Only the timeline view (SVG paths from `drawLines()` and `.node` stops). Lines draw segment by segment via `pathLength="1"` + `strokeDashoffset 1→0` (no DrawSVG), stops light up in `--path-ink` green in sequence. Graf (Cytoscape) unchanged — keeps its existing `cy.animate` fit. Tree view: no animation.
- **D-14:** "Primera parada" highlight for the focus element (`.node.is-focus`), inspired by the `#a5-stop` tag (`opacity 0, y 10→0`, `expo.out`), within D-07 limits.
- **D-15:** itinerari.html already has a reduced-motion CSS guard and a `reducedMotion()` JS helper — new animation must stay consistent with them.

### Phase structure (discussed)
- **D-16:** One phase, plans per page, each validated and deployed separately:
  - Plan 1: vendor GSAP + license check + CLAUDE.md update + shared helper (matchMedia + no-GSAP fallback) + index.html (rows + modal).
  - Plan 2: observatori.html.
  - Plan 3: itinerari.html (segment draw, green stops, first stop).

### Claude's Discretion
- Shared helper shape (a small `frontend/motion.js` or inline per page) — keep it minimal; no abstraction beyond what three pages need.
- How to detect "result set changed by search/filter" in Alpine (e.g. `$watch` on search/filters, then `$nextTick`) vs. pagination.
- Exact eases per element as long as they come from the compositions' vocabulary (`expo.out`, `power2.out`, `back.out`).
- Cache-busting `?v=` on new script tags, consistent with existing practice.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project constraints
- `CLAUDE.md` (repo root, `Cercador Graus/CLAUDE.md`) — Constraints → Tech Stack; Cytoscape exception wording to mirror.
- `fp-cercador/plans/073-itinerari-graf-cytoscape.md` — precedent for vendoring a library as an explicit exception (lazy load, version in filename).
- `fp-cercador/DESIGN.md` — committed design system ("The Official Register"); tokens incl. `--path-ink`.

### Motion reference (launch video)
- `grausfp-launch/index.html` — GSAP 3.14.2 core reference.
- `grausfp-launch/compositions/a3-escribe.html` — search rows reveal / stagger.
- `grausfp-launch/compositions/a5-itinerari.html` — line draw (`pathLength=1` + dashoffset), node entrance, `#a5-stop` first-stop tag.
- `grausfp-launch/compositions/a6-alertes.html` — alert confirmation.
- `grausfp-launch/compositions/a7-tancament.html`, `b2-tot-junt.html` — counter tween pattern.
- `grausfp-launch/assets/gfp-data.js` — `rowStagger` values.
- Explicitly rejected from the video: chaos, camera moves, blur transitions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/vendor/` — `alpinejs-3.15.11.min.js`, `cytoscape-3.34.3.min.js`, `uplot.min.js`; naming `<lib>-<semver>.min.js`.
- `itinerari.html:967` `reducedMotion()` JS helper; `itinerari.html:380-382` reduced-motion CSS guard.
- `frontend/site.css:24` `--path-ink: #2a6e2a`.

### Established Patterns
- index.html rows: `<template x-for="row in pagedRecords" :key="row.id">` (~3617), one `<tbody>` per result, main `<tr :data-row-id>`; `pageSize: 50` (~2079); search `x-model.debounce.250ms="search"` + `@input="resetPage()"` (~3340); filters `x-model` + `@change="resetPage()"`; `filteredRecords` getter (~2383).
- Alert modal: index.html ~4347-4379, `x-show="alertModalVisible"` with `x-transition` opacity 150/100 ms; success/error via `x-if` on `alertSaveError`; i18n key `modal.alert.ok`.
- observatori.html: no Alpine; `renderBarChart()` (~346-361) builds HTML via `innerHTML`, `.bar-fill style="width:${pct}%"`, CSS `transition: width 0.4s ease` (~153) that never fires; `#stat-total` via `textContent` (~459).
- itinerari.html: `drawLines()` (~1372-1398) creates cubic Bézier `<path>`s in `<svg class="tl-lines" x-ref="lines">` with `data-from`/`data-to` and classes `t-full|t-part|t-old` (dash arrays for part/old — line-draw must not clobber those dash patterns); `paintLines()` toggles `.on/.off` on hover; focus `.node.is-focus` (~373-376).
- No `prefers-reduced-motion` rule exists in index.html or site.css yet.

### Integration Points
- index.html: vendor script tag near Alpine (`<script defer src="vendor/alpinejs-3.15.11.min.js">` ~3251).
- itinerari.html: hook after `drawLines()` call (~1263) for timeline view.
- observatori.html: hook after `renderBarChart()` call (~470).

</code_context>

<specifics>
## Specific Ideas

- Motion vocabulary taken from the compositions: `expo.out` entrances, `power2.in` exits, `back.out` for the ✓ pop, hand-rolled line draw without DrawSVG, proxy-object counters.
- Rows: video uses 140–160 ms stagger; app uses 20 ms to stay within D-07.

</specifics>

<deferred>
## Deferred Ideas

- Cytoscape Graf animation (focus/edges lighting via `ele.animate()`) — not in this phase.
- Tree view branch cascade on `<details>` open — not in this phase.
- Converting the alert modal to a toast — rejected for now (UX change).

</deferred>

---

*Phase: 07-microanimacions-gsap*
