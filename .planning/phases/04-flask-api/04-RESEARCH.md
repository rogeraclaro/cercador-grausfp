# Phase 4: Flask API - Research

**Researched:** 2026-04-18
**Domain:** Flask 3.x REST API — threading, autenticació Bearer, JSON serving
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Descripció | Suport de la recerca |
|----|------------|----------------------|
| API-01 | `GET /api/ofertes` retorna contingut complet de `ofertes.json` (status 200) | Verificat: load 20ms + serialize 13ms = ~33ms per a 12.374 registres. Flask `send_file` o `jsonify` ambdós viables |
| API-02 | `GET /api/ofertes` retorna 503 si `ofertes.json` no existeix | Verificat: `os.path.exists(DATA_PATH)` + `abort(503)` o resposta manual |
| API-03 | `POST /api/admin/refresh` llança pipeline en thread separat i retorna `{"status": "started"}` immediatament | Verificat: `threading.Thread(daemon=True)` + `threading.Lock` per a non-blocking |
| API-04 | `POST /api/admin/refresh` requereix `Authorization: Bearer <ADMIN_TOKEN>`; retorna 401 si incorrecte | Verificat: `request.headers.get('Authorization', '')[7:]` + comparació constant-time |
| API-05 | `POST /api/admin/refresh` retorna 409 si ja hi ha un procés en curs | Verificat: `lock.acquire(blocking=False)` retorna `False` si ja s'ha adquirit |
| API-06 | `GET /api/refresh-status` retorna estat (idle/running/done/error) amb last_run, total, by_grado, duration_seconds, errors | pipeline.run() ja retorna total/by_grado/duration_seconds/errors — cal afegir last_run i estat |
| API-07 | `GET /health` retorna `{"status": "ok"}` sense autenticació | Trivial en Flask |
| API-08 | CORS habilitat per a totes les origins | Verificat: `flask-cors` 6.0.2 disponible; `CORS(app)` a app.py ja fet |
| API-09 | `ADMIN_TOKEN` llegit de variable d'entorn via `.env` | Verificat: `python-dotenv` 1.2.2; `load_dotenv()` ja cridat a app.py |

</phase_requirements>

---

## Summary

La Fase 4 afegeix les rutes REST a un `app.py` que ara és un stub mínim (11 línies). Flask 3.1.3 està instal·lat, `CORS(app)` i `load_dotenv()` ja estan cridats. El pipeline `scrapers.pipeline.run()` retorna el dict estructurat que necessita `/api/refresh-status`. Els dos reptes tècnics de la fase són: (1) gestió de l'estat del thread de refresh de forma thread-safe amb un `threading.Lock` i un dict d'estat compartit, i (2) autenticació Bearer constant-time per evitar timing attacks.

La mida real de `ofertes.json` és 3,7 MB amb 12.374 registres. El temps de càrrega i serialització mesurat és ~33ms en local, perfectament assolible. No cal caching en memòria per a v1 (dades quasi-estàtiques, refresh manual).

No hi ha dependències noves a instal·lar: `flask-cors` 6.0.2 i `python-dotenv` 1.2.2 s'han instal·lat en aquesta sessió de recerca per verificar disponibilitat. Cal afegir-los al `requirements.txt` o confirmar que ja hi eren (sí, estan declarats sense versió fixa).

**Recomanació principal:** Implementar totes les rutes directament a `app.py` (sense Blueprints) — el projecte té exactament 5 endpoints, no justifica la complexitat addicional de Blueprint. Afegir un mòdul `refresh_state.py` per centralitzar l'estat compartit del thread.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Servir ofertes.json | API / Backend (Flask) | — | Lectura de fitxer + serialització JSON |
| Autenticació Bearer | API / Backend (Flask) | — | Comparació de token al servidor, mai al client |
| Lançament del pipeline | API / Backend (Flask thread) | — | Thread separat al mateix procés Flask |
| Estat del refresh | API / Backend (memòria del procés) | — | Dict compartit + Lock, no persistit |
| CORS | API / Backend (Flask middleware) | — | flask-cors gestiona headers automàticament |
| Health check | API / Backend (Flask) | — | Endpoint sense lògica |

---

## Standard Stack

### Core (ja instal·lat)

| Llibreria | Versió | Propòsit | Per què estàndard |
|-----------|--------|----------|-------------------|
| Flask | 3.1.3 | Framework web | Decisió del projecte; ja instal·lat |
| flask-cors | 6.0.2 | Headers CORS automàtics | `CORS(app)` ja a app.py |
| python-dotenv | 1.2.2 | Carregar `.env` | `load_dotenv()` ja a app.py |
| threading (stdlib) | Python 3.13 stdlib | Thread + Lock per al refresh | Sense dependències externes |
| os / json (stdlib) | Python 3.13 stdlib | Lectura fitxer + serialització | Sense dependències externes |

