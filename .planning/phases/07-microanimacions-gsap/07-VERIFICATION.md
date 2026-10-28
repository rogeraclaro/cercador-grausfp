---
phase: 07-microanimacions-gsap
verified: 2026-10-28T19:00:00Z
status: human_needed
score: 14/14 must-haves verified
covered_files:
  - ".planning/phases/07-microanimacions-gsap/07-01-PLAN.md"
  - ".planning/phases/07-microanimacions-gsap/07-01-SUMMARY.md"
  - ".planning/phases/07-microanimacions-gsap/07-02-PLAN.md"
  - ".planning/phases/07-microanimacions-gsap/07-02-SUMMARY.md"
  - ".planning/phases/07-microanimacions-gsap/07-03-PLAN.md"
  - ".planning/phases/07-microanimacions-gsap/07-03-SUMMARY.md"
  - "CLAUDE.md"
  - "fp-cercador/frontend/i18n.js"
  - "fp-cercador/frontend/index.html"
  - "fp-cercador/frontend/itinerari.html"
  - "fp-cercador/frontend/motion.js"
  - "fp-cercador/frontend/observatori.html"
  - "fp-cercador/frontend/vendor/gsap-3.14.2.min.js"
  - "fp-cercador/scripts/check_motion_static.sh"
  - "fp-cercador/scripts/motion_smoke.py"
covered_digest: "v4:sha256:ece386ec96c0a7738ba8782bf0a03de2ff36ee395bb66bec9fafce309876db5b"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open itinerari.html (timeline view) in Safari (macOS and iOS) and Firefox with an itinerary that has full, partial (t-part, dashed) and old (t-old, dotted) C->D links"
    expected: "Solid lines draw A->E; dashed and dotted C->D links reveal progressively through the SVG mask and keep their dash pattern during and after the draw; no link stays invisible; stops light up green in sequence"
    why_human: "The dashed/dotted draw relies on an SVG <mask maskUnits=userSpaceOnUse> with a pathLength=1 dashoffset clone. The automated smoke suite runs in system Chrome only. The owner did not report Safari/Firefox results (07-03-SUMMARY), and the planned clip-path fallback was never implemented, so a WebKit/Gecko mask-rendering difference would leave dashed links permanently hidden."
  - test: "Load observatori.html in production with real data (more than one record, grades with clearly different percentages) in Chrome, Safari and Firefox"
    expected: "The five 'Distribucio per grau' bars grow from the left in about 0.4 s, values count up to the exact final number, no flicker or overlap of the real and counting text, final widths match the data"
    why_human: "The owner's local review used a test database (total = 1, A = B = 50), so the visual quality of the growth and count-up on realistic data was never reviewed. The smoke suite uses a route-mocked fixture."
  - test: "In a Windows High Contrast / forced-colors browser, load observatori.html"
    expected: "No double or overlapping numbers on the bar values during the roughly 0.3 s animation (review IN-01)"
    why_human: "The real .bar-value text is hidden with color: transparent while an aria-hidden copy counts. Forced-colors mode overrides color, so both texts may show briefly. Cannot be checked with the available Chrome automation."
---

# Phase 7: Microanimacions GSAP Verification Report

**Phase Goal:** GSAP-driven micro-animations (vendored core, reduced-motion aware, no-GSAP fallback) on index.html, observatori.html and itinerari.html that never delay results or interaction
**Verified:** 2026-10-28
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

ROADMAP.md lists no Success Criteria for this phase (goal only, "Requirements: none assigned"). The must-haves are therefore the merged `must_haves.truths` of the three PLAN files, checked against the CONTEXT decisions D-01..D-16. The code was read directly; SUMMARY claims were not used as evidence.

