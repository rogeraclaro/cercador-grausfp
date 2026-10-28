---
phase: "07"
slug: "microanimacions-gsap"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-28"
---

# Phase 07 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| third-party code -> repo | `gsap.min.js` copied from npm into `frontend/vendor/`, served on index, observatori, itinerari | executable third-party JS |
| server -> browser | static files (vendored GSAP, motion.js, i18n.js) served by nginx | public static assets |
| i18n.js -> DOM | translation values written with innerHTML | static first-party strings |
| API -> DOM / SVG DOM | `/api/observatory` and `/api/itinerari/complet` data drive bars and SVG paths | public catalogue numbers |
| dev machine -> localhost | `motion_smoke.py` serves `frontend/` on a local ephemeral port | local test traffic only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-07-SC | Tampering | vendored `gsap-3.14.2.min.js` (supply chain) | high | mitigate | sha256 `c174bfce…8cd8280` matches on disk; `scripts/check_motion_static.sh:11,32` re-verifies it on every run | closed |
| T-07-01 | Tampering | runtime script loading (CDN) | medium | mitigate | All three pages load `vendor/gsap-3.14.2.min.js` same-origin (index.html:3289, observatori.html:337, itinerari.html:1653); static check rejects remote gsap | closed |
| T-07-02 | Denial of Service | index.html when GSAP missing/throws | medium | mitigate | `motion.js` guards `window.gsap`, catches builder errors and reverts (lines 11–34); callers use `GFPMotion?.play` | closed |
| T-07-03 | Tampering | `modal.alert.ok` via innerHTML | low | accept | Static first-party string, no user/API data | closed |
| T-07-04 | Repudiation | GSAP license compliance | low | mitigate | Header kept byte-identical (hash check) + `vendor-header` static check; provenance in CLAUDE.md | closed |
| T-07-05 | Information Disclosure | local `http.server` in `motion_smoke.py` | low | mitigate | Bound to `localhost` port 0 (`scripts/motion_smoke.py:71`) | closed |
| T-07-06 | Tampering | counting copy in `animateBars` | low | mitigate | Writes only `ghost.textContent` from a rounded number + suffix (observatori.html `animateBars`) | closed |
| T-07-07 | Denial of Service | observatori chart when GSAP missing | low | mitigate | `GFPMotion?.play('bars', …)` guard; final values in markup | closed |
| T-07-08 | Tampering | mask/clone construction in `animateTimeline` | low | mitigate | `createElementNS`/`setAttribute` only, generated ids `tlm<i>` (itinerari.html:1001–1015) | closed |
| T-07-09 | Denial of Service | redraw storms leaking tweens/SVG nodes | low | mitigate | Single reverted `'timeline'` slot + cleanup; `itinerari:no-reanimate` / `dashed-preserved` smoke checks | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-03 | `modal.alert.ok` is a static first-party translation string; no user or API data reaches it | plan 07-01 (plan-time disposition) | 2026-10-28 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-28 | 10 | 10 | 0 | /gsd-secure-phase 7 (L1 grep verification, orchestrator) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-28
