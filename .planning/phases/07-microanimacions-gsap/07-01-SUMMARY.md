---
phase: 07-microanimacions-gsap
plan: 01
subsystem: ui
tags: [gsap, motion, alpine, microanimations, playwright-smoke]

requires:
  - phase: 06
    provides: index.html Alpine cercador component, i18n.js, modal alert markup
provides:
  - GSAP 3.14.2 core vendored at fp-cercador/frontend/vendor/ (unmodified, license header intact)
  - motion.js GFPMotion guard (reduced-motion gate, named slots, no-op without GSAP)
  - Row cascade on search/filter change and alert-modal box scale + green check pop on index.html
  - Static checker and Playwright smoke harness for motion
affects: [07-02, 07-03, observatori, itinerari]

actuals:
  tokens: 26450
  tasks: 5
  commits: 4
plan_head_before: cb8b1754b325f34ad8882ae8563f2741468047d7
plan_head_after: 4a3f9d22247bf745a7995e587beee4560314682f
commits: 4

tech-stack:
  added: ["GSAP 3.14.2 core (vendored, no plugins, no CDN)"]
  patterns:
    - "GFPMotion.play(slot, builder): guarded, one gsap.context per slot, reverts on re-run"
    - "Callers use optional chaining (GFPMotion?.play) so a missing/blocked GSAP leaves the page unchanged"

key-files:
  created:
    - fp-cercador/frontend/vendor/gsap-3.14.2.min.js
    - fp-cercador/frontend/motion.js
    - fp-cercador/scripts/motion_smoke.py
    - fp-cercador/scripts/check_motion_static.sh
  modified:
    - fp-cercador/frontend/index.html
    - fp-cercador/frontend/i18n.js
    - CLAUDE.md

key-decisions:
  - "GSAP license decision (Task 1): owner answered `vendor-3142` on 2026-10-28 -- vendor GSAP 3.14.2 core unmodified under the GreenSock standard license"
  - "Cascade limited to first 10 rows, 360 ms, from opacity 0.4 / 8 px; only on search/filter changes in name mode"
  - "Reduced motion or blocked GSAP: no inline styles, behaviour identical to before"

patterns-established:
  - "Motion guard module (motion.js) loaded before Alpine; pages never reference gsap directly"
  - "Static check re-verifies vendored file sha256 on every run"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-16]

duration: multi-session
completed: 2026-10-28
status: complete
---

# Phase 7 Plan 01: GSAP tracer on index.html Summary

**GSAP 3.14.2 core vendored with a reduced-motion/no-GSAP-safe `motion.js` guard, driving a 360 ms row cascade on search/filter and an alert-modal scale plus green check pop on index.html, deployed to production.**

## Performance

- **Duration:** several sessions (tasks 1-4b in earlier sessions; Task 5 deploy 2026-10-28)
- **Tasks:** 5/5 (Task 1 decision, Tasks 2-4b implementation, Task 5 owner approval + deploy)
- **Files changed:** 7 (601 insertions, 7 deletions)

## Accomplishments

- Vendored `gsap-3.14.2.min.js` byte-identical to npm gsap@3.14.2 (sha256 `c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280`).
- `motion.js` exposes `GFPMotion.play/stop`; no-op when GSAP is missing or reduced motion is on.
- index.html: rows cascade (first 10, 360 ms) only on search/filter changes; alert modal success box scales 0.96 to 1 with a green aria-hidden check pop; error variant untouched.
- CLAUDE.md Tech Stack records the GSAP exception.
- `check_motion_static.sh` and `motion_smoke.py` (8 index checks, including `index:reduced-motion` and `index:gsap-blocked`) green.
- Backend untouched (`git diff --stat cb8b175..HEAD -- fp-cercador/backend` empty).

## Task Commits

1. Task 1: GSAP license decision (`vendor-3142`, 2026-10-28) -- no commit
2. Task 2 (tracer): `2869bbf` feat(index): GSAP 3.14.2 vendoritzat, guarda motion.js i cascada de files en cercar
3. Task 3: `4fbfa52` feat(index): entrada del modal d'alerta desada i check verd
4. Task 4a: `487e4a2` docs(claude): excepcio GSAP a Tech Stack
5. Task 4b: `4a3f9d2` test(motion): proves de fum de l'index i comprovacio estatica
6. Task 5: owner answered `deploy` (2026-10-28); production deploy below.

## Task 5: Owner review and production deploy

Owner answer recorded: `deploy`.

Local servers (ports 5001, 8080) stopped by port; both confirmed free.

Deploy (frontend-only, no service restart):

```
$ git push cercador-grausfp master
   b34a111..4a3f9d2  master -> master

$ ssh contabo 'cd /home/masellas-grausfp/htdocs/grausfp.masellas.info && git status --short && git pull --ff-only'
?? fp-cercador/backend/scrapers/old_pdf_scraper.py   (pre-existing untracked on VPS)
?? fp-cercador/frontend/video/                        (pre-existing untracked on VPS)
?? venv/                                              (pre-existing untracked on VPS)
... 16 files changed, 2449 insertions(+), 16 deletions(-)  (fast-forward; created motion.js, vendor/gsap-3.14.2.min.js, scripts)
```

No tracked local changes on the VPS; pull was fast-forward.

Post-deploy checks (A3, T-07-SC) against https://grausfp.es:

```
$ curl -sIL https://grausfp.es/vendor/gsap-3.14.2.min.js
HTTP/2 200
content-type: application/javascript

$ curl -sL https://grausfp.es/vendor/gsap-3.14.2.min.js | shasum -a 256
c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280  -

$ curl -sL https://grausfp.es/index.html | rg -c 'motion.js\?v=1'
1
```

All three match the expected values; the served file hash equals the vendored hash (supply-chain check passed).

## Decisions Made

- 2026-10-28: owner chose `vendor-3142` for the GSAP license decision (Task 1).
- 2026-10-28: owner approved production deploy (`deploy`).

## Deviations from Plan

**1. [Process] Commits made directly on protected-branch `master`**
- Project convention is to deploy from master (push to `cercador-grausfp master`, pull on the VPS); no feature branch is used.

**2. [Rule 3 - Blocking] motion.js comment rewording**
- Comments in `motion.js` were reworded so the plan's acceptance greps (e.g. forbidden-token checks) do not match prose. No behavioural change. Commit: `2869bbf`.

**3. [Rule 3 - Blocking] `check_motion_static.sh` runs `rg` from inside `frontend/`**
- The repo path contains a space ("Cercador Graus"); running `rg` from `frontend/` avoids path-quoting failures. Commit: `4a3f9d2`.

The in-browser manual review (Chrome/Safari/Firefox, reduced motion) is the owner's step; the owner's `deploy` answer is the recorded approval. Safari/Firefox slide-vs-fade observations (research A2) were not reported as issues.

## Auth Gates

None.

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, auth paths or schema changes; the only new third-party surface (vendored GSAP) is covered by T-07-SC and verified by sha256 locally and post-deploy.

## Self-Check: PASSED

- Commits `2869bbf`, `4fbfa52`, `487e4a2`, `4a3f9d2` are ancestors of HEAD; `git rev-list --count` from plan start = 4.
- Created files exist on disk and on the VPS (`motion.js`, `vendor/gsap-3.14.2.min.js`, both scripts).
- Post-deploy curl checks match expected output.
