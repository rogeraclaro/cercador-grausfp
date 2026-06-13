"""
history.py — Persistència de l'historial públic de refreshos.

Sense imports de Flask ni d'app.py (el consumeixen tant app.py com
scheduler_service.py). Mateix patró que refresh_state.py.
"""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

HISTORY_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "refresh_history.json")
)
SNAPSHOT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "last_snapshot.json")
)
HISTORY_MAX = 20


def _load_json(path: str):
    """Retorna el contingut JSON del fitxer o None si no existeix o és invàlid."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write_atomic(data, path: str) -> None:
    """Escriu data com JSON al path de forma atòmica (tempfile + os.replace)."""
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=dir_path, delete=False
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def compute_changes(curr: dict, prev: dict) -> dict:
    """Calcula les diferències entre el refresh actual i l'anterior."""
    prev_families = set(prev.get("families") or [])
    curr_families = set(curr.get("families") or [])
    prev_by_grado = prev.get("by_grado") or {}
    curr_by_grado = curr.get("by_grado") or {}

    new_families = sorted(curr_families - prev_families)
    removed_families = sorted(prev_families - curr_families)
    all_grados = set(curr_by_grado) | set(prev_by_grado)
    grado_deltas = {
        g: (curr_by_grado.get(g) or 0) - (prev_by_grado.get(g) or 0)
        for g in sorted(all_grados)
        if (curr_by_grado.get(g) or 0) != (prev_by_grado.get(g) or 0)
    }
    total_delta = (curr.get("total") or 0) - (prev.get("total") or 0)

    prev_denoms = set(prev.get("denominacions") or [])
    curr_denoms = set(curr.get("denominacions") or [])
    new_denominacions = sorted(curr_denoms - prev_denoms)
    removed_denominacions = sorted(prev_denoms - curr_denoms)

    new_by_grado = {}
    removed_by_grado = {}
    curr_dbg = curr.get("denominacions_by_grado") or {}
    prev_dbg = prev.get("denominacions_by_grado") or {}
    for g in sorted(set(curr_dbg) | set(prev_dbg)):
        added = sorted(set(curr_dbg.get(g) or []) - set(prev_dbg.get(g) or []))
        gone  = sorted(set(prev_dbg.get(g) or []) - set(curr_dbg.get(g) or []))
        if added: new_by_grado[g] = added
        if gone:  removed_by_grado[g] = gone

    return {
        "new_families": new_families,
        "removed_families": removed_families,
        "grado_deltas": grado_deltas,
        "total_delta": total_delta,
        "new_denominacions": new_denominacions,
        "removed_denominacions": removed_denominacions,
        "new_by_grado": new_by_grado,
        "removed_by_grado": removed_by_grado,
        "has_changes": bool(new_families or removed_families or grado_deltas or new_denominacions or removed_denominacions),
    }


def append(result: dict) -> None:
    """Afegeix una entrada SLIM a l'historial i actualitza l'snapshot.

    L'snapshot (last_snapshot.json) guarda les llistes completes del
    darrer refresh — només serveixen per diffejar el refresh següent.
    Les entrades de l'historial només porten el resum + changes.
    """
    full = {
        "total": result.get("total"),
        "by_grado": result.get("by_grado"),
        "families": result.get("families", []),
        "denominacions": result.get("denominacions", []),
        "denominacions_by_grado": result.get("denominacions_by_grado", {}),
    }
    prev = _load_json(SNAPSHOT_PATH)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "total": result.get("total"),
        "by_grado": result.get("by_grado"),
        "unknown_families": result.get("unknown_families", []),
        "duration_seconds": result.get("duration_seconds"),
        "changes": compute_changes(full, prev) if prev else None,
    }
    history = _load_json(HISTORY_PATH) or []
    history.insert(0, entry)
    history = history[:HISTORY_MAX]
    _write_atomic(history, HISTORY_PATH)
    _write_atomic(full, SNAPSHOT_PATH)