### Observable Truths

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | GSAP 3.14.2 core is vendored unmodified, with its license header, and no CDN or plugin is used (D-01, D-02, D-03) | VERIFIED | `frontend/vendor/gsap-3.14.2.min.js` sha256 is `c174bfce...8280`, which equals the plan's expected hash. The `@license Copyright 2025, GreenSock` header is present. Static checks `vendor-hash`, `vendor-header`, `single-vendor-file`, `no-remote-gsap` and `no-plugins` pass. Production serves a byte-identical file (re-downloaded to a file and compared with `cmp`: identical). |
| 2  | Only index, observatori and itinerari load GSAP; naming follows `<lib>-<semver>.min.js` (D-03) | VERIFIED | `rg` shows gsap and `motion.js?v=1` tags in exactly those three pages. Static checks `allowed-pages-only` and `load-order:*` pass. |
| 3  | CLAUDE.md Tech Stack lists the GSAP exception (vendored, no CDN or plugins, only on the three pages, behind matchMedia, works without GSAP) before "No afegir-ne cap altre." (D-01) | VERIFIED | `CLAUDE.md` line 12 contains the "Excepció acceptada (fase 07): GSAP 3.x ..." text. Static check `claude-md-exception` passes. |
| 4  | All animation runs behind `gsap.matchMedia()` with `(prefers-reduced-motion: no-preference)`; with reduced motion or blocked GSAP there are no inline styles, no errors, and `GFPMotion.play` returns false (D-04, D-05) | VERIFIED | `motion.js` sets `enabled` only inside the matchMedia handler and `play()` returns false otherwise. Pages call `window.GFPMotion?.play`. Smoke checks `index:/observatori:/itinerari: reduced-motion` and `gsap-blocked` all PASS (re-run by the verifier: 21 passed, 0 failed). |
| 5  | No content starts hidden waiting for GSAP (D-05, D-06) | VERIFIED | Static check `no-hidden-start-state` passes. The code starts rows at opacity 0.4 (never 0), uses `clearProps`, and writes the final text and widths in the markup. The review notes the regex is a heuristic (IN-03); the smoke tests are the stronger evidence. |
| 6  | Typing a search (after the 250 ms debounce) or changing a filter in name mode cascades the first <= 10 rows, opacity 0.4 to 1 and y 8 px to 0, 180 ms `expo.out`, 20 ms stagger (about 360 ms total) (D-07, D-08, D-09) | VERIFIED | `index.html:2246-2256` implements exactly these values (`fromTo` opacity 0.4/y 8, duration 0.18, stagger 0.02, `slice(0,10)`). Smoke `index:rows-cascade` PASS (budget 650 ms). |
| 7  | Pagination, expand/collapse, favourites, sorting and initial load never start a cascade; a new query reverts the running cascade and leaves no inline style (D-08, D-10) | VERIFIED | The `$watch` is keyed on search/filter signature only and de-duplicates via `rowsKey`. `GFPMotion.play` reverts the slot before restarting. Smoke `index:no-cascade-on-load`, `index:no-cascade-on-pagination` and `index:restart-clean` PASS. These exercise the behaviour, not only symbol presence. |
| 8  | The success alert modal keeps its centred modal and focus handling; the box scales 0.96 to 1 and a green aria-hidden check pops (`back.out`, 200 ms); the error state is untouched (D-11) | VERIFIED | `index.html:2259-2268` (scale 0.96 to 1, `expo.out` 0.2 s; tick `back.out(2)` 0.2 s) guarded by `!this.alertSaveError`. The markup at line 4394-4399 keeps `.centres-modal` and adds `<span class="ok-tick" aria-hidden="true">`. Smoke `index:modal-pop` and `index:modal-error-untouched` PASS. |
| 9  | observatori: the five bars grow from the left and values count up, within the 600 ms limit (D-07, D-12) | VERIFIED | `animateBars` (`observatori.html:372-406`): `scaleX` 0 to 1 at 0.25 s, 0.04 s offset per bar, count tween 0.25 s. Total about 0.41 s. Smoke `observatori:bars-grow` PASS. |
| 10 | Final numbers are correct in the DOM and accessibility tree from the first frame; the counting copy is `aria-hidden` and written with `textContent` only; the hero `#stat-total` is untouched (D-12, D-06) | VERIFIED | Final text and width are written by `renderBarChart` before animation. The ghost span has `aria-hidden` and is filled by `textContent`. Smoke `observatori:final-text` PASS. A forced-colors edge case is listed as human item 3. |
| 11 | itinerari: connector lines draw A to E segment by segment through `pathLength=1` plus `strokeDashoffset`, with no DrawSVG; the sequence is at most 600 ms even with several early `drawLines()` redraws (D-07, D-13) | VERIFIED | `animateTimeline` (`itinerari.html:970-1043`): STEP 0.09, DUR 0.18, so the last segment ends about 0.558 s. `tl.time(...)` seeks to the elapsed time on an early redraw. Smoke `itinerari:solid-draw`, `itinerari:restart-keeps-t0` and `itinerari:no-reanimate` PASS. Caveat: the span assertion has only about 59 ms of margin (review WR-02). |
| 12 | Dashed (`t-part`) and dotted (`t-old`) C to D links keep their dash pattern during and after the draw; afterwards no mask, defs, `pathLength` or inline dash property remains (D-13) | VERIFIED (Chromium only) | Mask with `maskUnits=userSpaceOnUse` and a white clone path is used; `cleanup` removes `pathLength`, `mask` and `defs`. Smoke `itinerari:dashed-preserved` PASS in system Chrome. Safari/Firefox are not covered (human item 1). |
| 13 | Stops light up green (`--path-ink`) in sequence and the focus node's `.node-main` rises as "Primera parada"; `.node` itself never receives transform or opacity, so line endpoints stay aligned; no new text (D-13, D-14, D-06) | VERIFIED | Code uses `backgroundColor` and `borderLeftColor` only on `.node`, and `opacity`/`y` on `.node.is-focus .node-main`. Smoke `itinerari:stops-light`, `itinerari:first-stop` and `itinerari:endpoints-aligned` PASS. |
| 14 | Graf (Cytoscape) and tree views are unchanged; the existing reduced-motion CSS guard and `reducedMotion()` helper are kept (D-13, D-15) | VERIFIED | The `itinerari.html` diff for 07-03 is 82 insertions and 0 deletions (purely additive). `@media (prefers-reduced-motion: no-preference)` (line 380) and `reducedMotion()` (line 970) are still present. Static check `d15-guards` passes. |

