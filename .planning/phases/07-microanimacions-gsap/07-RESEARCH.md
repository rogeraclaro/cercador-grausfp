# Phase 7: Microanimacions GSAP - Research

**Researched:** 2026-10-28
**Domain:** GSAP 3 core micro-animations on a no-build vanilla + Alpine.js 3 frontend (index / observatori / itinerari)
**Confidence:** HIGH (license text, file hash, helper behaviour and the Alpine timing were verified this session; Safari/Firefox rendering of `<tr>` transforms and production caching of the new files are ASSUMED)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Dependency & loading (pre-decided by owner, locked)
- **D-01:** GSAP added as an explicit exception to the "no other dependency" rule. Update the project `CLAUDE.md` Constraints → Tech Stack line, mirroring the Cytoscape wording (vendored, no CDN, no plugins, only on the pages that use it). — **Reversibility:** reversible
- **D-02:** Vendored at `frontend/vendor/gsap-<version>.min.js` (core only, no CDN, no plugins). Launch compositions use GSAP 3.14.2 core — preferred version unless research finds a reason otherwise. Verify the license of that exact version (GSAP "Standard no-charge license" since 3.13 — confirm terms permit commercial self-hosting) and record it.
- **D-03:** Loaded only on pages that use it (index, observatori, itinerari). Follow the existing vendor naming pattern `<lib>-<semver>.min.js`.
- **D-04:** All animation set up inside `gsap.matchMedia()` with a `(prefers-reduced-motion: no-preference)` condition; reduced motion → no animation, final state immediately.
- **D-05:** If GSAP fails to load (`typeof gsap === 'undefined'`), the app works identically without animation. Animation code must be a guarded no-op; no content may start hidden in CSS/HTML waiting for GSAP (no FOUC-hiding that depends on JS).
- **D-06:** Content must be readable and clickable from the first frame. Animations never gate data rendering, focus, clicks or keyboard.

#### Durations (discussed)
- **D-07:** Each individual tween is 150–250 ms. A whole sequence (stagger cascade, segment-by-segment line draw, counter) may total at most **600 ms**, with content already legible/clickable from frame one. Video-length timings (700 ms line draws, ≥1 s counters) are rejected.

#### index.html — result rows (discussed)
- **D-08:** Cascade triggers when the result set changes due to the search text (after the existing 250 ms debounce) or a filter change. Does NOT trigger on pagination, row expand/collapse, favourite toggles, or initial data load.
- **D-09:** Only the first ~10 visible rows animate (50 rows/page, no virtualization). Motion: `opacity 0.4→1` + `y 8px→0`, 180 ms, `expo.out`, stagger 20 ms (≈360 ms total for 10 rows). Rows start at opacity 0.4, never 0.
- **D-10:** A new query kills any in-flight cascade before starting the next (no tween pile-up on fast typing).

#### index.html — "Alerta desada correctament" (discussed)
- **D-11:** Keep the existing centred modal (`.centres-modal-overlay > .centres-modal`, focus handling, Esc/backdrop close) — NOT converted to a toast. Add: modal box `scale 0.96→1` on enter, and a small pop on the ✓ in `--path-ink` green (`back.out`, ~200 ms). Success state only; error state unchanged.

#### observatori.html (scope decided, details to Claude)
- **D-12:** Animate "Distribució per grau": bars grow from 0 to their width and counters count up (proxy tween + `Math.round` into `textContent`, as in the compositions), within D-07 limits. Final numbers must be correct in the DOM/for screen readers even mid-animation or without GSAP.

#### itinerari.html (discussed)
- **D-13:** Only the timeline view (SVG paths from `drawLines()` and `.node` stops). Lines draw segment by segment via `pathLength="1"` + `strokeDashoffset 1→0` (no DrawSVG), stops light up in `--path-ink` green in sequence. Graf (Cytoscape) unchanged — keeps its existing `cy.animate` fit. Tree view: no animation.
- **D-14:** "Primera parada" highlight for the focus element (`.node.is-focus`), inspired by the `#a5-stop` tag (`opacity 0, y 10→0`, `expo.out`), within D-07 limits.
- **D-15:** itinerari.html already has a reduced-motion CSS guard and a `reducedMotion()` JS helper — new animation must stay consistent with them.

#### Phase structure (discussed)
- **D-16:** One phase, plans per page, each validated and deployed separately:
  - Plan 1: vendor GSAP + license check + CLAUDE.md update + shared helper (matchMedia + no-GSAP fallback) + index.html (rows + modal).
  - Plan 2: observatori.html.
  - Plan 3: itinerari.html (segment draw, green stops, first stop).

### Claude's Discretion
- Shared helper shape (a small `frontend/motion.js` or inline per page) — keep it minimal; no abstraction beyond what three pages need.
- How to detect "result set changed by search/filter" in Alpine (e.g. `$watch` on search/filters, then `$nextTick`) vs. pagination.
- Exact eases per element as long as they come from the compositions' vocabulary (`expo.out`, `power2.out`, `back.out`).
- Cache-busting `?v=` on new script tags, consistent with existing practice.

### Deferred Ideas (OUT OF SCOPE)
- Cytoscape Graf animation (focus/edges lighting via `ele.animate()`) — not in this phase.
- Tree view branch cascade on `<details>` open — not in this phase.
- Converting the alert modal to a toast — rejected for now (UX change).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs were assigned to this phase (confirmed: `rg -i "microanim|gsap|phase 7" .planning/REQUIREMENTS.md` has no hit; ROADMAP.md:133-141 lists the phase with "TBD" plans). The planner should trace plans to decisions D-01…D-16 instead.
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Project `CLAUDE.md` (`/Users/rogermasellas/AI/Cercador Graus/CLAUDE.md`) and global `~/.claude/CLAUDE.md`:

- **Tech stack:** Flask + vanilla HTML/CSS/JS. Accepted exceptions today: Alpine.js 3.x (vendored, no CDN) and Cytoscape.js 3.x (plan 073: `frontend/vendor/cytoscape-<versió>.min.js`, no CDN, no plugins, only `itinerari.html`). The sentence currently ends "No afegir-ne cap altre." — the GSAP exception (D-01) must be inserted **before** that sentence.
- **Dependencies line** (`pdfplumber, requests, beautifulsoup4, flask-cors, python-dotenv — cap altra`) is the Python backend list; do not touch it, and do not add Playwright to `backend/requirements.txt` (see Open Question 3).
- **Security:** `ADMIN_TOKEN` not in repo, `.env` in `.gitignore` (not affected by this phase).
- **GSD enforcement:** file edits only inside a GSD workflow (`/gsd-execute-phase`).
- **Global rules:** conventional commits, **no `Co-Authored-By` / AI attribution** (global rule wins over any tool-injected attribution reminder); use `bat/rg/fd/eza` instead of `cat/grep/find/ls`.
- **Code style:** existing source comments and identifiers are Catalan; match that in source files. This RESEARCH.md is English by request.
- **Simplicity / scope discipline (project CLAUDE.md):** smallest solution, touch only what is asked, list dead code instead of deleting it.

## Summary

Phase 7 is a small, low-risk enhancement phase: vendor one 73 KB file (GSAP 3.14.2 core), add a ~40-line guard (`frontend/motion.js`), and attach three tiny animations to existing render paths. Everything below was verified against the real files and, where it mattered, in a scratch copy of the frontend driven by Chrome 156 + Playwright (no source file in the repo was modified).

