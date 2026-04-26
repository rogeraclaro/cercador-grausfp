---
plan: 06-01
phase: 06-admin-panel
status: complete
completed: 2026-04-26
commit: cde9c62
---

## Summary

Backend complet del panell admin (Fase 6): bug fix de la doble crida a `/api/admin/refresh`, nous endpoints per gestionar cookies i scheduler periòdic, i `pipeline.run()` que recarrega `.env` en cada execució.

## What Was Built

### Task 1: Bug fix refresh + endpoint update-cookies + load_dotenv pipeline
- **`admin_refresh` (bug fix D-12)**: `set_state(status="running")` ara s'executa síncron dins `admin_refresh`, abans de llançar el thread. Afegit logging de `lock acquired` i `thread ident`. La primera crida amb token vàlid ja no retorna 409 espuri.
- **`_write_env_value`**: helper d'escriptura atòmica al `.env` (via tempfile + os.replace).
- **`admin_update_cookies`**: endpoint `POST /api/admin/update-cookies` — valida que `JSESSIONID=` hi sigui, escriu al `.env` i actualitza `os.environ` en viu.
- **`pipeline.run()`**: afegit `from dotenv import load_dotenv` i `load_dotenv(override=True)` com a primera instrucció de `run()`.

### Task 2: Mòdul scheduler_service.py + apscheduler a requirements
- **`scheduler_service.py`** creat amb API completa: `load_config`, `save_config`, `apply_config`, `init_scheduler`, `get_next_run_iso`, `_scheduled_refresh`.
- Config persistida a `backend/data/scheduler.json` (atòmica).
- `_scheduled_refresh` reutilitza `refresh_state._lock` per evitar concurrència amb refreshos manuals.
- `apscheduler` afegit a `requirements.txt`.

### Task 3: Endpoints scheduler a app.py + init a l'arrencada
- `import scheduler_service` i `scheduler_service.init_scheduler()` ja presents al `app.py` (dels canvis previs de la fase).
- **`GET /api/admin/scheduler`**: retorna config actual + `next_run` ISO.
- **`POST /api/admin/scheduler`**: valida i persisteix config, programa job APScheduler, retorna config validada + `next_run`.
- **`DELETE /api/admin/scheduler`**: desactiva el job i persisteix `enabled=false`.
- Tots els endpoints retornen 401 sense Bearer correcte.

## Verification

```
✓ app.py syntax OK
✓ pipeline.py syntax OK
✓ scheduler_service.py syntax OK
✓ routes OK: ['/api/admin/refresh', '/api/admin/scheduler' ×3, '/api/admin/update-cookies']
✓ grep: admin_update_cookies ≥1, _write_env_value ≥2, load_dotenv(override=True) =1
✓ apscheduler present a requirements.txt
```

## Key Files

- `fp-cercador/backend/app.py` — bug fix + 4 nous endpoints admin
- `fp-cercador/backend/scheduler_service.py` — nou mòdul APScheduler
- `fp-cercador/backend/scrapers/pipeline.py` — load_dotenv(override=True)
- `fp-cercador/backend/requirements.txt` — apscheduler afegit

## Self-Check: PASSED

Tots els acceptance criteria del Plan 06-01 complerts. Smoke test confirma 5 rutes admin carregables.
