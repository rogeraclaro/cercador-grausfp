# Pla 049 — Renovació automàtica de l'índex d'ocupacions

> Generat: 2026-06-21 · Commit base: `2b4fa22`
> Categoria: manteniment / automatització · Esforç: S · Priority: P2

## Problema

`scripts/generate_ocupaciones.py` genera `backend/data/ocupaciones.json` — l'índex
de cerca per ocupació de F6 — però **és d'execució manual**. El `pipeline.py:run()`
actualitza `ofertes.json` i `oferta_centres.json` setmanalment però no regenera
`ocupaciones.json`. Si el ministeri afegeix titulacions noves (passa cada trimestre
acadèmic), la cerca per ocupació retorna dades desfasades sense que ningú ho noti.

## Solució

Seguir el patró `admin_refresh_centres()` (`app.py:534-576`) exactament:

1. Afegir `POST /api/admin/refresh-ocupaciones` — endpoint admin que llança la
   regeneració en un thread de fons.
2. Afegir `GET /api/admin/ocupaciones-status` — retorna l'estat (idle/running/done/error).
3. Afegir un job **mensual** al `scheduler_service.py` que crida automàticament
   la regeneració (opcional, però recomanat).

## Fitxers en àmbit

| Fitxer | Canvi |
|--------|-------|
| `backend/app.py` | Afegir 2 routes + state dict + lock (~50 línies) |
| `backend/scheduler_service.py` | Afegir job mensual opcional (~20 línies) |
| `scripts/generate_ocupaciones.py` | Cap canvi — es crida via subprocess |

**Fora d'àmbit:** `pipeline.py`, `history.py`, `notifier.py`, `db.py`, cap fitxer
de frontend.

## Implementació pas a pas

### Pas 1 — Afegir el bloc d'estat i el lock a `app.py`

Insereix just **sota** el bloc de `_centres_scrape_state` (`app.py:522-525`):

```python
# ---------------------------------------------------------------------------
# Generació de l'índex d'ocupacions (F6) — admin manual o job mensual
# ---------------------------------------------------------------------------

_ocup_build_state: dict = {
    "status": "idle", "started_at": None,
    "finished_at": None, "total_entries": None, "error": None,
}
_ocup_build_lock = threading.Lock()
```

Verificació: `grep '_ocup_build_state' backend/app.py` ha de trobar la nova variable.

### Pas 2 — Afegir `GET /api/admin/ocupaciones-status`

Insereix just **sota** el bloc anterior (o agrupa-ho amb els endpoints de centres):

```python
@app.route("/api/admin/ocupaciones-status")
def ocupaciones_build_status():
    """Retorna l'estat de la darrera regeneració de l'índex d'ocupacions."""
    return jsonify(_ocup_build_state), 200
```

### Pas 3 — Afegir `POST /api/admin/refresh-ocupaciones`

```python
@app.route("/api/admin/refresh-ocupaciones", methods=["POST"])
def admin_refresh_ocupaciones():
    """Regenera ocupaciones.json en background (requereix Bearer token).

    Crida scripts/generate_ocupaciones.py com a subprocess per aïllament i per
    reutilitzar el codi existent sense moure-ho. Tarda ~2-3 min.
    Retorna 409 si ja hi ha una regeneració en curs.
    """
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    if not _ocup_build_lock.acquire(blocking=False):
        return jsonify({"error": "Regeneració d'ocupacions ja en curs"}), 409

    _ocup_build_state.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None, total_entries=None, error=None,
    )

    def _run():
        import subprocess
        repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
        script = os.path.join(repo_root, 'scripts', 'generate_ocupaciones.py')
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True, text=True, check=True,
            )
            logger.info("refresh-ocupaciones: completat\n%s", result.stdout[-2000:])
            # Recompta les entrades del fitxer generat
            total = 0
            if os.path.exists(OCUPACIONES_PATH):
                try:
                    with open(OCUPACIONES_PATH, encoding='utf-8') as f:
                        total = len(json.load(f))
                except (OSError, json.JSONDecodeError):
                    pass
            # Invalida la cache en memòria perquè el proper /api/ocupaciones llegeixi
            # el fitxer nou.
            _ocupaciones_cache.update(mtime=None, entries=None)
            _ocup_build_state.update(
                status="done",
                finished_at=datetime.now(timezone.utc).isoformat(),
                total_entries=total, error=None,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("refresh-ocupaciones: error\n%s", exc.stderr[-2000:])
            _ocup_build_state.update(
                status="error", error=exc.stderr[-500:],
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:
            logger.error("refresh-ocupaciones: error inesperat: %s", exc)
            _ocup_build_state.update(
                status="error", error=str(exc),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        finally:
            _ocup_build_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"}), 200
```

**Nota sobre `sys.executable`**: cal afegir `import sys` si no és present. Comprova
si ja hi és amb `grep '^import sys' backend/app.py`. Si no hi és, afegeix-lo al
bloc d'imports existents.