**Score:** 14/14 truths verified (0 present, behavior-unverified). One truth (12) is verified in Chromium only and carries a human item.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `fp-cercador/frontend/vendor/gsap-3.14.2.min.js` | GSAP core, unmodified | VERIFIED | 72,779 bytes, hash matches, license header intact. |
| `fp-cercador/frontend/motion.js` | `GFPMotion.play/stop` guard | VERIFIED | 40 lines, substantive; loaded by all three pages after GSAP. |
| `fp-cercador/frontend/index.html` | Rows cascade and modal pop | VERIFIED | Wired through `$watch` in `init()`. |
| `fp-cercador/frontend/observatori.html` | `animateBars` | VERIFIED | Called from `load()` at line 513 right after `renderBarChart`. |
| `fp-cercador/frontend/itinerari.html` | `animateTimeline` | VERIFIED | Called at the end of `drawLines()`. |
| `fp-cercador/frontend/i18n.js` | `modal.alert.ok` without the leading tick | VERIFIED | Static check `i18n-tick` passes. |
| `fp-cercador/scripts/motion_smoke.py`, `check_motion_static.sh` | Automated evidence | VERIFIED | Both run green. |
| `CLAUDE.md` | GSAP exception | VERIFIED | Line 12. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| index.html tags | vendor gsap file | `defer` script before `motion.js` and Alpine | WIRED | Lines 3289-3290; static `load-order:index` OK. |
| index `init()` | `GFPMotion.play('rows')` | `$watch` on search/filter signature | WIRED | Line 2250. |
| observatori `load()` | `GFPMotion.play('bars', animateBars)` | Called after `renderBarChart` | WIRED | Line 513; plain (non-deferred) tags at lines 337-338. |
| itinerari `drawLines()` | `animateTimeline(this)` | Call after `paintLines()` | WIRED | Line 981 inside `animateTimeline`; the smoke tests confirm it runs on load. |
| animateTimeline early redraw | `linesT0` | `tl.time(...)` as the final builder step | WIRED | Line 1040; `itinerari:restart-keeps-t0` PASS. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| observatori bar-value | `data-n`, `data-suffix` | API `current` data rendered by `renderBarChart` | Yes (values come from the API response; the animation only displays them) | FLOWING |
| index rows | `pagedRecords` | existing catalogue fetch | Yes (animation acts on rows already rendered by Alpine) | FLOWING |
| itinerari paths | `vm.byKey` and `drawLines()` | existing itinerary API | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Structural checks (hash, header, load order, no CDN or plugins, D-15 guards, CLAUDE.md) | `bash fp-cercador/scripts/check_motion_static.sh` | 15 ok, 0 failed | PASS |
| End-to-end motion behaviour on all three pages, including reduced-motion and blocked-GSAP variants | `python3 -u fp-cercador/scripts/motion_smoke.py` | 21 passed, 0 failed (the script serves the frontend on an ephemeral port and mocks the API, so no local servers were started and no ports needed stopping) | PASS |
| Production serves the vendored file and updated pages | `curl` to https://grausfp.es | Vendor file byte-identical to local (`cmp`); `motion.js?v=1` present on index, observatori, itinerari; `animateTimeline` served | PASS |

### Probe Execution

SKIPPED: the phase declares no `scripts/*/tests/probe-*.sh` probes. The smoke and static scripts above serve that purpose.

### Requirements Coverage

No REQUIREMENTS.md IDs are assigned to this phase (ROADMAP: "none assigned"). The plans declare CONTEXT decision IDs D-01..D-16, checked against `07-CONTEXT.md`.

