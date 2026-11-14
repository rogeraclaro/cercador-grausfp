---
quick_id: 261114-ekq
status: complete
date: 2026-11-14
branch: fix/audit-261114 (not pushed, not deployed)
---
# Audit 2026-11-14 — what was fixed and what is left

Verification: 568 backend tests green (10 new in `tests/test_audit_fixes.py`); `node --check`
on every edited script; index.html fixes exercised in a browser against the local backend.
`tests/test_pipeline.py` was not run (network; it hangs offline).

## Fixed

Backend
- Alerts: `familia`/`texto`/`nivel` are type-checked on creation; a filter that cannot be
  evaluated no longer aborts the dispatch for every later alert.
- Unsubscribe tokens (alerts and centre watches): an expired token is replaced. Before, every
  unsubscribe link failed for good 365 days after the first email.
- Centres refresh: keeps the enriched `url_web` (13,373 of 17,951 centres locally would have
  been wiped), writes atomically, and a persistent 429 raises instead of storing "no centres".
- Observatory: returns the latest 200 snapshots (it returned the oldest 200).
- SMTP timeout 30 s; `/api/ocupaciones` limited to 8 tokens / 200 chars; `ciclos_fp.json`
  written atomically; centres caches swapped in one step (no `None` window).
- `_AUTH_ORIGINS` gains `https://grausfp.es` and `http://localhost:8765` (the documented dev
  server could not call `/api/auth/*`).
- Unused imports and variable removed.

Frontend
- index.html: centres error state with retry (an error body was cached as the list and broke
  the panel); favourites and centre ticks roll back on any failed response and the centre is
  saved after the favourite exists; occupation search drops stale responses; the page number
  is reset when switching mode; FPO error is "unavailable", not "0 results"; the ca→es term
  map invalidates the search memo; `?q=…&grado=X` is honoured (observatory links were dead).
- login.html honours `?next=` (own pages only).
- auth.js shows a notice for `/?unsubscribed=1` and `/?google_error=…` (were silent).
- historial.html escapes the scraper error text; admin.html escapes the config error and
  re-enables the FPO button after a 409; forgot-password.html no longer says "email sent" on
  a 500; perfil.html shows an error instead of "no favourites" when the API fails and
  sanitises `ficha_url`; alertes.js no longer hard-codes Spanish.
- Cache version `20261114a` for i18n.js, auth.js and alertes.js on every page.

## Second pass (same day, decisions taken with the owner)

- Refresh aborts and keeps the previous catalogue if a grado loses over half its records
  (`REFRESH_ALLOW_DROP=1` in `.env` overrides it for a real change).
- Scheduled and manual refresh share `scheduler_service.run_refresh_job`: the Sunday run now
  also sends the Brevo news campaign and uses `BASE_URL`.
- `POST /api/auth/resend-verification` and a resend button on the login error.
- Privacy policy declares Google Fonts (owner chose to declare, not self-host).
- Removal alerts are filtered by familia/nivel/texto like additions (`removed_by_grado_meta`).
- `/api/certificado/<codigo>` cached per catalogue, generic error.
- historial.html fully translated; no raw scraper error on the public page.
- Keyboard-sortable headers, pressed state on mode/grade buttons, named favourite buttons,
  orphan favourites shown in the profile with a remove button.
- nginx vhost checked: `/api/` sets `X-Real-IP $remote_addr`, nothing to do.
- CLAUDE.md lists gunicorn and apscheduler; two orphan local data files deleted.

## Still open

- Modal focus trap; unlabeled controls in index.html (occupation search, FPO text filter,
  centres CCAA select and search, close button).
- Partial centre scrapes still checkpoint over the live file; other scrapers (d_modulos,
  b_contingut, SOC, generate_ocupaciones) have no plausibility threshold.
- No rate limit / purge for sessions and tokens tables; missing indexes (low impact today).
- No canonical/hreflang on static pages; auth pages lack noindex.
- test_pipeline.py is network-bound and was not run.
