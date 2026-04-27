# Phase 6: Frontend — Admin Panel - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 5
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `fp-cercador/frontend/admin.html` | component (HTML/JS) | request-response + polling | `fp-cercador/frontend/index.html` | role-match |
| `fp-cercador/backend/app.py` | controller (Flask routes) | request-response | `fp-cercador/backend/app.py` (existent) | exact (extensió) |
| `fp-cercador/backend/scrapers/pipeline.py` | service (orchestrador) | batch | `fp-cercador/backend/scrapers/pipeline.py` (existent) | exact (extensió mínima) |
| `fp-cercador/backend/requirements.txt` | config | — | `fp-cercador/backend/requirements.txt` (existent) | exact |
| `deploy/DEPLOY.md` | config/docs | — | `deploy/DEPLOY.md` (existent) | exact (actualització secció) |

---

## Pattern Assignments

### `fp-cercador/frontend/admin.html` (component, request-response + polling)

**Analog:** `fp-cercador/frontend/index.html`

**Imports / head pattern** (línies 1–16):
```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cercador FP — Administració</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link
    href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=DM+Serif+Display:ital@0;1&family=Geist+Mono:wght@400;500&display=swap"
    rel="stylesheet">
```

**Variables CSS (copiar íntegrament)** (línies 26–33):
```css
:root {
  --dark: #1c1410;
  --warm: #8a7060;
  --warm2: #f5ece2;
  --border: #e8ddd4;
  --bg: #fdf8f2;
  --white: #ffffff;
}
```

**Topbar pattern** (línies 43–60):
```css
.topbar {
  background: var(--dark);
  padding: 0 48px;
}
.topbar-inner {
  display: flex;
  align-items: center;
  height: 52px;
}
.topbar-logo {
  font-family: 'DM Serif Display', serif;
  color: var(--white);
  font-size: 20px;
  letter-spacing: -0.3px;
}
```
```html
<div class="topbar">
  <div class="topbar-inner">
    <span class="topbar-logo">GrausFP</span>
  </div>
</div>
```

**Spinner / loading state** (línies 379–401):
```css
@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
  border: 3px solid var(--border);
  border-top-color: var(--dark);
  border-radius: 50%;
  width: 32px; height: 32px;
  animation: spin 0.8s linear infinite;
}
.loading-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 16px; padding: 64px 48px; color: var(--warm);
}
```

**Error state pattern** (línies 403–410):
```css
.error-state {
  padding: 16px 20px;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 4px;
  margin: 24px 48px;
  font-size: 14px;
}
```

**API_BASE detection pattern** (línia 565–567):
```javascript
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:5001'
  : '';
```

**Fetch + error handling pattern** (línies 587–600):
```javascript
async init() {
  try {
    const res = await fetch(API_BASE + '/api/ofertes');
    if (!res.ok) { this.state = 'error'; return; }
    const data = await res.json();
    // processar data...
    this.state = 'ready';
  } catch (e) {
    this.state = 'error';
  }
},
```

**Notes admin.html:**
- No usar Alpine.js per al panell admin — el polling i la gestió d'estat és més simple amb JS vanilla (setInterval + fetch directe). Alpine afegeix complexitat innecessària per a 3 seccions simples.
- El collapsible d'instruccions: usar l'element HTML natiu `<details>`/`<summary>` — zero JS necessari.
- Token admin: guardar a variable JS de sessió (no localStorage per ADMN-08). Demanar via `prompt()` o un `<input type="password">` inline.
- Polling refresh-status: `setInterval(() => fetchStatus(), 3000)` actiu només mentre status === 'running'.

---

### `fp-cercador/backend/app.py` (controller, request-response — extensió)