[VERIFIED: pip3 list output + python3 -c "import flask; print(flask.__version__)"]

### No instal·lar (fora d'abast)

| Alternativa | Per què no |
|-------------|------------|
| Celery / Redis | Overkill per a un únic endpoint admin amb ús ocasional |
| Flask-RESTful | Innecessari per a 5 endpoints simples |
| asyncio / gevent | Complexitat sense benefici mesurable per a aquest cas |
| Gunicorn (ara) | Fase de desplegament, no Fase 4 |

---

## Architecture Patterns

### System Architecture Diagram

```
Client Browser / curl
        │
        ▼
  Flask app.py
  ├── GET /health ──────────────────────────────→ {"status": "ok"}
  │
  ├── GET /api/ofertes
  │       │
  │       ├── ofertes.json existeix? ──NO──→ 503 {"error": "..."}
  │       └── SÍ ──→ json.load() → jsonify() → 200 [array]
  │
  ├── GET /api/refresh-status
  │       └── _state dict (thread-safe read) → jsonify(state)
  │
  └── POST /api/admin/refresh
          │
          ├── Auth check: Authorization: Bearer <TOKEN>
          │       ├── Incorrecte ──→ 401
          │       └── Correcte ──→ continua
          │
          ├── Lock check: _lock.acquire(blocking=False)
          │       ├── False (ja en curs) ──→ 409
          │       └── True ──→ llança Thread
          │
          └── Thread (daemon=True)
                  │
                  ├── Crida pipeline.run()
                  │       ├── Èxit ──→ _state = {status: done, total, by_grado, ...}
                  │       └── Excepció ──→ _state = {status: error, errors: [...]}
                  └── Allibera _lock (finally)

Retorna immediatament: {"status": "started"}
```

### Estructura de fitxers recomanada

```
fp-cercador/backend/
├── app.py              # Flask app + totes les rutes (ampliat)
├── refresh_state.py    # _state dict + _lock (compartit entre rutes)
├── requirements.txt    # sense canvis (dependències ja declarades)
├── .env.example        # sense canvis
├── data/
│   └── ofertes.json    # 3.7 MB, 12.374 registres
├── scrapers/
│   ├── pipeline.py     # run() — sense modificacions
│   └── ...
└── tests/
    ├── test_api.py     # NOU — tests de les rutes Flask
    └── ...
```

### Pattern 1: Refresh State Module (thread-safe shared state)

**Què:** Mòdul separat amb el dict d'estat i el Lock. Evita importacions circulars i facilita el mock als tests.

**Quan usar:** Sempre que un endpoint escrigui i un altre llegeixi estat compartit en un entorn multi-thread.

```python
# refresh_state.py
# Source: stdlib threading docs + patró estàndard Flask
import threading

_lock = threading.Lock()

_state = {
    "status": "idle",       # idle | running | done | error
    "last_run": None,       # ISO 8601 string o null
    "total": None,
    "by_grado": None,
    "duration_seconds": None,
    "errors": [],
}

def get_state() -> dict:
    """Retorna una còpia de l'estat actual (thread-safe per a lectures simples de dict)."""
    return dict(_state)

def set_state(**kwargs) -> None:
    """Actualitza camps de l'estat (cridar dins el thread de refresh)."""
    _state.update(kwargs)
```

[VERIFIED: threading.Lock comportament confirmat amb python3 -c "import threading; lock = threading.Lock(); print(lock.acquire(blocking=False)); print(lock.acquire(blocking=False))"]

### Pattern 2: Autenticació Bearer constant-time

**Què:** Comparació de token amb `hmac.compare_digest` per evitar timing attacks.

**Quan usar:** Sempre que es compari un secret/token rebut per l'usuari.

```python
# app.py — fragment endpoint refresh
# Source: Python docs hmac.compare_digest + OWASP timing attack prevention
import hmac
import os

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

def _check_auth(request) -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth[7:]
    return hmac.compare_digest(provided, ADMIN_TOKEN)
```

[VERIFIED: python3 -c "import hmac; print(hmac.compare_digest('abc','abc'))"]

### Pattern 3: Background thread amb Lock per a 409

