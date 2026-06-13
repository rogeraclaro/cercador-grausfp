"""
app.py — Flask application: rutes REST per al Cercador FP España.

Rutes:
  GET    /health                       → {"status": "ok"} (sense auth)
  GET    /api/ofertes                  → array JSON dels registres (200) o 503 si no hi ha dades
  GET    /api/refresh-status           → estat del darrer refresh (idle/running/done/error)
  GET    /api/refresh-history          → historial de refreshos (sense auth, màx 20 entrades)
  GET    /api/next-refresh             → data del proper refresh programat (sense auth)
  POST   /api/admin/refresh            → llança el pipeline en background (requereix Bearer token)
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
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import history
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
# Rutes
# ---------------------------------------------------------------------------


@app.route("/health")
def health():
    """API-07: Health check sense autenticació."""
    return jsonify({"status": "ok"}), 200


_ofertes_cache = {"mtime": None, "body": None}


@app.route("/api/ofertes")
def get_ofertes():
    """API-01 / API-02: Retorna tots els registres (cache en memòria per mtime)."""
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "Data not available. Run /api/admin/refresh first."}), 503
    try:
        mtime = os.path.getmtime(DATA_PATH)
        if _ofertes_cache["mtime"] != mtime:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                body = f.read()
            json.loads(body)  # valida abans de cachejar
            _ofertes_cache.update(mtime=mtime, body=body)
        return app.response_class(_ofertes_cache["body"], mimetype="application/json")
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("ofertes.json unreadable: %s", exc)
        return jsonify({"error": "Data file is corrupt. Run /api/admin/refresh."}), 503


@app.route("/api/refresh-status")
def refresh_status():
    """API-06: Retorna l'estat del darrer procés de refresh."""
    return jsonify(refresh_state.get_state()), 200


@app.route("/api/refresh-history")
def refresh_history():
    """Retorna l'historial de refreshos (públic, sense auth)."""
    if not os.path.exists(history.HISTORY_PATH):
        return jsonify([]), 200
    try:
        with open(history.HISTORY_PATH, "r", encoding="utf-8") as f:
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
                history.append(result)
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


@app.route("/api/next-refresh")
def next_refresh():
    """Retorna la data del proper refresh programat (públic, sense auth)."""
    next_run = scheduler_service.get_next_run_iso()
    return jsonify({"next_run": next_run}), 200


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
    # Debug NOMÉS en desenvolupament explícit: FLASK_DEBUG=1 python app.py
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
