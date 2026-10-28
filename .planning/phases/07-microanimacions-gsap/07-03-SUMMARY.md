---
phase: 07-microanimacions-gsap
plan: 03
subsystem: ui
tags: [gsap, motion, itinerari, svg-mask, stroke-dashoffset, reduced-motion, playwright-smoke]

requires:
  - phase: 07-01
    provides: vendored GSAP 3.14.2 core, motion.js GFPMotion guard, static checker and smoke harness
  - phase: 07-02
    provides: smoke harness extension pattern and observatori checks
provides:
  - itinerari.html timeline view: connector lines draw A->E segment by segment (pathLength=1 + stroke-dashoffset, no DrawSVG plugin)
  - Dashed (t-part) and dotted (t-old) C->D links draw through a userSpaceOnUse mask that keeps their dash pattern; mask/defs/pathLength removed afterwards
  - Stops light up green (--path-ink) in sequence; focus node (.node-main) rises as the "Primera parada" highlight
  - Smoke checks for itinerari plus static checker extended to itinerari.html
affects: [phase-07-verification]

actuals:
  tokens: 5081
  tasks: 4
  commits: 3
commits: 3
plan_head_before: 4f071a37e7511c950a8762cae90e25af9c401be3
plan_head_after: 114fc60964b34c08669c70e3a64bf120c94f99aa

tech-stack:
  added: []
  patterns:
    - "Segment draw via pathLength=1 + stroke-dashoffset instead of the DrawSVG plugin"
    - "Dashed lines drawn through a runtime-only userSpaceOnUse mask (white clone path) so the dash pattern is untouched"
    - "Early redraws seek the timeline to the elapsed time since linesT0 so the same sequence continues"

key-files:
  created: []
  modified:
    - fp-cercador/frontend/itinerari.html
    - fp-cercador/scripts/motion_smoke.py
    - fp-cercador/scripts/check_motion_static.sh

key-decisions:
  - "D-03/D-07: GSAP core only (vendored), segments start 90 ms apart and last 180 ms each, well under the 600 ms ceiling per element"
  - "D-04/D-05/D-15: reduced motion or blocked GSAP show the final lines and stops at once; existing reducedMotion() helper and CSS guard untouched"
  - "D-06: the focus node highlight adds no new text"
  - "D-13: lines draw via pathLength=1 + dashoffset; dashed/dotted C->D links go through a userSpaceOnUse mask; stops light up green in sequence; Graf (Cytoscape) and tree views unchanged"
  - "D-14: focus node's inner .node-main rises from opacity 0.4 / 10 px; no transform/opacity on .node or .tl-lines path"
  - "D-16: production deploy approved explicitly by the owner (answer `deploy`, 2026-10-28)"

patterns-established:
  - "Runtime-only SVG defs/mask removed on complete/revert, leaving the DOM in its final static state"

requirements-completed: [D-03, D-04, D-05, D-06, D-07, D-13, D-14, D-15, D-16]

duration: multi-session
completed: 2026-10-28
status: complete
---

# Phase 7 Plan 03: GSAP on itinerari.html Summary

**The itinerari timeline now draws its connector lines A->E segment by segment (dashed and dotted C->D links through a pattern-preserving SVG mask), lights stops up green in sequence and raises the focus node, with Graf and tree views untouched; deployed to production after explicit owner approval.**

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Tracer: solid connectors draw segment by segment | 43b547e |
| 2 | Dashed/dotted C->D connectors draw through userSpaceOnUse mask | e5ae04b |
| 3 | Stops light green in sequence + focus node rise | 114fc60 |
| 4 | Owner review + production deploy (checkpoint:human-verify, gate blocking-human) | no code commit |

## Task 4: owner review and deploy

- Owner answer: `deploy` (2026-10-28), approving the production deploy.
- Safari/Firefox result: not reported by owner. The clip-path wipe fallback was therefore not used and remains unimplemented.
- Local servers (API stub on 5001, http.server on 8080) stopped by port; both ports confirmed free.
- Deploy: `git push cercador-grausfp master` (4f071a3..114fc60), then on the VPS `git status --short` showed only the expected untracked `fp-cercador/backend/scrapers/old_pdf_scraper.py`, `fp-cercador/frontend/video/` and `venv/`, and `git pull --ff-only` fast-forwarded (itinerari.html +82, motion_smoke.py, check_motion_static.sh, 07-02 docs). Frontend-only, no restart. VPS HEAD: 114fc60.
- Post-deploy check:

```
$ curl -sL https://grausfp.es/itinerari.html | rg -c 'motion.js\?v=1'
1
$ curl -sL https://grausfp.masellas.info/itinerari.html | rg -c 'motion.js\?v=1'
1
```

## Deviations from Plan

**1. [Process] Commits made directly on master**
- The three task commits live on `master` (no phase branch), consistent with the sequential execution mode this plan was dispatched in.

**2. [Environment] Local review used a stubbed API**
- Local data lacks the C->D edge sources (missing `d_modulos.json`, `ciclos_fp.json`, `bc_lomloe.json`), so the real backend could not return an itinerary with C->D links of all three strengths. The owner review used a temporary stub API on port 5001 serving a fixture (A, B, C focus, three D full/part/old, E). The stub was not part of tracked files.

No other deviations; plan otherwise executed as written.

## Known Stubs

None. (The review-time API stub was temporary and not committed.)

## Threat Flags

None. No new network endpoints, auth paths or schema changes; frontend-only animation on an already-vendored library.

## Self-Check: PASSED

- FOUND: 43b547e, e5ae04b, 114fc60 (ancestors of HEAD)
- FOUND: fp-cercador/frontend/itinerari.html, fp-cercador/scripts/motion_smoke.py, fp-cercador/scripts/check_motion_static.sh
- Measured commits: 3 (`git rev-list --count 4f071a3..HEAD`)
