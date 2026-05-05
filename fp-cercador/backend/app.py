"""
app.py — Flask application: rutes REST per al Cercador FP España.

Rutes:
  GET    /health                       → {"status": "ok"} (sense auth)
  GET    /api/ofertes                  → array JSON dels registres (200) o 503 si no hi ha dades
  GET    /api/refresh-status           → estat del darrer refresh (idle/running/done/error)
  GET    /api/refresh-history          → historial de refreshos (sense auth, màx 20 entrades)
  POST   /api/admin/refresh            → llança el pipeline en background (requereix Bearer token)
  POST   /api/admin/update-cookies     → actualitza BUSCADOR_COOKIES al .env (Phase 6, D-02)
  GET    /api/admin/scheduler          → retorna config scheduler periòdic (Phase 6, D-08)
  POST   /api/admin/scheduler          → actualitza config scheduler (Phase 6, D-08)
  DELETE /api/admin/scheduler          → desactiva scheduler (Phase 6, D-08)

Decisions de disseny:
  - Sense Blueprints: rutes no justifiquen la complexitat addicional
  - refresh_state.py: mòdul separat per a l'estat compartit (evita circulars)
  - hmac.compare_digest: comparació constant-time per evitar timing attacks
  - Thread(daemon=True): el pipeline no bloqueja l'aturada del servidor
  - DATA_PATH relatiu a __file__: correcte independentment del cwd de l'execució
  - scheduler_service.py: wrapper APScheduler per al refresh periòdic (Phase 6)
"""
import hmac
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import refresh_state
import scheduler_service
from scrapers import pipeline

# ---------------------------------------------------------------------------
# Inicialització
# ---------------------------------------------------------------------------

load_dotenv()

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    raise RuntimeError("ADMIN_TOKEN not set. Create .env from .env.example.")

DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "ofertes.json")
)

ENV_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), ".env")
)

HISTORY_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "refresh_history.json")
)

HISTORY_MAX = 20

app = Flask(__name__)
CORS(app)

# Phase 6 (D-06/D-07): Arrenca APScheduler i programa el job persistit (si enabled).
scheduler_service.init_scheduler()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper d'autenticació
# ---------------------------------------------------------------------------


def _check_auth(req) -> bool:
    """Verifica el token Bearer amb comparació constant-time (evita timing attacks)."""
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth[7:]
    return hmac.compare_digest(provided, ADMIN_TOKEN)


# ---------------------------------------------------------------------------
# Helper historial de refreshos
# ---------------------------------------------------------------------------


def _compute_changes(curr: dict, prev: dict) -> dict:
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


def _append_history(result: dict) -> None:
    """Afegeix una entrada a refresh_history.json (màx HISTORY_MAX entrades)."""
    import tempfile
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "total": result.get("total"),
        "by_grado": result.get("by_grado"),
        "families": result.get("families", []),
        "denominacions": result.get("denominacions", []),
        "denominacions_by_grado": result.get("denominacions_by_grado", {}),
        "unknown_families": result.get("unknown_families", []),
        "duration_seconds": result.get("duration_seconds"),
    }
    history = []
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            history = []

    entry["changes"] = _compute_changes(entry, history[0]) if history else None

    history.insert(0, entry)
    history = history[:HISTORY_MAX]
    dir_path = os.path.dirname(HISTORY_PATH)
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=dir_path, delete=False
    ) as tmp:
        json.dump(history, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    os.replace(tmp_path, HISTORY_PATH)


# ---------------------------------------------------------------------------
# Helper escriptura atòmica al .env (D-02)
# ---------------------------------------------------------------------------


def _write_env_value(key: str, value: str, env_path: str = ENV_PATH) -> None:
    """Actualitza o afegeix KEY=value al .env de forma atòmica (os.replace)."""
    import tempfile
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
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
    dir_path = os.path.dirname(env_path) or "."
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=dir_path, delete=False
    ) as tmp:
        tmp.writelines(lines)
        tmp_path = tmp.name
    os.replace(tmp_path, env_path)


# ---------------------------------------------------------------------------
# Rutes
# ---------------------------------------------------------------------------


@app.route("/health")
def health():
    """API-07: Health check sense autenticació."""
    return jsonify({"status": "ok"}), 200


@app.route("/api/ofertes")
def get_ofertes():
    """API-01 / API-02: Retorna tots els registres de ofertes.json o 503 si no existeix."""
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "Data not available. Run /api/admin/refresh first."}), 503
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("ofertes.json is corrupt: %s", exc)
        return jsonify({"error": "Data file is corrupt. Run /api/admin/refresh."}), 503
    return jsonify(data), 200


