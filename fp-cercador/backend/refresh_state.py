"""
refresh_state.py — Estat compartit thread-safe per al pipeline de refresh.

Dependència unidireccional: app.py → refresh_state.py
Cap import de Flask ni de app.py per evitar importacions circulars.

Dos locks amb rols separats:
  _lock      — mutex de concurrència de refresh (adquirit per app.py, alliberat
               per _run); indica si hi ha un refresh en curs.
  _state_lock — mutex de lectura/escriptura de _state; adquirit/alliberat sempre
               en parella dins get_state/set_state.
"""
import copy
import threading

_lock = threading.Lock()
_state_lock = threading.Lock()

_state = {
    "status": "idle",         # idle | running | done | error
    "last_run": None,         # ISO 8601 string o null
    "total": None,
    "by_grado": None,
    "duration_seconds": None,
    "errors": [],
    "phase": None,             # nom de la fase en curs (només durant "running")
}


def get_state() -> dict:
    """Retorna una còpia profunda de l'estat actual (thread-safe)."""
    with _state_lock:
        return copy.deepcopy(_state)


def set_state(**kwargs) -> None:
    """Actualitza camps de l'estat (thread-safe)."""
    with _state_lock:
        _state.update(kwargs)
