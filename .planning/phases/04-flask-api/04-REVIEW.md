---
phase: 04-flask-api
reviewed: 2026-04-18T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - fp-cercador/backend/app.py
  - fp-cercador/backend/refresh_state.py
  - fp-cercador/backend/tests/test_api.py
findings:
  critical: 0
  warning: 6
  info: 3
  total: 9
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-04-18
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files were reviewed: the Flask application (`app.py`), the shared refresh state module (`refresh_state.py`), and the integration test suite (`test_api.py`). The overall design is clean and well-reasoned — the module decomposition, constant-time token comparison, and daemon thread usage are all correct choices.

Six warnings and three info items were found. No critical security vulnerabilities exist. The most impactful issues are: (1) a lock leak if `Thread.start()` raises in `app.py`, (2) the shallow copy in `get_state()` exposing mutable nested objects to callers, and (3) a test isolation problem where `ADMIN_TOKEN` is a module-level constant that can't be overridden via `os.environ` after first import.

---

## Warnings

### WR-01: Lock leaked if `Thread.start()` raises

**File:** `fp-cercador/backend/app.py:97-123`
**Issue:** The lock is acquired at line 97 with `refresh_state._lock.acquire(blocking=False)`. If `threading.Thread(target=_run, daemon=True).start()` raises `RuntimeError` (OS thread limit reached), the lock is held permanently — no thread will ever release it, and all future `POST /api/admin/refresh` calls will return 409 forever until the process restarts.

**Fix:**
```python
acquired = refresh_state._lock.acquire(blocking=False)
if not acquired:
    return jsonify({"error": "Refresh already running"}), 409

try:
    t = threading.Thread(target=_run, daemon=True)
    t.start()
except Exception as exc:
    refresh_state._lock.release()
    logger.error("Could not start refresh thread: %s", exc)
    return jsonify({"error": "Could not start refresh"}), 500

return jsonify({"status": "started"}), 200
```

---

### WR-02: `get_state()` shallow copy exposes mutable nested objects

**File:** `fp-cercador/backend/refresh_state.py:22-23`
**Issue:** `dict(_state)` creates a shallow copy. The `errors` list and `by_grado` dict inside `_state` are shared by reference with the returned copy. Any caller that mutates `state["errors"]` (e.g., `state["errors"].append(...)`) silently mutates the shared `_state`, bypassing the lock and corrupting state visible to other threads.

**Fix:**
```python
import copy

def get_state() -> dict:
    """Retorna una còpia profunda de l'estat actual (thread-safe)."""
    return copy.deepcopy(_state)
```
If `deepcopy` overhead is a concern (it is minimal here given the small dict), at minimum copy the list: `{**_state, "errors": list(_state["errors"]), "by_grado": dict(_state["by_grado"]) if _state["by_grado"] else None}`.

---

### WR-03: `set_state` is not protected by lock — convention, not enforcement

**File:** `fp-cercador/backend/refresh_state.py:26-28`
**Issue:** `set_state` calls `_state.update(kwargs)` without acquiring `_lock`. The docstring says "call only from the refresh thread," but nothing prevents a future caller from violating this. `dict.update()` with multiple keys is not atomic across the full update — a reader calling `get_state()` concurrently could observe a partially-updated state (e.g., `status="done"` but `total=None`).

**Fix:** Acquire the lock inside `set_state` to make it self-enforcing:
```python
def set_state(**kwargs) -> None:
    """Actualitza camps de l'estat (thread-safe)."""
    with _lock:
        _state.update(kwargs)
```
Note: if this change is made, the `finally: refresh_state._lock.release()` in `app.py` must not hold the lock when calling `set_state`, which is already the case (the `_run` thread calls `set_state` while holding the lock only via the `finally` release, but the `set_state` calls happen before `finally`). Review the call order carefully before applying.

---

### WR-04: `json.load` can raise `JSONDecodeError` — unhandled 500

**File:** `fp-cercador/backend/app.py:80-82`
**Issue:** If `ofertes.json` exists but is corrupt or partially written (e.g., interrupted refresh write), `json.load(f)` raises `json.JSONDecodeError`. Flask will return a 500 with a stack trace instead of a clean error response. This is a real scenario: a refresh pipeline could crash mid-write.