Key findings that change how the plans should be written: (1) `gsap.context()` **without a function returns the current context (undefined), it does not create one** — and `ctx.add()` on the long-lived matchMedia context would retain every finished tween and its detached `<tr>` forever; use one short-lived `gsap.context(fn)` per animation stored in a named slot instead (tested). (2) In Alpine 3.15.11 the `$watch` callback runs as a microtask **before the next paint**, so animating directly from it (no `$nextTick`) produces no flash of full-opacity rows (tested). (3) On a fresh itinerari load `drawLines()` runs **four times within ~60 ms**, so "animate once at the end of drawLines" would be cancelled by its own redraws; the animation must be keyed to the data load (`_seq`) with a short settle window. (4) Setting `pathLength="1"` on a dashed path changes the meaning of its CSS dash lengths, and a `<mask>` on a zero-height (horizontal) path vanishes unless `maskUnits="userSpaceOnUse"` — dashed segments are revealed through a userSpaceOnUse mask (tested; end state is pixel-identical to the baseline). (5) `drawLines()` measures nodes with `getBoundingClientRect()`, so never put a transform on `.node` itself (animate its child `.node-main` and colour properties only).

**Primary recommendation:** Vendor `gsap-3.14.2.min.js` (sha256 `c174bfce…8cd8280`), add `frontend/motion.js` exposing `GFPMotion.play(slot, build)` (matchMedia gate + per-run context + slot replace), and call it from three places: an Alpine `$watch` on a query signature (index rows), a `$watch('alertModalVisible')` (modal), and after the existing render calls in observatori/itinerari. Page-specific tween code stays inline next to its trigger.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Motion gating (reduced-motion, GSAP absent) | Browser / Client | — | Pure client concern; `gsap.matchMedia()` + guard in `motion.js` |
| Row cascade trigger (search/filter vs pagination) | Browser / Client (Alpine component) | — | State lives in the `cercador` Alpine component; no server involvement |
| Modal enter / ✓ pop | Browser / Client (Alpine) | — | `alertModalVisible` is client state; Alpine `x-transition` already owns the overlay opacity |
| Observatori bars / counters | Browser / Client (vanilla JS) | API (data only) | Data arrives from `/api/observatory`; animation is post-render |
| Itinerari line draw / stop lighting | Browser / Client (Alpine + SVG) | — | Paths are generated client-side by `drawLines()` |
| Vendored file delivery + caching | CDN / Static (nginx on the VPS) | — | Static files from the repo; nginx adds gzip and `no-transform` only |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GSAP (core only) | 3.14.2 (published 2025-12-12) | Tweens/timelines, `gsap.matchMedia()`, `gsap.context()` | Owner decision D-02; same version as the launch-video compositions; `latest` on npm is 3.15.0 (2026-04-13) but 3.14.2 is >10 months old and already used in `grausfp-launch/index.html:7` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `frontend/motion.js` (first-party, ~40 lines) | v1 | `GFPMotion.play(slot, build)` guard | Loaded on index, observatori, itinerari after the GSAP script |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GSAP 3.14.2 | GSAP 3.15.0 | Newer, one-file swap later; no reason found to deviate from the owner's preferred version. No release notes were retrievable (GitHub Releases page is empty), so a 3.15.0 move is untested here. |
| per-page inline helper | shared `motion.js` | Three copies of the matchMedia guard would drift; a shared 40-line file is the smallest abstraction that three pages need. |
| `gsap.matchMedia()` + `ctx.add()` per tween | one `gsap.context(fn)` per run in a slot | `ctx.add()` records every Animation in `context.data` forever (GSAP source: `Animation` constructor does `_context.data.push(this)` at gsap.js:1551; nothing prunes it) → leaks detached rows on every search. |

**Installation (no npm in the frontend; one-time fetch, then commit the file):**
```bash
# run in an empty scratch dir; do NOT run npm install in the repo
curl -sSL -o gsap-3.14.2.tgz https://registry.npmjs.org/gsap/-/gsap-3.14.2.tgz
shasum gsap-3.14.2.tgz            # expect 6a9ea31e5046948e0be61eae006ae576ca5937d6 (npm dist.shasum)
tar -xzf gsap-3.14.2.tgz package/dist/gsap.min.js
shasum -a 256 package/dist/gsap.min.js   # expect c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280
cp package/dist/gsap.min.js "<repo>/fp-cercador/frontend/vendor/gsap-3.14.2.min.js"
```

**Version verification:** `npm view gsap version` → `3.15.0` (latest); `npm view gsap@3.14.2` → tarball `https://registry.npmjs.org/gsap/-/gsap-3.14.2.tgz`, `dist.shasum = 6a9ea31e5046948e0be61eae006ae576ca5937d6`, `dist.integrity = sha512-P8/mMxVLU7o4+55+1TCnQrPmgjPKnwkzkXOK1asnR9Jg2lna4tEY5qBJjMmAaOBDDZWtlRjBXjLa0w53G/uBLA==`; `time["3.14.2"] = 2025-12-12T21:12:52.670Z`. [VERIFIED: npm registry, 2026-10-28]

**File facts (verified this session):** `dist/gsap.min.js` = **72,779 bytes**, sha256 `c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280`, ~28 KB gzipped (`gzip -9`: 28,255 bytes). The jsDelivr copy (`cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js`, `content-length: 72779`) has the **identical sha256** — two independent sources agree. No `new Function`, `eval(`, `XMLHttpRequest`, `sendBeacon`, `document.write` in the file; `npm view gsap@3.14.2 scripts.postinstall` is empty. [VERIFIED: local download + jsDelivr]

**License header (first 8 lines of the file, keep untouched — the license forbids removing proprietary notices):**
```
/*!
 * GSAP 3.14.2
 * https://gsap.com
 * 
 * @license Copyright 2025, GreenSock. All rights reserved.
 * Subject to the terms at https://gsap.com/standard-license.
 * @author: Jack Doyle, jack@greensock.com
 */
```
The npm tarball contains no separate `LICENSE` file (`tar: package/LICENSE: Not found in archive`); `package.json` says `"license": "Standard 'no charge' license: https://gsap.com/standard-license."` [VERIFIED: tarball]. Do not re-minify or strip the header.

### License terms (https://gsap.com/standard-license, fetched 2026-10-28; "Effective date: April 30, 2025 / Last modified date: May 30, 2025")
- Permitted Uses = "the implementation and/or use of GSAP Products on any website, web application, or digital interface by any person or entity"; the grant covers the right to "use, reproduce, display, and implement GSAP Products solely for Permitted Uses". [CITED: gsap.com/standard-license]
- Commercial use: "Commercial usage is covered under the standard license"; the formerly paid plugins are also free in commercial projects. [CITED: gsap.com/standard-license FAQ]
- Restriction (Prohibited Uses): use "in tools that allow users to build visual animations without code" that materially assists "a solution that competes with Webflow's visual animation building capabilities"; also no reverse-engineering to create Competitive Products and no removing/altering proprietary notices. GrausFP is a search app and is not such a tool. [CITED: gsap.com/standard-license]
- The license text does **not** say anything explicit about self-hosting/bundling; it neither requires nor forbids shipping the license text with the file. Self-hosting is covered only by inference from "reproduce … on any website" → recorded as A1. The 3.14.2 header points at the live page ("Subject to the terms at https://gsap.com/standard-license"), so the terms that apply are whatever that page says today; re-check it when upgrading GSAP.
- **Record in the repo** (mirror the Cytoscape precedent comment at `itinerari.html:944-945`): an HTML comment next to each `<script src="vendor/gsap-…">` stating version, source (`npm gsap@3.14.2 dist/gsap.min.js`), sha256, license URL and the 2026-10-28 effective/modified dates, plus the CLAUDE.md exception line.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| gsap | npm | created 2014-08-25 (12 yrs) | ~6.5M/wk | github.com/greensock/GSAP | OK (`gsd-tools query package-legitimacy check --ecosystem npm gsap`; `postinstall: null`, `deprecated: false`) | Approved |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
The package name `gsap` is confirmed by the official docs (gsap.com) and the owner's decision D-02, not only by the registry. Nothing is installed with npm in this phase: the single file is vendored.

## Architecture Patterns

### System Architecture Diagram