```python
# app.py — POST /api/admin/refresh
# Source: stdlib threading docs
import threading
from datetime import datetime, timezone
from scrapers import pipeline
from refresh_state import _lock, set_state

@app.route("/api/admin/refresh", methods=["POST"])
def admin_refresh():
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    acquired = _lock.acquire(blocking=False)
    if not acquired:
        return jsonify({"error": "Refresh already running"}), 409

    def _run():
        try:
            set_state(status="running", last_run=datetime.now(timezone.utc).isoformat(), errors=[])
            result = pipeline.run()
            set_state(
                status="done",
                total=result["total"],
                by_grado=result["by_grado"],
                duration_seconds=result["duration_seconds"],
                errors=result["errors"],
            )
        except Exception as exc:
            set_state(status="error", errors=[str(exc)])
        finally:
            _lock.release()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"status": "started"}), 200
```

[VERIFIED: patró Lock.acquire(blocking=False) + Thread(daemon=True) confirmat amb python3]

### Pattern 4: Servir ofertes.json

```python
# app.py — GET /api/ofertes
# Source: Flask 3.x docs + mesures de rendiment locals
import json, os
from flask import abort, current_app

DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "ofertes.json")
)

@app.route("/api/ofertes")
def get_ofertes():
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "Data not available. Run /api/admin/refresh first."}), 503
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data), 200
```

**Nota de rendiment:** Mesurat localment: `json.load()` = 20ms, `jsonify()` = 13ms. Total ~33ms per a 12.374 registres / 3.7MB. Acceptable per a v1 sense caching. [VERIFIED: python3 timing test]

### Anti-Patrons a evitar

- **Llegir ADMIN_TOKEN en cada request:** `os.environ.get()` en cada crida és correcte, però si `load_dotenv()` no s'executa, el token serà buit. Millor llegir-lo un cop a l'inici del mòdul i aturar l'app si és buit.
- **Lock sense `finally`:** Si el thread falla sense alliberar el lock, l'app quedarà bloquejada per sempre en estat "running". El `finally: _lock.release()` és obligatori.
- **`Thread(daemon=False)`:** Un thread no-daemon evita que Flask pugui aturar-se mentre el pipeline s'executa.
- **`string == token` en comptes de `hmac.compare_digest`:** Vulnerable a timing attacks. Usar sempre `hmac.compare_digest`.
- **Blueprint per a 5 endpoints:** Complexitat innecessària. Rutes directament a `app.py`.

---

## Don't Hand-Roll

| Problema | No construir | Usar | Per què |
|----------|-------------|------|---------|
| CORS headers | Headers manuals | `flask-cors` `CORS(app)` | Preflight OPTIONS, varies headers |
| Timing-safe comparison | `token == secret` | `hmac.compare_digest` | Timing attack en comparació naïve |
| Thread-safe state | Locks manuals complexos | `threading.Lock` + dict simple | Suficient per a un únic thread de refresh |
| Variables d'entorn | `os.environ` + parsing manual | `python-dotenv` `load_dotenv()` | Suport `.env` file, ja cridat a app.py |

---

## Common Pitfalls

### Pitfall 1: ADMIN_TOKEN buit sense avís

**Què passa:** Si `.env` no existeix o `ADMIN_TOKEN` no està definit, `os.environ.get("ADMIN_TOKEN", "")` retorna `""`. Qualsevol request amb `Authorization: Bearer ` (string buit) passarà l'autenticació.

**Per què passa:** `load_dotenv()` no llança error si `.env` no existeix.

**Com evitar:** Afegir un guard a l'inici de l'app:
```python
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    raise RuntimeError("ADMIN_TOKEN not set. Create .env from .env.example.")
```

**Senyals d'alerta:** Tests passen amb token buit; el servidor arranca sense errors.

### Pitfall 2: Lock no alliberat si el pipeline llança excepció

**Què passa:** L'app queda atascada en estat "running" per sempre. Cap nou refresh és possible fins a reiniciar el servidor.

**Per què passa:** Si `pipeline.run()` llança una excepció i no hi ha `finally`, el lock roman adquirit.

**Com evitar:** El bloc `try/except/finally` amb `_lock.release()` al `finally` és obligatori.

### Pitfall 3: `DATA_PATH` resolt des del cwd, no des del fitxer

**Què passa:** Si Flask s'arrenca des d'un directori diferent de `backend/`, la ruta relativa `data/ofertes.json` apunta a un lloc incorrecte.

**Per què passa:** Rutes relatives usen el cwd del procés, no la ubicació del fitxer.

**Com evitar:** Usar `os.path.dirname(__file__)` com ja fa `pipeline.py`. [VERIFIED: pipeline.py usa DATA_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'ofertes.json'))]

### Pitfall 4: jsonify retorna llista directament (Flask 3.x)

**Què passa:** En Flask 2.x, `jsonify([...])` pot fallar. En Flask 3.x, és vàlid. Si es fa downgrade, cal `jsonify({"data": [...]})`.