| Decision | Source Plan | Description | Status | Evidence |
| -------- | ----------- | ----------- | ------ | -------- |
| D-01, D-02, D-03 | 07-01 (D-03 also 07-02, 07-03) | Dependency exception, vendored core, scoped loading | SATISFIED | Truths 1-3. |
| D-04, D-05, D-06 | 07-01, 07-02, 07-03 | matchMedia gate, no-GSAP fallback, never gating content | SATISFIED | Truths 4, 5. |
| D-07 | 07-01, 07-02, 07-03 | 150-250 ms per tween, 600 ms per sequence | SATISFIED | Truths 6, 9, 11. |
| D-08, D-09, D-10 | 07-01 | Rows cascade triggers, scope and restart | SATISFIED | Truths 6, 7. |
| D-11 | 07-01 | Alert modal scale and check pop | SATISFIED | Truth 8. |
| D-12 | 07-02 | observatori bars and counters | SATISFIED | Truths 9, 10. |
| D-13, D-14, D-15 | 07-03 | itinerari timeline draw, first stop, reduced-motion consistency | SATISFIED (Chromium); cross-browser pending | Truths 11-14, human item 1. |
| D-16 | 07-01, 07-02, 07-03 | One phase, three plans, each deployed separately | SATISFIED | Three plans, each with its own deploy commit range. |

No ORPHANED requirements: REQUIREMENTS.md contains no Phase 7 entries.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `frontend/motion.js` | 31-34 | WR-01 (from 07-REVIEW): if a builder throws after mutating the DOM, `play()` swallows the error and never registers the builder's cleanup, so only tweens are reverted. In `animateTimeline` the dashed paths could stay masked (invisible); in `animateBars` the value text could stay transparent. | Warning | Not triggered by any current code path (no concrete throw found), so it does not fail a truth. It is a latent violation of the "page behaves as before if the animation fails" contract. Recommend fixing before the next change to a builder. |
| `fp-cercador/scripts/motion_smoke.py` | 501 | WR-02: the itinerari span budget (617 ms) leaves about 59 ms of margin against a 558 ms sequence, so it may flake under load. | Warning | Test robustness only. Passed in the verifier's run. |
| `frontend/observatori.html` | 392-393 | IN-01: `color: transparent` hiding is overridden by forced-colors mode. | Info | See human item 3. |
| `scripts/check_motion_static.sh` | 98 | IN-03: the `no-hidden-start-state` regex is narrow. | Info | The smoke tests carry the real evidence. |
| `scripts/motion_smoke.py` | 22, 95, 781-789 | IN-02: missing-playwright exits 1 instead of 2, and browser contexts are not closed per check. | Info | Tooling only. |

The debt-marker scan (TBD/FIXME/XXX) over the phase's changed implementation files was not separately run. The reviewed diff and the code read here showed none.

### Human Verification Required

#### 1. Safari and Firefox rendering of the itinerari dashed/dotted mask

**Test:** Open the itinerari timeline in Safari (macOS and iOS) and Firefox with an itinerary containing full, partial (dashed) and old (dotted) C to D links.
**Expected:** Solid lines draw A to E; dashed and dotted links reveal progressively through the mask and keep their dash pattern during and after the draw; no link stays invisible; stops light green in sequence.
**Why human:** Only system Chrome is automated. The owner did not report Safari/Firefox results, and the clip-path fallback was never built, so an engine difference in SVG mask rendering could leave dashed links hidden.

#### 2. observatori with real production data

**Test:** Load observatori.html on the live site in Chrome, Safari and Firefox.
**Expected:** Bars grow from the left in about 0.4 s, counters land on the exact final values, no flicker or overlapping text.
**Why human:** The owner's local review used test data (total = 1, A = B = 50), and the smoke fixture is mocked.

#### 3. Forced-colors / High Contrast on observatori

**Test:** Load observatori.html with Windows High Contrast (forced-colors) active.
**Expected:** No doubled numbers on the bar values during the animation.
**Why human:** `color: transparent` is overridden in forced-colors mode (review IN-01), and this cannot be driven from the available automation.

### Gaps Summary

No gaps. All 14 must-have truths are backed by code that was read directly, by the 15 static checks, and by the 21 end-to-end smoke checks that the verifier re-ran. Those smoke checks exercise the behaviour-dependent truths (cascade restart, no cascade on pagination or load, dashed pattern preserved, sequence span, reduced-motion, blocked GSAP), so none is left at present-but-unverified.

The phase is marked `human_needed` rather than `passed` because the SVG-mask draw for dashed/dotted links has only been proven in Chromium, and the owner's Safari/Firefox observations were never reported. Observatori was also reviewed only on near-empty test data. These are cross-browser and visual checks, not suspected defects. The two review warnings (WR-01, WR-02) are non-blocking hardening items.

One process note: a single `curl | shasum` run on the production vendor file printed an unexpected hash (`4bd3b9e6...`) on its first attempt. Two later runs, one downloading to a file and comparing byte-for-byte with `cmp`, matched the vendored file exactly. The size was also identical (72,779 bytes), so the first output is attributed to the shell's output filtering and not to the server.

---

_Verified: 2026-10-28_
_Verifier: Claude (gsd-verifier)_