```
 page load (3 pages)
   |
   v
 <script defer vendor/gsap-3.14.2.min.js>  --(blocked/404)--> window.gsap undefined
   |                                                              |
   v                                                              v
 <script defer motion.js?v=1>  ----------------------------> GFPMotion.play() returns false (no-op)
   |  gsap.matchMedia().add('(prefers-reduced-motion: no-preference)')
   |       enabled = true   <--- OS/browser flips to "reduce" at any time ---> revert slots, enabled = false
   v
 page-specific trigger (user/data event)
   |
   |- index: input/select/tab -> Alpine state change -> x-for re-renders rows (microtask flush)
   |          -> $watch(signature) callback (next microtask, before paint)
   |          -> guard: nom mode + first-10-ids/count key changed?
   |          -> GFPMotion.play('rows', fromTo(first 10 tr[data-row-id]))      [pagination never changes signature]
   |
   |- index: alertModalVisible=true -> $watch -> play('modal', box scale + .ok-tick pop)   [x-show/x-transition own the overlay]
   |
   |- observatori: fetch -> renderBarChart(innerHTML, final width + final text) -> play('bars', scaleX + count-up ghost)
   |
   '- itinerari: load -> $nextTick(renderTree; redraw) -> drawLines() x4 within ~60 ms -> animateTimeline()
              keyed to _seq with 800 ms settle window -> play('timeline', solid: dashoffset | dashed: userSpaceOnUse mask
              | nodes: colour from-tween | focus: .node-main from-tween)

 each play(): revert previous context in the same slot -> gsap.context(fn) -> try/catch -> on error revert (content stays final)
```

### Recommended Project Structure
```
fp-cercador/frontend/
├── motion.js                       # NEW: GFPMotion guard (≈40 lines), loaded by the 3 pages only
├── vendor/gsap-3.14.2.min.js       # NEW: vendored core, header intact
├── index.html                      # + 2 script tags before Alpine, + $watch x2 in init(), + .ok-tick markup/CSS
├── observatori.html                # + 2 plain script tags, + data-* in renderBarChart, + animateBars()
└── itinerari.html                  # + 2 script tags, + animateTimeline() called from drawLines()
```
Page-specific tween code stays inline in each page (selectors are page-coupled; `motion.js` holds only the guard).

### Pattern 1: GFPMotion guard (matchMedia gate + per-run context + named slot)
**What:** `gsap.matchMedia()` is used only as the reduced-motion **gate** (and to revert in-flight animations when the OS setting flips). Every animation runs inside its own short-lived `gsap.context(fn)` kept in a named slot; a new `play()` in the same slot reverts the previous context first (this is D-10 "kill in-flight cascade" and also clears stale inline styles on Alpine-reused rows).
**When to use:** every animation in the phase.
**Example:**
```js
/* frontend/motion.js — guarda per a les microanimacions GSAP (fase 07). Carregar DESPRÉS de vendor/gsap-*.min.js. */
(function () {
  'use strict';
  var enabled = false;   // només mentre (prefers-reduced-motion: no-preference) coincideix i GSAP existeix
  var slots = {};        // nom -> gsap.context de l'animació en curs

  function stop(name) {
    var c = slots[name];
    if (c) { slots[name] = null; try { c.revert(); } catch (e) { } }
  }

  if (window.gsap && typeof gsap.matchMedia === 'function') {
    try {
      gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', function () {
        enabled = true;
        // Es crida quan la consulta deixa de coincidir: no cal cridar context.revert() aquí.
        return function () { enabled = false; Object.keys(slots).forEach(stop); };
      });
    } catch (e) { enabled = false; }
  }

  window.GFPMotion = {
    // build(gsap) crea els tweens de manera síncrona; pot retornar una funció de neteja (s'executa en revertir).
    play: function (name, build) {
      if (!enabled) return false;
      stop(name);
      var failed = false;
      var c = gsap.context(function () {   // NB: gsap.context() sense funció NO crea res, retorna el context actual
        try { return build(gsap); } catch (e) { failed = true; if (window.console) console.warn('[motion]', e); }
      });
      if (failed) { try { c.revert(); } catch (e) { } return false; }
      slots[name] = c;
      return true;
    },
    stop: stop
  };
})();
```
[VERIFIED: Chrome 156 + GSAP 3.14.2, scratch harness 2026-10-28] Results: play → inline styles present mid-flight and all cleared at the end; double `play` 40 ms apart → all clean; switching `prefers-reduced-motion` to `reduce` mid-flight → styles reverted, subsequent `play` returns `false`, switching back re-enables; a builder that throws → reverted, returns `false`, no page error; reduce at load → no-op; GSAP script blocked → `GFPMotion` exists, `play` returns `false`, zero page errors. Source facts behind it: `gsap.context(func)` runs `func` immediately and a **returned function is pushed to the cleanup list** (`Context.add`, gsap.js:3649-3669 — so a builder must return either nothing or a cleanup function, never a tween); `matchMedia.add` runs the handler only when a query matches and reverts + re-runs on change (gsap.js:3586-3616, 3765-3860). [VERIFIED: gsap.js source in the 3.14.2 tarball; CITED: gsap.com/docs/v3/GSAP/gsap.matchMedia/]

Callers always use optional chaining so a missing/failed `motion.js` is also harmless: `window.GFPMotion?.play('rows', g => { … })` (the codebase already uses `?.`, e.g. `index.html:2202`).

**Script placement:**
- `index.html` / `itinerari.html`: two `defer` tags **immediately before** the existing Alpine tag (`index.html:3251`, `itinerari.html:1573`): `<script defer src="vendor/gsap-3.14.2.min.js"></script>` then `<script defer src="motion.js?v=1"></script>`. Deferred scripts execute in document order before Alpine starts.
- `observatori.html`: plain (non-defer) tags before the inline script at line 337 (the inline script calls `load()` immediately and would otherwise race the deferred scripts): `<script src="vendor/gsap-3.14.2.min.js"></script><script src="motion.js?v=1"></script>` after `feedback.js` (line 331).

### Pattern 2: index.html rows — trigger on a query signature, guard on the visible result key
**What:** Alpine `$watch` on a **string signature of the search/filter inputs only** (pagination, expand/collapse, favourites toggles, sort and data load are not in it), then a cheap guard that skips animation if the first-10 ids + count did not change (typing "cocin"→"cocina" with identical results must not re-flash).
**Verified facts (code read this session):** `search: ''`, `filterGrado: ''`, `filterFamilia: ''`, `filterNivel: ''`, `filterOld: 'all'`, `currentPage: 1`, `pageSize: 50` (`index.html:2071-2079`); `x-model.debounce.250ms="search" @input="resetPage()"` (`index.html:3340`); `<template x-for="row in pagedRecords" :key="row.id">` with one `<tbody>` per row and `:data-row-id="row.id"` on the main `<tr>` (`index.html:3617-3620`); `get pagedRecords()` slices `filteredRecords` by `currentPage`/`pageSize` (`index.html:2473-2476`); only main rows carry `data-row-id` (grep: lines 2363, 2377, 3620). `this.$watch('fpoFilters', …)` at `index.html:2233` is the precedent for watchers at the top of `init()`.
**Timing facts (verified in Chrome 156):** Alpine's `$watch` queues its callback with `queueMicrotask` (vendored `St()` function), x-for renders in the same flush → at callback time the **new rows are already in the DOM** (log: 10 `tr[data-row-id]`), and the first painted frame already shows the new first row at `opacity: 0.4; transform: matrix(1,0,0,1,0,8)` — **no flash of opaque rows**. `$nextTick` is `queueMicrotask → setTimeout` (vendored `st()`), i.e. a macrotask that *can* be preceded by a paint [ASSUMED for the paint ordering; the direct call needs no such assumption]. Therefore call `play()` straight from the `$watch` callback.
**Example:**
```js
// init(), junt al $watch('fpoFilters') (index.html:2233) — abans de qualsevol await
let rowsKey = '';
this.$watch(
  () => [this.search, this.filterGrado, this.filterFamilia, this.filterNivel, this.filterOld, this.filterFavs].join('\u0001'),
  () => {
    if (this.searchMode !== 'nom') return;   // en mode ocupació filteredRecords és un getter amb efectes (ocupMatchedRecords)
    const key = this.filteredCount + ':' + this.pagedRecords.slice(0, 10).map(r => r.id).join(',');
    if (key === rowsKey) return;
    rowsKey = key;
    window.GFPMotion?.play('rows', g => {
      const rows = [...document.querySelectorAll('#results-table tr[data-row-id]')].slice(0, 10);
      if (!rows.length) return;
      g.fromTo(rows, { opacity: 0.4, y: 8 },
        { opacity: 1, y: 0, duration: 0.18, ease: 'expo.out', stagger: 0.02, clearProps: 'opacity,transform' });
    });
  });
```
Duration check: 9 × 20 ms stagger + 180 ms = **360 ms** ≤ 600 (D-07/D-09). `clearProps` leaves an empty `style=""` attribute on the rows (observed) — harmless. `$watch` with a function getter is supported by the vendored Alpine (the experiment used exactly this form and the watcher fired). [VERIFIED: local experiment + vendored Alpine source]