Verificació del pas: `grep "refresh-ocupaciones" backend/app.py` ha de trobar les
dues routes.

### Pas 4 — Actualitzar el docstring de rutes a `app.py`

Al bloc de comentari inicial d'`app.py` (línies 1-32), afegeix:

```
  POST   /api/admin/refresh-ocupaciones → regenera ocupaciones.json (requereix Bearer token)
  GET    /api/admin/ocupaciones-status  → estat de la darrera regeneració (sense auth)
```

### Pas 5 (opcional) — Job mensual al scheduler

A `backend/scheduler_service.py`, **en el context del scheduler APScheduler existent**,
afegeix un segon job que crida la mateixa lògica mensualment. Busca el patró
`_scheduler.add_job` i afegeix just al costat:

```python
# Job mensual per regenerar l'índex d'ocupacions de F6.
# S'executa el 1r de cada mes a les 04:00 UTC, DESPRÉS del refresh setmanal
# (que sol ser dilluns a les 03:00).
_OCUP_JOB_ID = "monthly_ocupaciones"

def _run_ocupaciones_job():
    """Crida POST /api/admin/refresh-ocupaciones internament (no via HTTP)."""
    import subprocess, sys as _sys
    repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
    script = os.path.join(repo_root, 'scripts', 'generate_ocupaciones.py')
    try:
        subprocess.run([_sys.executable, script], check=True)
        logger.info("monthly_ocupaciones: completat")
    except Exception as exc:
        logger.error("monthly_ocupaciones: error: %s", exc)
```

I al `apply_config()`, just on es configuren els jobs:

```python
if _scheduler.get_job(_OCUP_JOB_ID) is None:
    _scheduler.add_job(
        _run_ocupaciones_job, 'cron',
        day=1, hour=4, minute=0,
        id=_OCUP_JOB_ID, replace_existing=True,
    )
```

**STOP condition**: Si el job mensual complica l'estructura del scheduler o xoca
amb la gestió de config existent, **implementa només els passos 1–4** (l'endpoint
manual és suficient per a la primera iteració). Reporta-ho i el propietari decidirà.

### Pas 6 — Tests

El fitxer de tests és `backend/tests/`. Mira els tests existents per a `admin_refresh`
o `admin_refresh_centres` com a patró. Escriu un test per a cada cas:

- `POST /api/admin/refresh-ocupaciones` sense token → 401
- `POST /api/admin/refresh-ocupaciones` amb token vàlid → 200 `{"status": "started"}`
- `POST /api/admin/refresh-ocupaciones` dos cops seguits → segon retorna 409
- `GET /api/admin/ocupaciones-status` → 200 amb `{"status": "idle"|"running"|"done"|"error"}`

Usa `unittest.mock.patch('subprocess.run')` per no fer scraping real als tests.

Execució de la suite:
```bash
cd backend
python -m pytest tests/ -v
```
Expected: tots els tests verds.

## Criteris de done

```bash
# 1. Les dues routes existeixen
grep "refresh-ocupaciones\|ocupaciones-status" backend/app.py

# 2. El lock i el state dict existeixen
grep "_ocup_build_lock\|_ocup_build_state" backend/app.py

# 3. sys importat
grep "^import sys" backend/app.py

# 4. Tests passen
cd backend && python -m pytest tests/ -v

# 5. Crida manual funciona (cal xarxa + ocupaciones.json al VPS)
# Fer des del VPS o amb token real:
# curl -X POST http://localhost:5001/api/admin/refresh-ocupaciones \
#      -H "Authorization: Bearer $ADMIN_TOKEN"
# Esperar ~3 min, llavors:
# curl http://localhost:5001/api/admin/ocupaciones-status
# → {"status": "done", "total_entries": ...}
```

## Desplegament al VPS

1. `git pull` al VPS.
2. `systemctl restart fp-cercador`.
3. Cridar l'endpoint manualment una vegada per actualitzar l'índex:
   ```bash
   curl -X POST https://<domini>/api/admin/refresh-ocupaciones \
        -H "Authorization: Bearer $ADMIN_TOKEN"
   # Verificar ~3 min després:
   curl https://<domini>/api/admin/ocupaciones-status
   ```
4. A partir d'ara el job mensual (si s'ha implementat el pas 5) ho farà sol.
   Si no, repetir el `curl` cada trimestre quan el catàleg canviï.

## Notes de manteniment

- El subprocess hereda l'entorn de Python del procés Flask (el venv), per la qual
  cosa `pdfplumber`, `requests` i `beautifulsoup4` hi seran disponibles.
- Si el ministeri canvia l'estructura del PDF de `/pdfPT` o la pàgina de fitxes
  D/E, `generate_ocupaciones.py` fallarà i l'endpoint retornarà `{"status": "error"}`.
  El fitxer `ocupaciones.json` antic es manté intacte (el script escriu atòmicament).
- La invalidació de cache (`_ocupaciones_cache.update(mtime=None, entries=None)`)
  al `_run()` garanteix que el proper `/api/ocupaciones` llegeixi el fitxer nou.
