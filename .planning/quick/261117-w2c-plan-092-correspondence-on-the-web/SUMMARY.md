---
quick_id: 261117-w2c
status: complete
date: 2026-11-17
---

# Summary — Plan 092: correspondence on the web

- Backend (`app.py`, `uc_corr.py`, `itinerary_graph.py`, `grau_page.py`): C→D edges carry `conv`, `mods`,
  `derogada`; `/api/correspondencia` adds `certificats` and `moduls_restants`; `/api/que-em-falta` adds
  `convalidacions`. Backend suite: 869 passed.
- Frontend: `itinerari.html` (pills, legend, detail per cycle, cycle table), `que-em-falta.html`
  (official convalidations, repealed tables in their own group), `i18n.js` (ca/es), version bump to
  `20261117a` on every page.
- Repealed tables: «Taula derogada» tag with icon, red edge, warning with the replacing decree, dotted
  red line, listed last.
- Checked in the browser with ELEE0109, the Mecanizado cycle and a mixed held list, ca and es, 1280 and
  375 px, keyboard. No horizontal overflow.
- Not deployed. Deploy needs `git pull` and a service restart.