**Analog:** `fp-cercador/backend/app.py` (el mateix fitxer, s'estén)

**Pattern d'autenticació reutilitzable** (línies 55–61):
```python
def _check_auth(req) -> bool:
    """Verifica el token Bearer amb comparació constant-time (evita timing attacks)."""
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth[7:]
    return hmac.compare_digest(provided, ADMIN_TOKEN)
```
Tots els nous endpoints admin han de cridar `_check_auth(request)` com a primera línia.

**Pattern endpoint admin existent** (línies 95–134):
```python
@app.route("/api/admin/refresh", methods=["POST"])
def admin_refresh():
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    # ... lògica de negoci ...
    return jsonify({"status": "started"}), 200
```

**Pattern escriptura atòmica al .env** (nou — no hi ha analog directe, usar os.replace):
```python
# Patró: llegir .env, substituir/afegir línia, escriure atòmicament
import tempfile, os

def _write_env_value(key: str, value: str, env_path: str) -> None:
    """Actualitza o afegeix KEY=value al .env de forma atòmica."""
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    new_line = f"{key}={value}\n"
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = new_line
            found = True
            break
    if not found:
        lines.append(new_line)
    dir_path = os.path.dirname(env_path)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                    dir=dir_path, delete=False) as tmp:
        tmp.writelines(lines)
        tmp_path = tmp.name
    os.replace(tmp_path, env_path)
```

**Pattern thread daemon** (línies 126–132 de app.py):
```python
try:
    t = threading.Thread(target=_run, daemon=True)
    t.start()
except Exception as exc:
    refresh_state._lock.release()
    logger.error("Could not start refresh thread: %s", exc)
    return jsonify({"error": "Could not start refresh"}), 500
```

**Nous endpoints a afegir (estructura):**
```python
ENV_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), ".env")
)
SCHEDULER_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "scheduler.json")
)

@app.route("/api/admin/update-cookies", methods=["POST"])
def admin_update_cookies():
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    cookies = body.get("cookies", "").strip()
    # validació bàsica: ha de contenir JSESSIONID
    if "JSESSIONID=" not in cookies:
        return jsonify({"error": "Invalid cookies format"}), 400
    _write_env_value("BUSCADOR_COOKIES", cookies, ENV_PATH)
    os.environ["BUSCADOR_COOKIES"] = cookies  # actualitzar entorn en viu
    return jsonify({"status": "ok"}), 200

@app.route("/api/admin/scheduler", methods=["GET"])
def scheduler_get():
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    # llegir scheduler.json i retornar
    ...

@app.route("/api/admin/scheduler", methods=["POST"])
def scheduler_set():
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    # actualitzar scheduler.json i reprogramar APScheduler
    ...

@app.route("/api/admin/scheduler", methods=["DELETE"])
def scheduler_delete():
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    # desactivar scheduler
    ...
```

**Bug doble crida (D-12) — investigar refresh_state._lock:**
El bug és a `app.py` línies 101–103. `_lock.acquire(blocking=False)` a la primera crida retorna `True` i adquireix el lock. El thread `_run` allibera el lock a `finally`. Si el primer `POST /api/admin/refresh` no allibera el lock per algun motiu de timing, la segona crida el troba ocupat i retorna 409. Revisar si `_run` es llança correctament amb `t.start()` i el `try/except` al voltant — si l'excepció és llançada abans de `t.start()`, el lock queda adquirit i mai s'allibera. Solució: moure `refresh_state._lock.release()` al `except` del bloc `try: t = threading.Thread(...)`.

---

### `fp-cercador/backend/scrapers/pipeline.py` (service, batch — extensió mínima)

**Analog:** `fp-cercador/backend/scrapers/pipeline.py` (el mateix fitxer)

**Canvi únic: afegir load_dotenv(override=True) al principi de run()** (línia 78):
```python
from dotenv import load_dotenv
import os

def run() -> dict:
    # D-01 (Phase 6): Reload .env each time so updated BUSCADOR_COOKIES
    # are picked up without restarting the service.
    load_dotenv(override=True)
    
    start = time.time()
    # ... resta del codi sense canvis ...
```

`load_dotenv` ja és importada a `app.py`; aquí cal importar-la també a `pipeline.py`. Verificar que `python-dotenv` ja és a `requirements.txt` (sí, hi és).

---

### `fp-cercador/backend/requirements.txt` (config)

**Analog:** `fp-cercador/backend/requirements.txt` (el mateix fitxer)

**Estat actual** (línies 1–7):
```
flask
flask-cors
pdfplumber
requests
beautifulsoup4
python-dotenv
gunicorn
```

**Canvi: afegir `apscheduler`** (sense pinning de versió, consistent amb la resta):
```
flask
flask-cors
pdfplumber
requests
beautifulsoup4
python-dotenv
gunicorn
apscheduler
```

**APScheduler — patró d'integració amb Flask (no hi ha analog al codebase):**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.start()

# Afegir/reemplaçar job:
scheduler.add_job(
    func=lambda: pipeline.run(),
    trigger='cron',
    day_of_week='mon',  # 'mon','tue','wed','thu','fri','sat','sun' o '*'
    hour=3, minute=0,
    id='weekly_refresh',
    replace_existing=True
)

# Eliminar job:
if scheduler.get_job('weekly_refresh'):
    scheduler.remove_job('weekly_refresh')
```

---

### `deploy/DEPLOY.md` (config/docs — actualització secció)

**Analog:** `deploy/DEPLOY.md` (el mateix fitxer)

**Secció a substituir:** "Renovar les cookies del buscador (quan caduca la sessió)" (línies 129–177)

**Patró de la secció actual** (extracte línies 148–161):
```markdown
### Actualitzar al VPS

```bash
nano /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/.env
# Substituir la línia BUSCADOR_COOKIES= pel nou valor
```
```
BUSCADOR_COOKIES=JSESSIONID=XXXXXXXX; __Host-todofp.es=YYYY...
```

Reinicia el servei perquè recarregui el `.env`:

```bash
systemctl restart fp-cercador
```
```

**La secció actualitzada ha de substituir el bloc "Actualitzar al VPS" per:**
```markdown
### Actualitzar des del panell d'administració (recomanat)

1. Obre `https://DOMINI_AQUI/admin.html`
2. Introdueix l'`ADMIN_TOKEN` quan et sigui demanat
3. A la secció **"Cookies del buscador"**, enganxa el valor obtingut
4. Clica **"Guardar"** — el servei actualitza les cookies sense reiniciar

> La secció de l'admin inclou les instruccions completes per obtenir les cookies amb DevTools.

### Alternativa: actualitzar manualment per SSH

```bash
nano /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/.env
# Substituir la línia BUSCADOR_COOKIES=
```
A partir de la Fase 6, **no cal `systemctl restart`** — el pipeline llegeix `.env` en cada execució.
```

---

## Shared Patterns

### Autenticació Bearer (tots els endpoints admin)
**Font:** `fp-cercador/backend/app.py` línies 55–61
**Aplicar a:** `POST /api/admin/update-cookies`, `GET/POST/DELETE /api/admin/scheduler`
```python
if not _check_auth(request):
    return jsonify({"error": "Unauthorized"}), 401
```

### JSON response format
**Font:** `fp-cercador/backend/app.py` línies 72, 86, 134
**Aplicar a:** Tots els nous endpoints
```python
return jsonify({"status": "ok"}), 200          # èxit
return jsonify({"error": "missatge"}), 4XX     # error client
```

### Escriptura atòmica de fitxers
**Font:** `fp-cercador/backend/scrapers/pipeline.py` línies 55–70 (`_write_atomic`)
**Aplicar a:** `_write_env_value()` (nou) i `scheduler.json` writes
```python
with tempfile.NamedTemporaryFile(..., dir=dir_path, delete=False) as tmp:
    # escriure contingut
    tmp_path = tmp.name
os.replace(tmp_path, output_path)
```

### CSS warm palette i tipografia
**Font:** `fp-cercador/frontend/index.html` línies 26–33 i 35–39
**Aplicar a:** `admin.html` (copiar íntegrament les variables CSS i la declaració `body`)

### Logger
**Font:** `fp-cercador/backend/app.py` línia 48; `pipeline.py` línia 31
**Aplicar a:** Qualsevol nou mòdul Python
```python
logger = logging.getLogger(__name__)
```

---

## No Analog Found

| File / Pattern | Role | Raó |
|----------------|------|-----|
| APScheduler integration | config/service | Primer scheduler al projecte; seguir patró de RESEARCH/documentació oficial |
| `scheduler.json` (nou fitxer de dades) | config | Primer fitxer de config JSON al backend; usar `_write_atomic` de pipeline.py |
| Polling JS (setInterval + fetch) | component | index.html no fa polling; patró estàndard JS vanilla sense analog local |
| `<details>`/`<summary>` collapsible | component | No existeix cap collapsible al codebase; usar HTML natiu sense JS |

---

## Metadata

**Analog search scope:** `fp-cercador/backend/`, `fp-cercador/frontend/`, `deploy/`
**Files scanned:** 7 (app.py, refresh_state.py, pipeline.py, buscador_scraper.py, index.html, admin.html, requirements.txt, DEPLOY.md)
**Pattern extraction date:** 2026-04-25
