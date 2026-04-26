---
plan: 06-02
phase: 06-admin-panel
status: complete
completed: 2026-04-26
commit: 2f72839
---

## Summary

`admin.html` complet i autocontingut (CSS + JS inline, sense frameworks). Tres seccions operatives: Refresh manual, Cookies del buscador i Refresh periòdic. Paleta i topbar idèntics a `index.html`.

## What Was Built

### Task 1: Estructura, estils i secció Refresh manual
- HTML complet amb `<!DOCTYPE html>`, Google Fonts (DM Sans + DM Serif Display + Geist Mono), topbar fosc `GrausFP`.
- CSS inline copiat de `index.html`: reset, `:root` amb les 6 variables (`--dark: #1c1410`, etc.), topbar, spinner, error state. Afegits: `.container`, `.section`, `.status-msg`, `.by-grado-table`, `details/summary`, `.form-row`, `.next-run`.
- Secció "Refresh manual": input password token, botó "Actualitzar dades", àrea de status.
- JS: `getToken()`, `setStatus/clearStatus/stopPolling`, `renderDone/renderError`, `escapeHtml`, `pollOnce`, listener del botó.
- Comportament: 401 → "Token incorrecte", 409 → "Ja hi ha un refresh en curs", 200 → polling `/api/refresh-status` cada 3s (ADMN-04), running → spinner, done → taula per Grado, error → llista escapada.
- ADMN-08: cap `localStorage`/`sessionStorage` al fitxer.

### Task 2: Seccions Cookies + Scheduler
- **Cookies**: textarea, `<details>` col·lapsable tancat per defecte amb instruccions pas a pas (URL buscador, DevTools, cURL, quines dues cookies extreure), botó "Guardar" → POST `/api/admin/update-cookies`.
- Respostes: 200 → "Cookies guardades correctament", 400 → "Format invàlid", 401 → "Token incorrecte", 500 → "Error escrivint .env".
- **Scheduler**: botó "Carregar config actual" → GET `/api/admin/scheduler` → mostra form (checkbox activat, select dia, input hora/minut). "Desar config" → POST, "Desactivar" → DELETE amb confirm dialog.
- `applyConfigToForm` formata `next_run` amb `toLocaleString('ca-ES')`.

## Verification

```
OK — 25/25 checks passen. Lines: 500
✓ topbar present, refresh endpoint, refresh-status endpoint
✓ polling 3s, Bearer auth, Token incorrecte, Actualitzant
✓ NO localStorage, NO sessionStorage
✓ DM Sans, --dark: #1c1410, h1 Administracio, 3 sections
✓ cookies endpoint, scheduler 3x, details, JSESSIONID, __Host-todofp.es
✓ Cada dia, hour 0-23, min 0-59, DELETE, confirm, Propera execució
✓ >= 350 lines (500 total)
```

## Key Files

- `fp-cercador/frontend/admin.html` — pàgina admin completa (500 línies)

## Self-Check: PASSED

Tots els acceptance criteria del Plan 06-02 complerts. ADMN-01..ADMN-08 tots implementats.