`<tr>` transforms render correctly in Chromium (computed `matrix(1, 0, 0, 1, 0, 8)` → 0). The CSS Transforms spec lists table rows as transformable, but Safari/Firefox were not testable here (Playwright's bundled Firefox/WebKit are not installed) → A2 / Open Question 2; fallback if a browser ignores it: opacity-only (the opacity part is universally supported).

### Pattern 3: Alert modal — box scale + ✓ pop from `$watch('alertModalVisible')`
**What:** The overlay opacity belongs to Alpine (`x-show` + `x-transition:enter.opacity.duration.150ms`, `index.html:4348-4353`); GSAP touches only the inner `.centres-modal` box (`transform`) and a new `.ok-tick` span, so there is no property overlap and focus handling (`x-effect` focusing `$refs.alertModalClose`, `index.html:4350`) is untouched.
**Verified in Chrome 156:** in the watcher callback the overlay is still `display:none` (x-show with x-transition defers display by a frame), the tween nevertheless starts at once; the first visible frame (t≈33 ms) already shows `scale 0.9867` (≈⅓ of the `expo.out` move is consumed while hidden); focus lands on `centres-modal-close` at t≈43 ms; the transform is cleared at the end (`tf: none`). Accept this, or add `delay: 0.03` to the box tween.
**✓ markup (decision for the planner — recommended Option A):** the ✓ is currently part of the i18n value (`i18n.js:190` `'modal.alert.ok': '✓ Alerta desada correctament'`, `i18n.js:898` `'modal.alert.ok': '✓ Alerta guardada correctamente'`; used only at `index.html:4359`), so it cannot be animated alone. 
- **Option A (recommended):** drop the leading `✓ ` from both i18n values and render the glyph in markup: `<p class="centres-modal-msg" style="color:var(--ok-ink);"><span class="ok-tick" aria-hidden="true">✓</span> <span data-i18n="modal.alert.ok">Alerta desada correctament</span></p>` with `.ok-tick { display:inline-block; color:var(--path-ink); }`. **`display:inline-block` is mandatory — transforms do not apply to inline boxes.** Bump `i18n.js?v=` (index.html only is enough functionally; bump all 15 pages for consistency — one `sd` replace — at the cost of one 108 KB re-download per user). Bonus: `aria-hidden` stops screen readers announcing "check mark". `i18n.js:1460-1466` applies values with `innerHTML` and the ES translation is applied inside that `x-if` block (verified: ES run printed `'✓ Alerta guardada correctamente'`).
- **Option B (no i18n edit):** pop the whole `<p class="centres-modal-msg">` instead of the glyph (deviates from D-11 wording "pop on the ✓").
**Example:**
```js
this.$watch('alertModalVisible', v => {
  if (!v || this.alertSaveError) return;                    // només l'estat d'èxit (D-11)
  window.GFPMotion?.play('modal', g => {
    const box = document.querySelector('.centres-modal-overlay[role="dialog"] .centres-modal');  // o x-ref="alertBox"
    if (!box) return;
    g.fromTo(box, { scale: 0.96 }, { scale: 1, duration: 0.2, ease: 'expo.out', clearProps: 'transform' });
    const tick = box.querySelector('.ok-tick');
    if (tick) g.fromTo(tick, { scale: 0.5 }, { scale: 1, duration: 0.2, delay: 0.08, ease: 'back.out(2)', clearProps: 'transform' });
  });
});
```
(Prefer adding `x-ref="alertBox"` to the `.centres-modal` div at `index.html:4354` and using `this.$refs.alertBox` — the existing selector would match the gate modal too because both use `role="dialog"`.) Total ≈ 280 ms ≤ 600. The box starts at `scale 0.96`, opacity 1 → content readable from frame one (D-06). The box tween was verified; the ✓ tick tween was not run (markup does not exist yet) — same mechanism.

### Pattern 4: observatori — bars via `scaleX`, counters via an aria-hidden ghost
**Verified facts:** `.bar-fill { height:100%; background:var(--dark); border-radius:2px; transition: width 0.4s ease; }` (`observatori.html:149-154`); `renderBarChart()` writes `<div class="bar-fill" style="width:${pct}%"></div>` and `<span class="bar-value">${val.toLocaleString(…)} (${pct}%)</span>` via `container.innerHTML = html` (`observatori.html:346-360`); called from `load()` at line 470. The CSS `transition: width` never fires today (width is set at creation). `setLang()` does `location.reload()` (`i18n.js:1448-1451`), so there is no re-render path to guard.
**Rules:**
1. Animate **`scaleX` (transform-origin left), never `width`** — a GSAP-driven `width` would restart the 0.4 s CSS transition on every tick and fight the tween. `width:${pct}%` stays in the markup, so the final state is correct without GSAP.
2. Counters: keep `.bar-value` text final in the DOM at all times (D-12). Overlay an aria-hidden "ghost" that counts up; make the real text `color: transparent` meanwhile (opacity/visibility would hide it from assistive tech differently — `color:transparent` keeps it in the accessibility tree).
3. Return a cleanup function from the builder so a reduced-motion flip mid-animation removes the ghost and restores colour.
**Example:**
```js
// renderBarChart(): afegir al markup  data-n="${val}" data-suffix=" (${pct}%)"  a .bar-value i  .bar-value{position:relative}  al CSS.
function animateBars(g) {
  const locale = getLang() === 'ca' ? 'ca-ES' : 'es-ES';
  const rows = [...document.querySelectorAll('#chart-grados .bar-row')];
  const undo = [];
  const tl = g.timeline({ onComplete: () => undo.forEach(f => f()) });
  rows.forEach((row, i) => {
    const fill = row.querySelector('.bar-fill'), val = row.querySelector('.bar-value');
    const at = i * 0.04;                                       // 4 × 40 ms + 250 ms = 410 ms ≤ 600
    tl.fromTo(fill, { scaleX: 0, transformOrigin: '0 50%' },
      { scaleX: 1, duration: 0.25, ease: 'expo.out', clearProps: 'transform' }, at);
    const color = getComputedStyle(val).color;
    const ghost = document.createElement('span');
    ghost.setAttribute('aria-hidden', 'true');
    ghost.style.cssText = 'position:absolute;inset:0;text-align:right;color:' + color;
    val.style.color = 'transparent';
    val.appendChild(ghost);
    undo.push(() => { ghost.remove(); val.style.color = ''; });
    const target = +val.dataset.n, suffix = val.dataset.suffix, p = { n: 0 };
    tl.fromTo(p, { n: 0 }, { n: target, duration: 0.25, ease: 'expo.out',
      onUpdate: () => { ghost.textContent = Math.round(p.n).toLocaleString(locale) + suffix; } }, at);
  });
  return () => undo.forEach(f => f());      // revert / reduced-motion flip: remove ghosts, restore colour
}
// a load(), després de renderBarChart(data.current):  window.GFPMotion?.play('bars', animateBars);
```
The tween/ghost mechanics follow the compositions' proxy-object counter (`b2-tot-junt.html:70`: `tl.fromTo(n, { v: 0 }, { v: stats.total, … onUpdate() { nEl.textContent = … Math.round(n.v) … } })`) but write to an aria-hidden copy. Not run end-to-end here (observatori needs `/api/observatory`); the guard, tween and clearProps behaviours it relies on were verified in the other experiments. The hero counter `#stat-total` (`observatori.html:459`) is **not** in D-12 scope — see Open Question 1.

### Pattern 5: itinerari timeline — solid paths by dashoffset, dashed paths by userSpaceOnUse mask
**Verified code facts:** `drawLines()` (`itinerari.html:1372-1398`) removes all children of `svg.tl-lines`, sets `svg` `width`/`height` from `wrap.offsetWidth/offsetHeight`, builds one `<path>` per edge (`M a.r,a.y C mx,a.y mx,b.y b.l,b.y`) with `data-from`/`data-to`, adds class `'t-' + tier` where `cdTier(e)` returns `'old' | 'full' | 'part' | ''` for `kind === 'cd'` edges only (`itinerari.html:917-921`), then calls `paintLines()`. CSS: `.tl-lines path.t-part … { stroke-dasharray: 7 4; }`, `.t-old { stroke-dasharray: 1.5 4; stroke-linecap: round; }` (`itinerari.html:319-320`), `.tl-lines path.off { opacity: 0.35; }` (316) and `@media (prefers-reduced-motion: no-preference) { .node, .tl-lines path { transition: opacity 0.15s, stroke 0.15s; } }` (380-382). `reducedMotion()` is at line 967 (used only for Cytoscape animations).
**Measured on a fresh load (mock API, Chrome 156):** `drawLines()` was called 4 times at t = 348, 355, 405, 407 ms (data render `$nextTick`, ResizeObserver ×2, `document.fonts.ready` — `itinerari.html:1089-1094,1145`), all with the same width. Resulting paths: `['solid','solid','solid','solid','t-full','t-part','t-old','solid']` — i.e. A→B, B→C, D→E edges carry **no** tier class, only C→D edges do.
**Techniques (tested in an isolated SVG page, Chrome 156):**
- **Solid paths** (no `t-*` class, and `t-full`): `setAttribute('pathLength','1')`, `fromTo(p, {strokeDasharray:1, strokeDashoffset:1}, {strokeDashoffset:0, clearProps:'strokeDasharray,strokeDashoffset'})`. After completion the canvas is pixel-identical to the never-animated baseline.
- **Dashed paths (`t-part`, `t-old`):** **do not** set `pathLength` or inline dash properties on them — `pathLength="1"` rescales the author's dash lengths (7/4 user units become 7/4 *of a path of length 1* → effectively solid) and an inline `stroke-dasharray` overrides the CSS pattern. Reveal them through a per-path `<mask>` that contains a solid white clone of the path animated with the same `pathLength=1` + dashoffset trick. **`maskUnits="userSpaceOnUse"` with x=0,y=0,width=svg width,height=svg height is mandatory**: with the default `objectBoundingBox` units a horizontal (zero-height bounding box) path — very common here because `a.y === b.y` for straight links — is masked out entirely (screenshot evidence: the straight dashed `t-part` and the `t-old` path were missing mid-animation; with `userSpaceOnUse` they appeared progressively with the dash pattern intact). Remove the `mask` attributes and `<defs>` on complete/revert; the end state was pixel-identical to the baseline (`end==baseline: True`, 0 leftover masks/pathLength attrs).
- **Alternative if per-path animation proves fragile (fallback only):** a single `clip-path: inset(0 100% 0 0)` → `inset(0 0 0 0)` wipe on the persistent `<svg class="tl-lines">` (left→right = A→E "segment by segment"), which survives path re-creation and keeps every dash pattern. It deviates from D-13's literal "pathLength + dashoffset", so use it only with owner agreement.
**Redraw handling (the non-obvious part):** key the animation to the data load, not to `drawLines()` calls:
```js
// mòdul (fora d'Alpine, com cy / cyFor): no han de ser reactius
let linesSeq = -1, linesT0 = 0;

function animateTimeline(vm) {                 // vm = component (this); cridar al final de drawLines(), després de paintLines()
  const now = performance.now();
  const fresh = linesSeq !== vm._seq;
  if (!fresh && now - linesT0 > 800) return;   // redibuixos tardans (resize, showMore, canvi de vista) no tornen a animar
  if (fresh) { linesSeq = vm._seq; linesT0 = now; }   // redibuixos dins de 800 ms: es reinicia sobre els paths nous (play reverteix l'anterior)
  window.GFPMotion?.play('timeline', g => {
    const svg = vm.$refs.lines, paths = [...svg.querySelectorAll('path')];
    if (!paths.length) return;
    const css = getComputedStyle(document.documentElement);
    const ink = css.getPropertyValue('--path-ink').trim(), bg = css.getPropertyValue('--path-bg').trim();
    const NS = 'http://www.w3.org/2000/svg', STEP = 0.09, DUR = 0.18;
    const col = k => GRADES.indexOf(k);                       // A=0 … E=4
    const tl = g.timeline({ onComplete: cleanup });
    let defs = null;
    function cleanup() { paths.forEach(p => { p.removeAttribute('mask'); p.removeAttribute('pathLength'); }); if (defs) defs.remove(); }
    paths.forEach((p, i) => {
      const at = Math.max(col((vm.byKey[p.dataset.from] || {}).grado), 0) * STEP;   // A→B 0, B→C .09, C→D .18, D→E .27
      if (p.classList.contains('t-part') || p.classList.contains('t-old')) {
        defs = defs || svg.insertBefore(document.createElementNS(NS, 'defs'), svg.firstChild);
        const m = document.createElementNS(NS, 'mask'), c = document.createElementNS(NS, 'path');
        m.id = 'tlm' + i;
        m.setAttribute('maskUnits', 'userSpaceOnUse');         // obligatori: bbox de path horitzontal té alçada 0
        m.setAttribute('x', 0); m.setAttribute('y', 0);
        m.setAttribute('width', svg.getAttribute('width')); m.setAttribute('height', svg.getAttribute('height'));
        c.setAttribute('d', p.getAttribute('d')); c.setAttribute('pathLength', '1');
        c.setAttribute('style', 'fill:none;stroke:#fff;stroke-width:6;stroke-dasharray:1;stroke-dashoffset:1');
        m.appendChild(c); defs.appendChild(m); p.setAttribute('mask', 'url(#tlm' + i + ')');
        tl.to(c, { strokeDashoffset: 0, duration: DUR, ease: 'power2.out' }, at);
      } else {
        p.setAttribute('pathLength', '1');
        tl.fromTo(p, { strokeDasharray: 1, strokeDashoffset: 1 },
          { strokeDashoffset: 0, duration: DUR, ease: 'power2.out', clearProps: 'strokeDasharray,strokeDashoffset' }, at);
      }
    });
    // Parades: s'encenen en verd quan hi arriba el seu tram (columna k+1 amb el tram k); la columna A al principi.
    vm.$refs.tl.querySelectorAll('.node[data-key]').forEach(n => {
      const k = Math.max(col((vm.byKey[n.dataset.key] || {}).grado) - 1, 0);
      tl.from(n, { backgroundColor: bg, borderLeftColor: ink, duration: 0.18, ease: 'power2.out',
        clearProps: 'backgroundColor,borderLeftColor' }, k * STEP + DUR * 0.6);
    });
    // Primera parada: el fill intern, mai .node (drawLines() mesura .node amb getBoundingClientRect)
    const first = vm.$refs.tl.querySelector('.node.is-focus .node-main');
    if (first) tl.from(first, { opacity: 0.4, y: 8, duration: 0.2, ease: 'expo.out', clearProps: 'opacity,transform' }, 0);
    return cleanup;                                            // revert (canvi de preferència / nova càrrega)
  });
}
```
Budget: last segment starts at 0.27 s + 0.18 s = 0.45 s; last node light-up starts at 0.27 + 0.108 and lasts 0.18 → **≈0.56 s ≤ 0.6** (tight; do not lengthen any tween). The mask/solid path mechanics were tested standalone; the combined function against the real page (node tweens, focus tween, redraw restarts) was **not** run end-to-end → covered by the Validation plan below.
**Why the guard `now - linesT0 > 800` instead of "once per `_seq`":** with the 4 early redraws, "once per seq" would animate the first (soon detached) paths and show the 2nd–4th set fully drawn immediately — the animation would be invisible. With the settle window each early redraw restarts the draw on the new paths (the last restart at ≈407 ms is 60 ms later than the first; negligible). A user-triggered later redraw (window resize, "show more", view switch) never re-animates. Switching tree→timeline for the first time after a load animates (`fresh` stays true until a draw actually happens, because `drawLines()` returns early while the container is hidden, `itinerari.html:1376`).

### Anti-Patterns to Avoid
- **Transform on `.node` (or any element whose rect `drawLines()` reads):** `getBoundingClientRect()` includes transforms, and `drawLines()` fires up to 4× during the first 60 ms → line endpoints would be anchored to a displaced node until the next redraw. Animate children or colour properties only.
- **Animating `opacity` on `.node` / `.tl-lines path` / `.bar-fill` `width`:** the existing CSS transitions (`itinerari.html:380-382`, `observatori.html:153`) smooth every inline change by 150–400 ms and fight the tween. Use properties not in a transition list (`transform`, `stroke-dashoffset`, `background-color`, `border-left-color`) or child elements.
- **`ctx.add()` on the matchMedia context for every event-driven tween:** unbounded retention (see Alternatives).
- **`gsap.context()` with no argument as a "create context" call:** returns the *current* context (undefined outside one) — `TypeError: Cannot read properties of undefined (reading 'add')` (reproduced).
- **`$nextTick` before animating rows:** unnecessary and puts a macrotask boundary before the first tween frame.
- **Setting the start state in HTML/CSS** (e.g. `.row{opacity:0}` or inline `stroke-dashoffset`) — violates D-05; start states must come only from `fromTo(...)` executed by GSAP. (The launch composition sets `p.style.strokeDashoffset = "1"` inline; do not copy that.)
- **`Playwright page.evaluate("…tl.progress(0.3)")`** returns the GSAP timeline object to the serializer and hangs — append `; 0` (hit twice while researching).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reduced-motion switching (OS setting changes while the page is open) | A `matchMedia` listener that kills tweens manually | `gsap.matchMedia().add(query, handler)` returning a cleanup function | Re-runs/reverts on change (gsap.js:3586-3616); tested mid-flight revert |
| Restoring final state when an animation is cut short | Manual `style.opacity = ''` bookkeeping | `context.revert()` (per-run `gsap.context`) + `clearProps` | Reverts exactly the props GSAP touched; verified empty `style` afterwards |
| Counter formatting | Custom number formatter | `Number.prototype.toLocaleString(locale)` — already what `renderBarChart` uses | Keeps identical output to the final text |
| Line drawing | DrawSVG plugin / custom path-length maths | `pathLength="1"` + `strokeDashoffset` (D-13) for solid; userSpaceOnUse mask for dashed | Plugins are out of scope (D-02); the plain technique is 6 lines |
| Detecting "results changed" | Diffing the DOM with MutationObserver | Alpine `$watch` on a signature string + first-10-ids key | Alpine already knows when inputs change; pagination is excluded by construction |

**Key insight:** every hazard in this phase comes from *coexisting* with something that already owns the same property (Alpine x-transition, CSS transitions, Alpine DOM reuse, `drawLines()` measuring, i18n innerHTML). Choose properties and elements nobody else touches, and let `revert()` restore the rest.

## Common Pitfalls

### Pitfall 1: Stale inline styles on Alpine-reused rows
**What goes wrong:** x-for with `:key="row.id"` reuses the DOM node when a row survives a new query; a killed (not reverted) tween leaves `opacity:.4; transform:…` on a node that is then permanently dim/shifted.
**Why:** `killTweensOf` stops the tween but does not undo its inline styles.
**How to avoid:** replace by `revert()` (slot replacement in `GFPMotion.play`) and always set `clearProps`.
**Warning signs:** a row stays at 40 % opacity after fast typing; `style` attribute non-empty on rows when no animation is running (assert in the smoke test).

### Pitfall 2: Triggering on pagination / data load
**What goes wrong:** animating inside `pagedRecords` effects or on `currentPage` changes violates D-08.
**How to avoid:** the signature contains only `search, filterGrado, filterFamilia, filterNivel, filterOld, filterFavs`; `currentPage`, `expandedRows`, `favorites`, `allRecords`, `sortCol/sortDir` are not in it. `$watch` never fires for the initial value, and the initial catalog load changes `allRecords`, not the signature (URL-prefill paths that set filters after load — `veureAlCercador` `index.html:3199-3204`, `applyListState` — are real user navigations and may animate).
**Warning signs:** Playwright check "click page 2 → no inline opacity on rows".

### Pitfall 3: Reading reactive getters with side effects from the watcher
**What goes wrong:** in ocupació mode `filteredRecords` delegates to `ocupMatchedRecords()` which mutates `this.ocupMatchByRec` inside a getter (`index.html:2384-2386`, `3205-3212`); calling `filteredCount` from the watcher in that mode re-runs it.
**How to avoid:** `if (this.searchMode !== 'nom') return;` first (in the example). FPO mode uses a separate table (`pagedFpoEspecs`) and is out of scope.

### Pitfall 4: `pathLength` on dashed paths / masks on horizontal paths
See Pattern 5 — both silently destroy the visible line. Covered by a dedicated assertion in the validation plan (computed `stroke-dasharray` of a `t-part` path after the animation equals `7px, 4px` and no `mask` attribute remains).

### Pitfall 5: Transforms on inline elements and on `drawLines()`-measured nodes
`.ok-tick` must be `inline-block`; `.node` must never carry a transform (Anti-Patterns).

### Pitfall 6: Running tween on a hidden element
The modal watcher fires while the overlay is still `display:none`; harmless (GSAP writes inline transform regardless) but eats ≈30 ms of the first visible frames. Use `delay` or accept.

### Pitfall 7: Script order on observatori
Its inline script calls `load()` at parse time; a `defer` GSAP would load after the fetch resolves on a fast/cached response → `GFPMotion` undefined → no animation (silently). Use plain script tags there.

### Pitfall 8: i18n bump scope
Changing `modal.alert.ok` (Option A) without bumping `i18n.js?v=` leaves cached clients showing "✓ ✓ Alerta…" (old string + new span). Bump `?v=` in `index.html` at minimum.

## Code Examples

The tested/verified patterns are in the Architecture Patterns section above (helper, rows, modal, bars, timeline). Additional load-bearing snippets:

### CLAUDE.md exception line (D-01) — insert before "No afegir-ne cap altre."
```
Excepció acceptada (fase 07): GSAP 3.x (només el core) vendoritzat (`frontend/vendor/gsap-<versió>.min.js`, sense CDN ni plugins), només a `index.html`, `observatori.html` i `itinerari.html`; sempre darrere de `gsap.matchMedia()` (`prefers-reduced-motion`) i amb la pàgina funcionant igual si GSAP no carrega.
```

### Script tags with provenance comment (precedent: `itinerari.html:944-945`)
```html
<!-- GSAP 3.14.2 core (llicència «Standard no-charge», https://gsap.com/standard-license, vigent 2025-04-30/2025-05-30), vendoritzat
     de npm gsap@3.14.2 dist/gsap.min.js — sha256 c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280. No retallar la capçalera. -->
<script defer src="vendor/gsap-3.14.2.min.js"></script>
<script defer src="motion.js?v=1"></script>
<script defer src="vendor/alpinejs-3.15.11.min.js"></script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GSAP free core + paid "Club" plugins (DrawSVG, SplitText…) | Everything free under the "Standard no-charge license" (Webflow) | 3.13.0, 2025-04-30 (license effective date) | DrawSVG would now be legally usable, but D-02/D-13 keep core-only and hand-rolled `pathLength` draws |
| `gsap.matchMedia` condition per breakpoint | Same API also for `prefers-reduced-motion` (official doc example) | — | Matches D-04 |
| GSAP 3.14.2 | GSAP 3.15.0 available | 2026-04-13 | No reason found to move; swap is one file + sha |

**Deprecated/outdated:** none relevant.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vendoring/self-hosting `gsap.min.js` on grausfp.es is permitted: the license grants "use, reproduce, display, and implement … on any website" but never mentions hosting explicitly; this is an inference (web search summary says the same: "my inference, not an explicit statement"). | Standard Stack / License | Low; owner already decided D-02 — if Webflow objected, the fallback is the CDN or a 3.12-era file, both easy swaps. Owner may confirm via Webflow/GSAP contact. |
| A2 | `transform` on `<tr>` renders in Safari and Firefox (only Chromium 156 verified). | Pattern 2 | Rows would not slide (opacity still works); cosmetic. Verify manually in Safari/Firefox at Plan 1 UAT. |
| A3 | Production serves new JS with heuristic caching only: observed `cache-control: no-transform`, `etag`, `content-encoding: gzip`, `content-type: application/javascript` for existing vendor files, no `max-age`/`expires`. First-party `motion.js?v=1` therefore revalidates; the `?v=` mostly future-proofs. | Deploy | Low. Re-check headers on the new files after deploy (`curl -sIL`). |
| A4 | A `$nextTick` (setTimeout) based trigger *could* allow one painted frame before the tween starts. Only the direct-from-`$watch` approach was measured. | Pattern 2 | None if the recommended direct call is used. |
| A5 | Playwright bundled Firefox/WebKit are unavailable; cross-browser automation is not possible without `playwright install` (downloads browsers). | Validation | Cross-browser checks stay manual. |
| A6 | The node light-up visual (background `--path-bg` + left border `--path-ink` fading to current colours) is an interpretation of "stops light up in `--path-ink` green in sequence"; exact look not specified by D-13. | Pattern 5 | Cosmetic; adjust at UAT. |
| A7 | The "Primera parada" highlight is implemented on the existing focus node's inner `.node-main` (no new "Primera parada" text/tag), because adding text would need new CA/ES i18n strings and is a UX addition. | Pattern 5 / Open Questions | If the owner wants the literal tag label, Plan 3 needs two i18n keys + markup. |

## Open Questions

1. **Hero counter `#stat-total` on observatori (`observatori.html:459`)?**
   - Known: D-12 names only "Distribució per grau" bars and counters; the composition counter pattern is also used for totals.
   - Unclear: whether the owner wants the hero total counted up too.
   - Recommendation: out of scope (it is a single `textContent` write after fetch; counting up from 0 would also flash a wrong total to non-AT users). Add only if the owner asks.
2. **Cross-browser `<tr>` transform (Safari/Firefox)?**
   - Recommendation: human UAT step in Plan 1 ("type a search in Safari and Firefox"); fall back to opacity-only if broken.
3. **Where does the browser smoke test live and does it add a dependency?**
   - Known: no frontend test infrastructure exists (only `backend/tests`, pytest); Python Playwright 1.57.0 is installed globally and works with `channel="chrome"` (Chrome 156.0.8078.73 launched OK); bundled browsers are not installed.
   - Recommendation: a standalone `fp-cercador/scripts/motion_smoke.py` (not in `backend/requirements.txt`, not collected by pytest), run manually/at verify-work; the project's "Dependencies — cap altra" line covers runtime deps, and this is a dev script like the existing `scripts/`.
4. **Should sort changes (`sortCol/sortDir`) cascade?** D-08 lists search and filters only → excluded from the signature. Recommendation: keep excluded.
5. **Ocupació/FPO modes:** not in D-08 → no animation there (guarded by `searchMode !== 'nom'`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node / npm | one-off tarball fetch (npm view) | ✓ | node v26.0.0 | `curl` the registry URL (used) |
| `curl`, `shasum`, `gzip` | checksum + size check | ✓ | system | — |
| Google Chrome (system) | Playwright `channel="chrome"` smoke test | ✓ | 156.0.8078.73 | — |
| Python 3.13 + `playwright` (pip) | smoke test | ✓ | playwright 1.57.0 | manual browser checks |
| Playwright bundled chromium/firefox/webkit | cross-browser automation | ✗ (launch fails: executable missing) | — | use `channel="chrome"`; Safari/Firefox manual |
| Flask + flask_cors | optional local backend | ✓ (import OK) | — | route-mock `/api/**` in Playwright (done in experiments; `backend/data/ofertes.json` = same payload as `/api/ofertes`, 12,894 records) |
| Network to gsap.com / npm / jsDelivr | license + file fetch | ✓ | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** bundled Playwright browsers (use system Chrome).

## Validation Architecture

> `workflow.nyquist_validation: true` in `.planning/config.json` (verified) → section required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None for the frontend today (backend: pytest in `backend/tests/`, ~50 files, none touch the DOM). Add a standalone Python-Playwright script (Chrome channel) + shell structural checks. |
| Config file | none — Wave 0 creates `fp-cercador/scripts/motion_smoke.py` |
| Quick run command | structural: the `rg`/`shasum` block below (< 2 s) |
| Full suite command | `python3 -u fp-cercador/scripts/motion_smoke.py` (route-mocked, serves `frontend/` with `python3 -m http.server`; ~15 s) + backend suite unchanged (`reference_backend_tests_gotchas`: ignore scrapers and test_pipeline) |

### Phase Requirements → Test Map
No requirement IDs; mapped to decisions.

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-02/D-03 | Exactly one vendored GSAP file, header intact, hash matches, loaded only by 3 pages | structural | `shasum -a 256 fp-cercador/frontend/vendor/gsap-3.14.2.min.js` = `c174bfce…8cd8280`; `head -8` shows `@license` + `standard-license`; `fd -t f gsap fp-cercador/frontend` = vendor file + `motion.js`; `rg -l "gsap-3.14.2" fp-cercador/frontend/*.html` = index, observatori, itinerari only | ❌ Wave 0 |
| D-01 | CLAUDE.md exception present | structural | `rg -n "GSAP" CLAUDE.md` (1 hit in Tech Stack, before "No afegir-ne cap altre.") | ❌ |
| D-05 | No CDN, no hidden start state, no plugins | structural | `rg -n "cdn.jsdelivr\|unpkg\|gsap.com/.*\.js" fp-cercador/frontend/*.html` (no hit); `rg -n "ScrollTrigger\|DrawSVG\|SplitText\|registerPlugin" fp-cercador/frontend` (no hit); `rg -n "opacity:\s*0\b" fp-cercador/frontend/{index,observatori,itinerari}.html` reviewed (no new start-state rule) | ❌ |
| D-04/D-05 | App works with GSAP blocked | e2e smoke | Playwright `page.route("**/vendor/gsap-*.js", abort)` → rows render, search filters, no `pageerror`, computed opacity of rows = `1` | ❌ Wave 0 |
| D-04 | Reduced motion = final state immediately | e2e smoke | `browser.new_context(reduced_motion="reduce")`: after a search no row has inline `opacity`/`transform` (sample 5× over 400 ms); observatori `.bar-fill` has no transform; itinerari has no `mask`/`pathLength` leftovers | ❌ |
| D-08/D-09/D-10 | Cascade on search/filter only; ≤10 rows; restarts cleanly | e2e smoke | rAF-sample first row after `fill('#search','cocina')` (Spanish term: the mock has no CA→ES expansion): first frame opacity < 1 (≈0.4) and transform ≠ none; all inline styles empty by ≤ 700 ms; click pagination → no inline opacity at any sample; two searches 40 ms apart → clean | ❌ |
| D-07 | Sequence ≤ 600 ms | e2e smoke / dev | rows: last row clean ≤ 600 ms after first animated frame (360 ms nominal); itinerari: all dashoffset/mask/colour inline props gone ≤ 650 ms after first draw | ❌ |
| D-11 | Modal pop, focus intact | e2e smoke | set `Alpine.$data(document.querySelector('[x-data]')).alertModalVisible = true`; assert `document.activeElement.className` contains `centres-modal-close` within 100 ms, box transform returns to `none`, error state (`alertSaveError='x'`) never gets a transform | ❌ |
| D-12 | Final numbers correct mid-animation | e2e smoke | immediately after bars render: `.bar-value` `textContent` equals `${val.toLocaleString(...)} (${pct}%)` (ghost is aria-hidden); `.bar-fill` `style.width` = `${pct}%`; with GSAP blocked identical | ❌ |
| D-13 | Dashed paths keep pattern; no leftovers | e2e smoke | after 800 ms: `getComputedStyle(path.t-part).strokeDasharray` = `7px, 4px`, `t-old` = `1.5px, 4px`; `document.querySelectorAll('.tl-lines mask, .tl-lines path[mask], .tl-lines path[pathLength]').length === 0`; first sample < 400 ms has at least one path with non-zero inline `stroke-dashoffset` or a `mask` | ❌ |
| D-13/D-14 | Line endpoints not displaced by node transforms | e2e smoke | after 1 s compare each path's start/end to node rects (`|Δy| < 1 px`) | ❌ |
| D-15 | Existing guards untouched | structural | `rg -n "prefers-reduced-motion\|reducedMotion\(\)" fp-cercador/frontend/itinerari.html` still shows lines 380 and 967 | ✅ |

Fixtures for the e2e script (proven in this research): `page.route("http://localhost:5001/**", …)` — the frontends call `http://localhost:5001` when `location.hostname === 'localhost'` — answering `/api/ofertes` with `backend/data/ofertes.json` and everything else with `404 {}` plus `access-control-allow-origin: *`; for itinerari answer `/api/itinerari/complet` with a hand-built `{focus, nodes:[{key,grado,codigo,denominacion,familia,nivel,plan_antiguo,ref,id}], edges:[{from,to,kind,shared,total}]}` (A, B, C, D incl. a `part`, a `old` and a straight horizontal edge, E); for observatori `/api/observatory` → `{current:{ts,total,A,B,C,D,E}, series:[…], recent_changes:[]}` (shape read from `observatori.html:451-474`).

### Sampling Rate
- **Per task commit:** structural block (< 2 s) + `python3 -u fp-cercador/scripts/motion_smoke.py -k <page>` for the touched page.
- **Per wave (plan) merge:** full smoke script + manual Safari/Firefox glance (A2).
- **Phase gate:** full smoke green + backend suite unchanged before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `fp-cercador/scripts/motion_smoke.py` — all e2e rows above (Chrome channel, route mocks, local `http.server`)
- [ ] Shell snippet (or Makefile-free script `scripts/check_motion_static.sh`) for the structural rows
- [ ] No framework install needed (Playwright 1.57.0 + Chrome 156 present); do **not** add to `backend/requirements.txt`

## Security Domain

> `security_enforcement` is absent from `.planning/config.json` → treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no auth change) |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | minimal | Itinerari builds DOM with `createElementNS`/`setAttribute` from numbers/`d` strings already produced by `drawLines()`; the mask clone copies the `d` attribute (own data). Observatori ghost uses `textContent` only — never `innerHTML` with API data (the existing `esc()` helper stays for the novetats list). |
| V6 Cryptography | no | Integrity of the vendored file is by pinned sha256 recorded in the repo (no SRI needed for same-origin files) |
| V14 Config / supply chain | yes | Pin exact version + checksum; two independent sources (npm tarball, jsDelivr) agree; no CDN at runtime; no postinstall; no `eval`/`new Function`/network calls in the file |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered third-party script | Tampering | Vendor + checksum, same-origin, `Cache-Control` unchanged; rehash on every upgrade |
| CDN outage / compromise | DoS / Tampering | No CDN (D-01/D-05); page works without GSAP |
| XSS via animated text | Tampering | counters write `textContent` of a number built by `Math.round().toLocaleString()` + static suffix |
| CSP | — | No CSP exists in `deploy/nginx-cloudpanel.conf` (grep: none); same-origin scripts and existing inline scripts need no change |

## Sources

### Primary (HIGH confidence)
- npm registry (`npm view gsap …`, tarball download, `gsd-tools query package-legitimacy check`) — version, dates, shasum, integrity, postinstall, download count
- jsDelivr `gsap@3.14.2/dist/gsap.min.js` — identical sha256/size
- GSAP 3.14.2 `dist/gsap.js` (unminified, from the tarball) — `Context.add` (3649-3669), `Context.kill/revert` (3690-3760), `MatchMedia` (3765-3860), `_onMediaChange` (3586-3616), `gsap.context` (3962-3964), `Animation` constructor context registration (1551)
- Repository files read this session: `07-CONTEXT.md`, `CLAUDE.md` (repo root), `frontend/index.html` (2071-2079, 2196-2345, 2383-2420, 2473-2476, 2510-2560, 2604-2638, 3240-3270, 3330-3360, 3569-3650, 4347-4410), `observatori.html` (120-190, 255-484), `itinerari.html` (290-450, 917-967, 1055-1100, 1126-1264, 1372-1408, 1655-1702), `frontend/i18n.js` (190, 898, 1437-1475), `frontend/vendor/*`, `deploy/nginx-cloudpanel.conf`, `fp-cercador/plans/073-itinerari-graf-cytoscape.md`, launch compositions `a3/a5/a6/a7/b2`
- Local experiments (scratch copy, Chrome 156.0.8078.73 via Playwright 1.57.0, 2026-10-28): helper behaviour (6 scenarios), row cascade timing/`<tr>` transform, modal timing/focus, SVG solid/dashed/mask techniques (pixel comparison + screenshots), itinerari redraw count, ES translation inside the x-if block

### Secondary (MEDIUM confidence)
- https://gsap.com/standard-license (fetched; effective 2025-04-30, modified 2025-05-30) — Permitted/Prohibited Uses, FAQ
- https://gsap.com/docs/v3/GSAP/gsap.matchMedia()/ and https://gsap.com/docs/v3/GSAP/gsap.context()/ (fetched) — signature, `context.add`, event-handler recording, revert semantics
- Live production headers (`curl -sIL https://grausfp.masellas.info/vendor/…` → 301 to `https://grausfp.es/vendor/…`): `application/javascript`, `content-encoding: gzip`, `cache-control: no-transform`, no max-age

### Tertiary (LOW confidence)
- Web search summary on self-hosting ("none of the results addresses self-hosting directly … inference") → A1
- GitHub Releases page for GSAP is empty; 3.15.0 changes not reviewed

## Metadata

**Confidence breakdown:**
- Standard stack / license / file integrity: HIGH — hash cross-checked on two sources, license read from the official page (self-hosting itself is an inference, A1)
- Architecture (helper, Alpine timing, SVG techniques): HIGH for Chromium — each load-bearing claim was reproduced in Chrome 156; MEDIUM for Safari/Firefox (A2)
- Pitfalls: HIGH — most were reproduced (`gsap.context()` no-arg, masked horizontal path, 4× redraw, Playwright serialization hang)
- Timeline end-to-end on the real page and observatori counters: MEDIUM — composed from tested parts, validated by the Wave 0 smoke script

**Research date:** 2026-10-28
**Valid until:** 2026-11-27 (30 days; GSAP/license page are stable, but re-check the license page if upgrading past 3.14.2)
