---
phase: quick
plan: 260419-wm
subsystem: deploy
tags: [deploy, gunicorn, nginx, systemd, cloudpanel, vps]
dependency_graph:
  requires: []
  provides: [deploy-artifacts, systemd-service, nginx-config, deploy-guide]
  affects: [fp-cercador/backend/requirements.txt, fp-cercador/frontend/index.html]
tech_stack:
  added: [gunicorn]
  patterns: [nginx-reverse-proxy, systemd-service, dynamic-api-base]
key_files:
  created:
    - deploy/fp-cercador.service
    - deploy/nginx-cloudpanel.conf
    - deploy/DEPLOY.md
  modified:
    - fp-cercador/backend/requirements.txt
    - fp-cercador/frontend/index.html
decisions:
  - "API_BASE ternari en lloc de variable d'entorn de build: zero tooling, compatible amb HTML pur"
  - "gunicorn --timeout 120: pipeline de refresh pot trigar 45s+, valor per defecte (30s) mataria el worker"
  - "proxy_read_timeout 130s a nginx: marge de 10s sobre el timeout de gunicorn"
  - "User=root al servei systemd: CloudPanel per defecte; comentat per facilitar ajust"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-04-19"
  tasks_completed: 2
  files_created: 3
  files_modified: 2
---

# Quick 260419-wm: Deploy VPS Contabo CloudPanel Summary

**One-liner:** Artefactes de deploy complets — gunicorn a requirements, API_BASE dinàmica al frontend, unitat systemd amb timeout extès, config nginx amb proxy invers, i guia de desplegament en 8 passos.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | gunicorn a requirements.txt + API_BASE dinàmic | 69a345b | requirements.txt, index.html |
| 2 | Fitxers de deploy (systemd + nginx + DEPLOY.md) | 43267db | deploy/fp-cercador.service, deploy/nginx-cloudpanel.conf, deploy/DEPLOY.md |

## What Was Built

**Tasca 1 — Prerequisits de producció:**
- `gunicorn` afegit a `fp-cercador/backend/requirements.txt` (dependency de producció per servir Flask)
- `API_BASE` al frontend canviat de hardcode `'http://localhost:5001'` a ternari dinàmic: `window.location.hostname === 'localhost' ? 'http://localhost:5001' : ''`. En producció retorna cadena buida, fent les peticions relatives (`/api/ofertes`), que nginx enruta al backend sense cap hardcode de domini.

**Tasca 2 — Artefactes de deploy:**
- `deploy/fp-cercador.service`: unitat systemd que arrenca gunicorn amb 2 workers, binding a `127.0.0.1:5001`, `--timeout 120` (cobreix el pipeline de refresh de 45s+), logs a `/var/log/fp-cercador/`
- `deploy/nginx-cloudpanel.conf`: config nginx amb bloc HTTP→HTTPS redirect, frontend estàtic servit directament, `location /api/` amb proxy_pass al backend (proxy_read_timeout 130s), i `location /health` per al health check
- `deploy/DEPLOY.md`: guia en 8 seccions cobreix tot el cicle: clonar repo, venv, .env, directori de logs, instal·lació systemd, configuració nginx (Opció A via CloudPanel UI + Opció B manual), verificació final, i primer refresh de dades

## Decisions Made

- **API_BASE ternari vs variable d'entorn:** El ternari `window.location.hostname` no requereix cap tooling de build (Vite, webpack) ni variables d'entorn al frontend — compatible amb HTML pur servit per nginx.
- **gunicorn --timeout 120:** El pipeline de refresh pot trigar fins a 45s+; el timeout per defecte de gunicorn (30s) mataria el worker durant el primer refresh. 120s dona marge suficient.
- **proxy_read_timeout 130s a nginx:** Marge de 10s sobre el timeout de gunicorn (120s) per evitar que nginx tanqui la connexió abans que gunicorn respongui.
- **User=root:** CloudPanel típicament opera com a root. Documentat al DEPLOY.md per ajustar si el VPS té usuari dedicat (canviar `User=` al .service).

## Deviations from Plan

None — pla executat exactament com estava escrit.

## Known Stubs

None — tots els artefactes estan completament implementats i llestos per usar.

## Threat Surface Scan

No nova superfície de xarxa introduïda. Els fitxers de deploy no modifiquen cap endpoint ni path d'autenticació. El threat model del pla (T-D-01 a T-D-04) queda cobert:
- T-D-01: `.env` fora del document root, llegit via `EnvironmentFile` al servei systemd (no exposat per nginx)
- T-D-02: Logs a `/var/log/fp-cercador/`, no accessibles via web
- T-D-03: User=root documentat amb nota per canviar si cal
- T-D-04: `/api/admin/refresh` protegit per ADMIN_TOKEN (ja implementat a app.py)

## Self-Check: PASSED

- fp-cercador/backend/requirements.txt conté "gunicorn": FOUND
- fp-cercador/frontend/index.html conté "window.location.hostname": FOUND
- deploy/fp-cercador.service existeix: FOUND
- deploy/nginx-cloudpanel.conf existeix: FOUND
- deploy/DEPLOY.md existeix: FOUND
- Commit 69a345b: FOUND
- Commit 43267db: FOUND
