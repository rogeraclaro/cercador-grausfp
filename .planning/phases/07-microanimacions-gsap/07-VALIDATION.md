---
phase: "7"
slug: "microanimacions-gsap"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-28"
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `07-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python Playwright 1.57.0 (system Chrome, `channel="chrome"`) standalone script + shell structural checks; no frontend framework exists |
| **Config file** | none — Wave 0 creates `fp-cercador/scripts/motion_smoke.py` and `fp-cercador/scripts/check_motion_static.sh` |
| **Quick run command** | `bash fp-cercador/scripts/check_motion_static.sh` |
| **Full suite command** | `python3 -u fp-cercador/scripts/motion_smoke.py` (route-mocked, local `http.server`) |
| **Estimated runtime** | quick < 2 s; full ~15 s |

---

## Sampling Rate

- **After every task commit:** quick structural check + `python3 -u fp-cercador/scripts/motion_smoke.py -k <page>` for the touched page
- **After every plan wave:** full smoke + manual Safari/Firefox glance (research A2)
- **Before `/gsd-verify-work`:** full smoke green, backend suite unchanged
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

Filled by the planner per task; decision → test mapping:

| Plan-Task | Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|-----------|----------|----------|-----------|-------------------|-------------|--------|
| 07-01-T2 | D-02/D-08/D-09 | Vendored hash; first ≤10 rows cascade ≤ 600 ms on search | structural + e2e | `shasum -a 256 …gsap-3.14.2.min.js` + `motion_smoke.py -k index:rows-cascade` | created in T2 | ⬜ pending |
| 07-01-T3 | D-11 | Modal pop, focus intact, error state untouched | e2e smoke | `motion_smoke.py -k index:` (`index:modal-pop`, `index:modal-error-untouched`) | ✅ (T2) | ⬜ pending |
| 07-01-T4 | D-01/D-02/D-03/D-05 | CLAUDE.md exception; hash/header; allowed pages; no CDN/plugins/start state | structural | `bash fp-cercador/scripts/check_motion_static.sh` | created in T4 | ⬜ pending |
| 07-01-T4 | D-04/D-05/D-08/D-10 | Reduced motion, GSAP blocked, no cascade on load/pagination, clean restart | e2e smoke | `motion_smoke.py -k index:` (8 checks) | ✅ (T2) | ⬜ pending |
| 07-02-T1 | D-12/D-07/D-03 | Bars grow (scaleX) ≤ 600 ms; plain tags before inline script | e2e + structural | `motion_smoke.py -k observatori:bars-grow` + static | ✅ | ⬜ pending |
| 07-02-T2 | D-12/D-04/D-05/D-06 | Final numbers correct mid-animation; reduced/blocked final at once | e2e smoke | `motion_smoke.py -k observatori:` (4 checks) | ✅ | ⬜ pending |
| 07-03-T1 | D-13/D-03 | Solid segments draw A→E; deferred tags before Alpine | e2e + structural | `motion_smoke.py -k itinerari:solid-draw` + static | ✅ | ⬜ pending |
| 07-03-T2 | D-13 | Dashed paths keep pattern via userSpaceOnUse mask, no leftovers, endpoints aligned | e2e smoke | `motion_smoke.py -k itinerari:` | ✅ | ⬜ pending |
| 07-03-T3 | D-13/D-14/D-07/D-04/D-05 | Stops light up, first stop, ≤ 700 ms incl. redraw restarts, no re-animate, reduced/blocked | e2e smoke | `motion_smoke.py -k itinerari:` (8 checks) + full suite | ✅ | ⬜ pending |
| all | D-15 | Existing reduced-motion guards untouched | structural | static check `d15-guards` | ✅ | ⬜ pending |
| 07-01-T5, 07-02-T3, 07-03-T4 | D-07/D-09/D-13/D-16 | Visual feel, Safari/Firefox, deploy approval | manual (blocking-human) | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `fp-cercador/scripts/motion_smoke.py` — e2e rows above (Chrome channel, route mocks, local `http.server`)
- [ ] `fp-cercador/scripts/check_motion_static.sh` — structural rows
- [ ] No framework install; do NOT add Playwright to `backend/requirements.txt`

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Visual feel matches launch video (eases, rhythm) | D-07/D-09 | Subjective | Owner reviews each page locally before deploy |
| `<tr>` transform + SVG mask in Safari/Firefox | D-09/D-13 | No Safari/Firefox automation available | Open index (search) and itinerari timeline in Safari and Firefox |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