@app.route("/api/refresh-status")
def refresh_status():
    """API-06: Retorna l'estat del darrer procés de refresh."""
    return jsonify(refresh_state.get_state()), 200


@app.route("/api/refresh-history")
def refresh_history():
    """Retorna l'historial de refreshos (públic, sense auth)."""
    if not os.path.exists(HISTORY_PATH):
        return jsonify([]), 200
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return jsonify([]), 200
    return jsonify(data), 200


@app.route("/api/admin/refresh", methods=["POST"])
def admin_refresh():
    """API-03 / API-04 / API-05: Llança el pipeline en background si el token és vàlid."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    acquired = refresh_state._lock.acquire(blocking=False)
    logger.info("admin_refresh: lock acquired=%s", acquired)
    if not acquired:
        return jsonify({"error": "Refresh already running"}), 409

    # Marcar estat "running" SÍNCRON ABANS de retornar, perquè el polling immediat
    # del client no vegi un transitori "idle" o l'estat "error" anterior (fix D-12).
    refresh_state.set_state(
        status="running",
        last_run=datetime.now(timezone.utc).isoformat(),
        total=None,
        by_grado=None,
        duration_seconds=None,
        errors=[],
    )

    def _run():
        try:
            result = pipeline.run()
            refresh_state.set_state(
                status="done",
                total=result["total"],
                by_grado=result["by_grado"],
                duration_seconds=result["duration_seconds"],
                errors=result["errors"],
            )
            try:
                _append_history(result)
            except Exception as exc_h:
                logger.error("Could not write refresh history: %s", exc_h)
        except Exception as exc:
            logger.error("Pipeline refresh failed: %s", exc)
            refresh_state.set_state(status="error", errors=[str(exc)])
        finally:
            refresh_state._lock.release()

    try:
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        logger.info("admin_refresh: thread started ident=%s", t.ident)
    except Exception as exc:
        refresh_state.set_state(status="error", errors=[f"thread start failed: {exc}"])
        refresh_state._lock.release()
        logger.error("Could not start refresh thread: %s", exc)
        return jsonify({"error": "Could not start refresh"}), 500

    return jsonify({"status": "started"}), 200


@app.route("/api/admin/update-cookies", methods=["POST"])
def admin_update_cookies():
    """D-02: Actualitza BUSCADOR_COOKIES al .env sense restart."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    raw = (body.get("cookies") or "").strip()
    # Alguns terminals escapen ! com ! en copiar cURL; normalitzar abans de guardar.
    cookies = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), raw)
    if "JSESSIONID=" not in cookies:
        return jsonify({"error": "Invalid cookies format"}), 400
    try:
        _write_env_value("BUSCADOR_COOKIES", cookies)
        os.environ["BUSCADOR_COOKIES"] = cookies
    except OSError as exc:
        logger.error("update-cookies write failed: %s", exc)
        return jsonify({"error": "Could not write .env"}), 500
    return jsonify({"status": "ok"}), 200


@app.route("/api/admin/scheduler", methods=["GET"])
def scheduler_get():
    """D-08: Retorna l'estat actual del scheduler periòdic."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    cfg = scheduler_service.load_config()
    cfg["next_run"] = scheduler_service.get_next_run_iso()
    return jsonify(cfg), 200


@app.route("/api/admin/scheduler", methods=["POST"])
def scheduler_set():
    """D-08: Actualitza la config del scheduler i la persisteix."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    try:
        validated = scheduler_service.save_config(body)
        scheduler_service.apply_config(validated)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        logger.error("scheduler save failed: %s", exc)
        return jsonify({"error": "Could not write scheduler.json"}), 500
    validated["next_run"] = scheduler_service.get_next_run_iso()
    return jsonify(validated), 200


@app.route("/api/admin/scheduler", methods=["DELETE"])
def scheduler_delete():
    """D-08: Desactiva el scheduler i elimina el job."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    cfg = scheduler_service.load_config()
    cfg["enabled"] = False
    try:
        scheduler_service.save_config(cfg)
        scheduler_service.apply_config(cfg)
    except (ValueError, OSError) as exc:
        logger.error("scheduler delete failed: %s", exc)
        return jsonify({"error": "Could not disable scheduler"}), 500
    return jsonify({"status": "disabled"}), 200


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)
