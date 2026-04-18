"""
refresh_state.py — Estat compartit thread-safe per al pipeline de refresh.

Dependència unidireccional: app.py → refresh_state.py
Cap import de Flask ni de app.py per evitar importacions circulars.
"""
import threading

_lock = threading.Lock()

_state = {
    "status": "idle",         # idle | running | done | error
    "last_run": None,         # ISO 8601 string o null
    "total": None,
    "by_grado": None,
    "duration_seconds": None,
    "errors": [],
}


def get_state() -> dict:
    """Retorna una còpia superficial de l'estat actual (thread-safe per a lectures simples de dict)."""
    return dict(_state)


def set_state(**kwargs) -> None:
    """Actualitza camps de l'estat. Cridar únicament des del thread de refresh."""
    _state.update(kwargs)