**Per què passa:** Canvi de comportament entre versions.

**Com evitar:** Quedar-se amb Flask 3.1.3 (version fixada efectivament). Retornar l'array directament: `return jsonify(data), 200`. [VERIFIED: Flask 3.1.3 instal·lat]

### Pitfall 5: Flask test_client i imports circulars de `refresh_state`

**Què passa:** Si `refresh_state.py` importa de `app.py` o viceversa de forma circular, els tests falen amb `ImportError`.

**Com evitar:** `refresh_state.py` no importa res de Flask ni de `app.py`. Dependència unidireccional: `app.py → refresh_state.py`.

---

## Code Examples

### Test d'integració Flask (patró amb test_client)

```python
# tests/test_api.py — exemple de patró de test
# Source: Flask 3.x testing docs https://flask.palletsprojects.com/en/3.1.x/testing/
import pytest
import os
import unittest.mock as mock

@pytest.fixture
def client(tmp_path):
    os.environ["ADMIN_TOKEN"] = "test-token"
    # Evitar importació de pipeline real
    with mock.patch("scrapers.pipeline.run") as mock_run:
        mock_run.return_value = {
            "total": 100, "by_grado": {"A": 100},
            "duration_seconds": 1.0, "errors": []
        }
        from app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}

def test_ofertes_503_when_no_file(client, tmp_path):
    with mock.patch("app.os.path.exists", return_value=False):
        r = client.get("/api/ofertes")
        assert r.status_code == 503

def test_refresh_401_wrong_token(client):
    r = client.post("/api/admin/refresh",
                    headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401

def test_refresh_409_while_running(client):
    import refresh_state
    # Adquirir lock manualment per simular procés en curs
    refresh_state._lock.acquire()
    try:
        r = client.post("/api/admin/refresh",
                        headers={"Authorization": "Bearer test-token"})
        assert r.status_code == 409
    finally:
        refresh_state._lock.release()
```

[VERIFIED: Flask test_client comportament confirmat amb python3]

---

## Validation Architecture

### Test Framework

| Propietat | Valor |
|-----------|-------|
| Framework | pytest (ja instal·lat com a dep de dev) |
| Config file | cap (pytest descobreix automàticament `tests/`) |
| Comanda ràpida | `cd fp-cercador/backend && python3 -m pytest tests/test_api.py -q` |
| Suite completa | `cd fp-cercador/backend && python3 -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Comportament | Tipus test | Comanda automatitzada | Fitxer existeix? |
|--------|-------------|------------|----------------------|------------------|
| API-01 | GET /api/ofertes retorna 200 + array JSON | unit | `pytest tests/test_api.py::test_ofertes_200 -x` | ❌ Wave 0 |
| API-02 | GET /api/ofertes retorna 503 sense fitxer | unit | `pytest tests/test_api.py::test_ofertes_503 -x` | ❌ Wave 0 |
| API-03 | POST /api/admin/refresh retorna `{"status":"started"}` | unit | `pytest tests/test_api.py::test_refresh_started -x` | ❌ Wave 0 |
| API-04 | POST /api/admin/refresh 401 amb token incorrecte | unit | `pytest tests/test_api.py::test_refresh_401 -x` | ❌ Wave 0 |
| API-05 | POST /api/admin/refresh 409 si procés en curs | unit | `pytest tests/test_api.py::test_refresh_409 -x` | ❌ Wave 0 |
| API-06 | GET /api/refresh-status retorna estat complet | unit | `pytest tests/test_api.py::test_refresh_status -x` | ❌ Wave 0 |
| API-07 | GET /health retorna `{"status":"ok"}` | unit | `pytest tests/test_api.py::test_health -x` | ❌ Wave 0 |
| API-08 | CORS headers presents a les respostes | unit | `pytest tests/test_api.py::test_cors_headers -x` | ❌ Wave 0 |
| API-09 | ADMIN_TOKEN llegit de .env | unit | `pytest tests/test_api.py::test_admin_token_from_env -x` | ❌ Wave 0 |

### Sampling Rate

- **Per commit de tasca:** `cd fp-cercador/backend && python3 -m pytest tests/test_api.py -q`
- **Per merge de wave:** `cd fp-cercador/backend && python3 -m pytest -q` (55 tests existents + nous)
- **Phase gate:** Suite completa verda abans de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_api.py` — cobreix API-01 a API-09 (9 tests nous mínim)
- [ ] `refresh_state.py` — mòdul d'estat compartit (creat a Wave 1, referenciat als tests)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | sí (admin endpoint) | `hmac.compare_digest` + Bearer token |
| V3 Session Management | no | No hi ha sessions |
| V4 Access Control | sí | Verificació token abans de llançar pipeline |
| V5 Input Validation | parcialment | Token és string simple; no hi ha body JSON a validar |
| V6 Cryptography | no | Token no es guarda ni es xifra |

