"""
app.py — Flask application: rutes REST per al Cercador FP España.

Rutes:
  GET  /health                → {"status": "ok"} (sense auth)
  GET  /api/ofertes           → array JSON dels registres (200) o 503 si no hi ha dades
  GET  /api/refresh-status    → estat del darrer refresh (idle/running/done/error)
  POST /api/admin/refresh     → llança el pipeline en background (requereix Bearer token)

Decisions de disseny:
  - Sense Blueprints: 4 rutes no justifiquen la complexitat addicional
  - refresh_state.py: mòdul separat per a l'estat compartit (evita circulars)
  - hmac.compare_digest: comparació constant-time per evitar timing attacks
  - Thread(daemon=True): el pipeline no bloqueja l'aturada del servidor
  - DATA_PATH relatiu a __file__: correcte independentment del cwd de l'execució
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

import refresh_state
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


@app.route("/api/admin/refresh", methods=["POST"])
def admin_refresh():
    """API-03 / API-04 / API-05: Llança el pipeline en background si el token és vàlid."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    acquired = refresh_state._lock.acquire(blocking=False)
    if not acquired:
        return jsonify({"error": "Refresh already running"}), 409

    def _run():
        try:
            refresh_state.set_state(
                status="running",
                last_run=datetime.now(timezone.utc).isoformat(),
                errors=[],
            )
            result = pipeline.run()
            refresh_state.set_state(
                status="done",
                total=result["total"],
                by_grado=result["by_grado"],
                duration_seconds=result["duration_seconds"],
                errors=result["errors"],
            )
        except Exception as exc:
            logger.error("Pipeline refresh failed: %s", exc)
            refresh_state.set_state(status="error", errors=[str(exc)])
        finally:
            refresh_state._lock.release()

    try:
        t = threading.Thread(target=_run, daemon=True)
        t.start()
    except Exception as exc:
        refresh_state._lock.release()
        logger.error("Could not start refresh thread: %s", exc)
        return jsonify({"error": "Could not start refresh"}), 500

    return jsonify({"status": "started"}), 200


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)
