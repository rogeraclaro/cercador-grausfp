---
phase: 01-project-setup
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - fp-cercador/backend/app.py
  - fp-cercador/backend/requirements.txt
  - fp-cercador/backend/.env.example
  - fp-cercador/backend/scrapers/__init__.py
  - fp-cercador/.gitignore
  - fp-cercador/frontend/index.html
  - fp-cercador/frontend/admin.html
  - fp-cercador/backend/data/ofertes.json
  - fp-cercador/README.md
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-16
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This is a Phase 1 project-setup deliverable. Most files are stubs or scaffolding for later phases. The codebase is minimal — `app.py` is a 12-line shell, the frontend HTML files are empty placeholders, and the scraper package is a one-liner comment. Review focuses on correctness and security of what IS present rather than what's missing.

One critical issue is found: `debug=True` is hardcoded in `app.run()` with no environment guard, meaning the Werkzeug debugger (remote code execution surface) will be active in production. Three warnings cover missing dependency pinning, an unprotected CORS wildcard, and a nullable field with no schema documentation. Three info items cover minor quality matters.

## Critical Issues

### CR-01: `debug=True` Hardcoded — Remote Code Execution Risk in Production

**File:** `fp-cercador/backend/app.py:11`
**Issue:** `app.run(debug=True)` is unconditional. Flask's debug mode activates the Werkzeug interactive debugger, which allows arbitrary Python code execution in any browser that reaches an error page. If this file is deployed to the VPS as-is (or a developer forgets to change it), the production server is fully compromised by anyone who can trigger a 500 error.
**Fix:**
```python
import os

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug)
```
Set `FLASK_DEBUG=true` in the local `.env` (already gitignored) and leave the production `.env` without it or with `FLASK_DEBUG=false`.

---

## Warnings

### WR-01: CORS Wildcard — All Origins Permitted

**File:** `fp-cercador/backend/app.py:8`
**Issue:** `CORS(app)` with no arguments allows any origin to call the API. This is fine for a fully public read-only API, but the project includes an admin panel that will use `ADMIN_TOKEN` for protected endpoints. If the CORS policy is not tightened before those endpoints exist, a malicious page loaded in an admin's browser can call admin routes cross-origin.
**Fix:** Restrict origins to the known frontend domain as soon as the deployment URL is known, or at minimum restrict admin-route CORS separately:
```python
CORS(app, resources={
    r"/api/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*")}
})
```
Document in `.env.example` that `ALLOWED_ORIGINS` should be set in production.

### WR-02: No Dependency Version Pins — Reproducibility and Supply-Chain Risk

**File:** `fp-cercador/backend/requirements.txt:1-6`
**Issue:** All six dependencies are unpinned (e.g., `flask`, `pdfplumber`). A `pip install` today and one six months from now will install different versions. This is a reproducibility problem and a supply-chain risk: a new major version of Flask, pdfplumber, or beautifulsoup4 can introduce breaking changes or, in a worst-case scenario, a compromised release could be pulled in silently.
**Fix:** Pin to specific versions after the first working install:
```
flask==3.1.0
flask-cors==5.0.1
pdfplumber==0.11.4
requests==2.32.3
beautifulsoup4==4.13.3
python-dotenv==1.1.0
```
Generate with `pip freeze > requirements.txt` inside the virtualenv.

### WR-03: Nullable `codigo` and `nivel` Fields — Undocumented Schema Contract

**File:** `fp-cercador/backend/data/ofertes.json:38,66`
**Issue:** Records with `grado: "D"` have `codigo: null` and the `grado: "E"` record has both `codigo: null` and `nivel: null`. The schema allows nulls but there is no documentation or validation stating when nulls are expected. Future scraper and frontend code that accesses `record.codigo.toUpperCase()` or filters by `nivel` without a null guard will crash or silently misfilter. This is a data-contract gap that will produce bugs in Phases 2–5.
**Fix:** Add a `SCHEMA.md` or inline JSON Schema comment documenting which fields are nullable and under what conditions (e.g., "Grado D/E courses defined by Ley 3/2022 do not yet have official `codigo`"). Ensure all consumers null-check before using these fields.

---

## Info

### IN-01: `.env.bak` Excluded from `.gitignore` but `.env` Is Not Fully Covered

**File:** `fp-cercador/.gitignore:14`
**Issue:** The gitignore excludes `.env` and `.env.bak` individually. It does NOT exclude `.env.*` variants like `.env.local`, `.env.production`, or `.env.staging`, which are common naming conventions developers use. A developer creating `.env.production` with real credentials would not be protected.
**Fix:** Add a broader pattern alongside the specific ones:
```gitignore
.env
.env.*
!.env.example
```
The negation keeps `.env.example` tracked (as intended) while catching all other `.env.*` files.

### IN-02: README Missing Production Deployment Notes

**File:** `fp-cercador/README.md:1-12`
**Issue:** The README only covers local dev setup. There is no mention of setting `FLASK_DEBUG=false` for production, the VPS/CloudPanel deployment target, or that `ADMIN_TOKEN` must be changed before going live. Given that the critical bug (CR-01) stems from a missing production/development distinction, this documentation gap increases the likelihood the issue is hit.
**Fix:** Add a "Production" section to README noting: disable debug mode, set a real `ADMIN_TOKEN`, and restrict `ALLOWED_ORIGINS`.

### IN-03: `data/ofertes.json` Mixed-Language Field Values

**File:** `fp-cercador/backend/data/ofertes.json:1-72`
**Issue:** Field values mix Catalan and Spanish inconsistently: `familia` values are in Catalan ("Administració i Gestió", "Informàtica i Comunicacions") while `denominacion` values are also in Catalan despite the project README using "España" branding. This is a data quality note for Phase 2 — the scraper will need a defined canonical language per field to avoid inconsistent display in the frontend.
**Fix:** Decide and document the language convention for each field before Phase 2 data ingestion begins.

---

_Reviewed: 2026-04-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