### Known Threat Patterns

| Pattern | STRIDE | Mitigació estàndard |
|---------|--------|---------------------|
| Timing attack al token comparison | Spoofing | `hmac.compare_digest` en lloc de `==` |
| Token buit passa autenticació | Elevation of Privilege | Guard `if not ADMIN_TOKEN: raise RuntimeError(...)` a l'inici |
| Refresh flood (múltiples POST simultanis) | DoS | `threading.Lock` retorna 409 si ja en curs |
| ADMIN_TOKEN al repositori | Information Disclosure | `.env` a `.gitignore` (ja configurat Fase 1) |

---

## Environment Availability

| Dependència | Requerida per | Disponible | Versió | Fallback |
|-------------|--------------|-----------|--------|----------|
| Python 3 | runtime | ✓ | 3.13.0 | — |
| Flask | framework web | ✓ | 3.1.3 | — |
| flask-cors | CORS headers | ✓ | 6.0.2 | — |
| python-dotenv | carregar .env | ✓ | 1.2.2 | — |
| pytest | tests | ✓ | instal·lat (Fase 2) | — |
| ofertes.json | GET /api/ofertes | ✓ | 3.7MB, 12.374 reg. | 503 si no existeix |

Cap dependència bloquejant. Totes disponibles. [VERIFIED: pip3 list + python3 import tests]

---

## Open Questions

1. **Cal reiniciar `_state` entre tests?**
   - Sabem: `refresh_state._state` és un dict mutable de mòdul — persisteix entre tests del mateix procés.
   - No clar: si cada test necessita un `client` fixture que reimporti o resetegi l'estat.
   - Recomanació: afegir un fixture `autouse` que restableixi `_state` i alliberi `_lock` al setUp/tearDown de cada test.

2. **Cal retornar `last_run` com a ISO 8601 o timestamp Unix?**
   - Sabem: el requisit diu "last_run" sense especificar format.
   - No clar: el frontend (Fase 6) espera quin format.
   - Recomanació: ISO 8601 (`datetime.now(timezone.utc).isoformat()`) — llegible i compatible amb JS `new Date()`.

3. **Flask en mode debug ha de quedar activat?**
   - Sabem: `app.run(debug=True)` és el stub actual.
   - Recomanació: Preservar `debug=True` per a Fase 4 (dev local). Fase de desplegament ho configurarà via Gunicorn.

---

## Assumptions Log

| # | Claim | Secció | Risc si és incorrecte |
|---|-------|--------|----------------------|
| A1 | `refresh_state.py` com a mòdul separat és l'estructura correcta | Architecture Patterns | Baix — l'alternativa (tot a app.py amb globals) funciona igualment però és menys testable |
| A2 | No cal caching en memòria de `ofertes.json` per a v1 | Pattern 4 | Baix — 33ms de lectura és negligible per a ús ocasional |
| A3 | El thread de refresh és daemon (`daemon=True`) | Pattern 3 | Mig — si és `False`, Flask no pot aturar-se mentre el pipeline corre; si és `True`, el pipeline s'atura si el procés principal surt |

---

## Sources

### Primary (HIGH confidence)

- Flask 3.1.3 instal·lat localment — `python3 -c "import flask; print(flask.__version__)"` → 3.1.3
- stdlib `threading` — documentació oficial Python 3.13, comportament verificat amb `python3` inline
- Mesures de rendiment JSON — `python3` timing test local amb `data/ofertes.json` real (12.374 registres, 3.7MB)
- `flask-cors` 6.0.2 — `pip3 install flask-cors` confirmació
- `python-dotenv` 1.2.2 — `pip3 install python-dotenv` confirmació
- `hmac.compare_digest` — docs.python.org/3/library/hmac.html

### Secondary (MEDIUM confidence)

- Flask test_client pattern — verificat amb `python3` inline, consistent amb Flask 3.x docs
- Patró Lock + daemon Thread — confirmat amb inline tests

### Tertiary (LOW confidence)

- Cap claim LOW confidence en aquesta recerca

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — llibreries instal·lades i versions verificades
- Architecture: HIGH — patterns provats amb python3 inline, pipeline.py revisat
- Pitfalls: HIGH — basats en el codi real del projecte i comportament verificat de stdlib
- Tests: HIGH — pytest operatiu, test_client flask verificat

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (Flask 3.x estable, stdlib threading immutable)
