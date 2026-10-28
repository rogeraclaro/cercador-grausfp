---
phase: 07-microanimacions-gsap
plan: 02
subsystem: ui
tags: [gsap, motion, observatori, count-up, reduced-motion, playwright-smoke]

requires:
  - phase: 07-01
    provides: vendored GSAP 3.14.2 core, motion.js GFPMotion guard, static checker and smoke harness
provides:
  - observatori.html "Distribucio per grau": bars grow from the left (scaleX), values count up through an aria-hidden copy
  - Smoke checks for reduced motion and blocked GSAP on observatori.html; static checker extended to observatori.html
affects: [07-03, itinerari]

actuals:
  tokens: 3440
  tasks: 3
  commits: 2
plan_head_before: cef38cbc1c15a70956d9959e8f16a26961e20a0c
plan_head_after: 83341077a3cc306fef47a57517b02f04d3db03ff
commits: 2

tech-stack:
  added: []
  patterns:
    - "Count-up writes into an aria-hidden copy; the real accessible text stays final at all times"
    - "Counting copy written with textContent only, never an HTML-parsing API"

key-files:
  created: []
  modified:
    - fp-cercador/frontend/observatori.html
    - fp-cercador/scripts/motion_smoke.py
    - fp-cercador/scripts/check_motion_static.sh

key-decisions:
  - "Bars animate with scaleX (compositor-friendly), 410 ms total, within the D-07 600 ms ceiling"
  - "Hero total (#stat-total) left untouched (owner default 1); only the per-grade bars and values animate"
  - "Final widths and numbers live in the markup, so reduced motion or blocked GSAP show the finished chart at once (D-04, D-05, D-06)"
  - "Production deploy approved explicitly by the owner (D-16): answer `deploy`, 2026-10-28"

patterns-established:
  - "aria-hidden counting copy beside the real text for screen-reader-safe count-ups"

requirements-completed: [D-03, D-04, D-05, D-06, D-07, D-12, D-16]

duration: multi-session
completed: 2026-10-28
status: complete
---

# Phase 7 Plan 02: GSAP on observatori.html Summary

**The observatori "Distribucio per grau" bars now grow from the left in 410 ms while the values count up through an aria-hidden copy, with final numbers always present in the DOM; deployed to production after explicit owner approval.**

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Tracer: bars grow (script tags, animateBars scaleX, smoke check, static checker) | 40240cc |
| 2 | Count-up via aria-hidden copy; reduced-motion and no-GSAP checks | 8334107 |
| 3 | Owner review and production deploy (checkpoint:human-verify, blocking-human) | no code commit; owner answered `deploy` |

## Deploy and verification (Task 3)

Owner answer: `deploy` (2026-10-28). Local servers on 5001 and 8080 were stopped and confirmed free before deploying.

- `git push cercador-grausfp master`: `cef38cb..8334107  master -> master`
- VPS `git status --short` before pull showed only the expected untracked items (`old_pdf_scraper.py`, `frontend/video/`, `venv/`).
- VPS `git pull --ff-only`: fast-forward `4a3f9d2..8334107`; no restart (frontend only).
- Post-deploy checks:

```
$ curl -sL https://grausfp.es/observatori.html | rg -c 'motion.js\?v=1'
1
$ curl -sL https://grausfp.masellas.info/observatori.html | rg -c 'motion.js\?v=1'
1
$ curl -sL https://grausfp.es/observatori.html | rg -c 'gsap-3.14.2.min.js'
1
```

## Deviations from Plan

### Auto-fixed Issues

None - code tasks executed as written.

### Process notes

**1. Commits made directly on master** (same as 07-01), not on a feature branch.

**2. Limited local visual review.** The local observatory database held test values (`current.total` = 1, A = B = 50), so the owner's local review of the bar growth was limited. The owner approved the deploy on that basis.

## Threat Model

- T-07-SC: no new package or download; vendored GSAP reused, sha256 re-verified by the static checker.
- T-07-06: counting copy written with `textContent` only; no HTML-parsing APIs in `animateBars`.
- T-07-07: guarded `GFPMotion` call with optional chaining; reduced-motion and blocked-GSAP smoke checks pass.

## Known Stubs

None.

## Self-Check: PASSED

- 40240cc and 8334107 present on master; `git rev-list --count cef38cb..HEAD` = 2 before this docs commit.
- `observatori.html`, `motion_smoke.py`, `check_motion_static.sh` modified as listed.
- Production serves `motion.js?v=1` on observatori.html.