**Fix:**
```python
try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except json.JSONDecodeError as exc:
    logger.error("ofertes.json is corrupt: %s", exc)
    return jsonify({"error": "Data file is corrupt. Run /api/admin/refresh."}), 503
```

---

### WR-05: `ADMIN_TOKEN` captured at module import — test fixture `os.environ` set may not take effect

**File:** `fp-cercador/backend/tests/test_api.py:51-55`
**Issue:** `ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")` is evaluated once at module load time (app.py line 37). The `client` fixture sets `os.environ["ADMIN_TOKEN"] = "test-token"` before importing `app`, which works on the first import. However, Python caches imported modules — if `app` was already imported (e.g., by another test session fixture or import side effect), the `ADMIN_TOKEN` constant retains its original value and the fixture's assignment has no effect. Tests that depend on `"test-token"` being the active token could fail non-deterministically depending on test execution order or environment.

**Fix:** Either pass `ADMIN_TOKEN=test-token` as an environment variable before running the test suite (CI-side), or refactor `app.py` to read `ADMIN_TOKEN` at request time (not module level), or use `importlib.reload(app)` inside the fixture (fragile). The cleanest solution for tests is a `conftest.py` that sets the env var before any import:
```python
# conftest.py
import os
os.environ.setdefault("ADMIN_TOKEN", "test-token")
```

---

### WR-06: Test fixture releases lock held by a live background thread

**File:** `fp-cercador/backend/tests/test_api.py:41-46`
**Issue:** The `reset_refresh_state` fixture releases the lock unconditionally in teardown (`if refresh_state._lock.locked(): refresh_state._lock.release()`). If `test_refresh_started` starts a background thread that is still running during teardown, the fixture releases the lock from the main thread while the background thread's `finally: refresh_state._lock.release()` will then attempt to release an already-released lock, raising `RuntimeError: release unlocked lock`. This is a race condition — it passes most of the time because the mock pipeline is fast, but it can fail under load.

**Fix:** Join the background thread before teardown, or introduce a short wait after the mock-based refresh test:
```python
# In test_refresh_started, after the POST:
import time
time.sleep(0.05)  # allow daemon thread to complete with mocked pipeline
```
A more robust fix is to expose a `join()` hook or use `threading.Event` in the test to synchronize completion before teardown runs.

---

## Info

### IN-01: Direct access to private `_lock` attribute from `app.py`

**File:** `fp-cercador/backend/app.py:97,120`
**Issue:** `refresh_state._lock.acquire(blocking=False)` and `refresh_state._lock.release()` directly access a private attribute of another module. This couples `app.py` to the internal implementation of `refresh_state.py`. If the locking mechanism ever changes, `app.py` breaks silently.

**Fix:** Expose a `try_acquire()` and `release()` function pair in `refresh_state.py`:
```python
def try_acquire() -> bool:
    return _lock.acquire(blocking=False)

def release() -> None:
    _lock.release()
```
This is a minor refactor that improves encapsulation and is aligned with the module's stated design goal ("Dependència unidireccional: app.py → refresh_state.py").

---

### IN-02: `debug=True` in `__main__` entry point

**File:** `fp-cercador/backend/app.py:132`
**Issue:** `app.run(debug=True, port=5001)` — the debug flag enables the Werkzeug reloader and exposes the interactive debugger. This is only active when the file is run directly (not under gunicorn/uwsgi), so production risk is low. However, if a developer accidentally runs `python app.py` on the VPS, debug mode is active.

**Fix:**
```python
if __name__ == "__main__":
    app.run(debug=False, port=5001)
```
Or gate it on an env var: `debug=os.environ.get("FLASK_DEBUG", "0") == "1"`.

---

### IN-03: `CORS(app)` applies to all origins including admin endpoint

**File:** `fp-cercador/backend/app.py:46`
**Issue:** `CORS(app)` with no restrictions allows any origin to make cross-origin requests to `POST /api/admin/refresh`. While the endpoint is protected by a Bearer token, it expands the attack surface for CSRF-adjacent techniques slightly. For a public search API the wildcard CORS is fine; for the admin endpoint it is worth considering a restricted origin list.

**Fix:** This is a conscious design choice for simplicity and may be acceptable given the token authentication. No immediate action required. If the frontend and admin are served from known origins, consider:
```python
CORS(app, resources={r"/api/*": {"origins": ["https://your-domain.com"]}})
```

---

_Reviewed: 2026-04-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
