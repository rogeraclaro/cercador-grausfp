"""
app.py — Flask application: rutes REST per al Cercador FP España.

Rutes:
  GET    /health                       → {"status": "ok"} (sense auth)
  GET    /api/ofertes                  → array JSON dels registres (200) o 503 si no hi ha dades
  GET    /api/refresh-status           → estat del darrer refresh (idle/running/done/error)
  GET    /api/refresh-history          → historial de refreshos (sense auth, màx 20 entrades)
  GET    /api/next-refresh             → data del proper refresh programat (sense auth)
  GET    /api/feed.rss               → Feed RSS 2.0 de novetats (sense auth)
  GET    /api/feed.json              → Feed JSON Feed 1.1 de novetats (sense auth)
  GET    /api/centres                  → centres per oferta (?codigo=ADGG0408 o ?id=12664)
  GET    /api/centres/count            → dict {clau: recompte} per a totes les ofertes
  POST   /api/admin/refresh            → llança el pipeline en background (requereix Bearer token)
  GET    /api/admin/scheduler          → retorna config scheduler periòdic (Phase 6, D-08)
  POST   /api/admin/scheduler          → actualitza config scheduler (Phase 6, D-08)
  DELETE /api/admin/scheduler          → desactiva scheduler (Phase 6, D-08)
  POST   /api/admin/refresh-centres    → llança scraping de centres en background (requereix Bearer token)
  GET    /api/admin/centres-status     → estat del darrer scraping de centres (sense auth)

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

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import feed
import history
import notifier
import refresh_state
import scheduler_service
from scrapers import pipeline
from scrapers.centres_scraper import build_centres_data

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

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_CENTRES_PATH = os.path.join(_DATA_DIR, "centres.json")
_OFERTA_CENTRES_PATH = os.path.join(_DATA_DIR, "oferta_centres.json")
_centres_index: dict | None = None
_oferta_centres: dict | None = None


def _load_centres_data():
    global _centres_index, _oferta_centres
    if _centres_index is None:
        with open(_CENTRES_PATH, encoding="utf-8") as f:
            centres_list = json.load(f)
        _centres_index = {c["id"]: c for c in centres_list}
    if _oferta_centres is None:
        with open(_OFERTA_CENTRES_PATH, encoding="utf-8") as f:
            _oferta_centres = json.load(f)

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


@app.route("/api/centres")
def get_centres():
    """
    GET /api/centres?codigo=ADGG0408   (Grado C LOE)
    GET /api/centres?id=12664          (Grado D/E)
    Retorna array JSON de centres per a l'oferta indicada.
    """
    try:
        _load_centres_data()
    except FileNotFoundError:
        return jsonify({"error": "centres.json no disponible"}), 503

    clau = request.args.get("codigo") or request.args.get("id")
    if not clau:
        return jsonify({"error": "cal el paràmetre codigo o id"}), 400

    ids = _oferta_centres.get(clau, [])
    centres = [_centres_index[i] for i in ids if i in _centres_index]
    return jsonify(centres)


@app.route("/api/centres/count")
def get_centres_count():
    """GET /api/centres/count → {clau: recompte} per a totes les ofertes."""
    try:
        _load_centres_data()
    except FileNotFoundError:
        return jsonify({}), 200
    return jsonify({k: len(v) for k, v in _oferta_centres.items()})


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


@app.route("/api/feed.rss")
def api_feed_rss():
    items = feed.load_feed_items()
    rss = feed.render_rss(items)
    return app.response_class(
        rss,
        mimetype="application/rss+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.route("/api/feed.json")
def api_feed_json():
    items = feed.load_feed_items()
    data = feed.render_json_feed(items)
    return jsonify(data), 200, {"Cache-Control": "public, max-age=3600"}


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
            try:
                notifier.notify_if_new()
            except Exception as exc_n:
                logger.error("Could not send Brevo notification: %s", exc_n)
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
# Scraping de centres (manual, des del panell admin)
# ---------------------------------------------------------------------------

_centres_scrape_state: dict = {"status": "idle", "started_at": None,
                                "finished_at": None, "total_centres": None,
                                "total_ofertes": None, "error": None}
_centres_scrape_lock = threading.Lock()


@app.route("/api/admin/centres-status")
def centres_scrape_status():
    """Retorna l'estat del darrer scraping de centres (sense auth — només estat)."""
    return jsonify(_centres_scrape_state), 200


@app.route("/api/admin/refresh-centres", methods=["POST"])
def admin_refresh_centres():
    """Llança el scraping de centres en background (requereix Bearer token)."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    if not _centres_scrape_lock.acquire(blocking=False):
        return jsonify({"error": "Scraping de centres ja en curs"}), 409

    _centres_scrape_state.update(status="running",
                                  started_at=datetime.now(timezone.utc).isoformat(),
                                  finished_at=None, total_centres=None,
                                  total_ofertes=None, error=None)

    def _run():
        global _centres_index, _oferta_centres
        try:
            build_centres_data()
            # Recarrega la cache en memòria perquè les noves dades siguin visibles
            _centres_index = None
            _oferta_centres = None
            _load_centres_data()
            _centres_scrape_state.update(
                status="done",
                finished_at=datetime.now(timezone.utc).isoformat(),
                total_centres=len(_centres_index),
                total_ofertes=len(_oferta_centres),
                error=None,
            )
        except Exception as exc:
            logger.error("Centres scraping failed: %s", exc)
            _centres_scrape_state.update(status="error", error=str(exc),
                                          finished_at=datetime.now(timezone.utc).isoformat())
        finally:
            _centres_scrape_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"}), 200


# ---------------------------------------------------------------------------
# Endpoint on-demand: fitxa BOE d'un Grado C LOE
# ---------------------------------------------------------------------------

_CERT_BASE = 'https://www.todofp.es/buscadorcertificados'
_CODIGO_RE = re.compile(r'^[A-Z0-9_]{4,20}$')


@app.route('/api/certificado/<string:codigo>')
def get_certificado_detail(codigo):
    """Retorna url_boe per a un Grado C LOE (plan_antiguo=True). Fa POST a fichaCP on-demand."""
    if not _CODIGO_RE.match(codigo):
        return jsonify({'error': 'Codi invàlid'}), 400

    if not os.path.exists(DATA_PATH):
        return jsonify({'error': 'Data not available. Run /api/admin/refresh first.'}), 503

    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            ofertes = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("get_certificado_detail: no s'ha pogut llegir ofertes.json: %s", exc)
        return jsonify({'error': 'Data file is corrupt.'}), 503

    record = next(
        (r for r in ofertes if r.get('codigo') == codigo and r.get('plan_antiguo')),
        None
    )
    if not record:
        return jsonify({'error': 'Certificat no trobat o no és pla antic'}), 404

    cert_id = record.get('cert_id_buscador')
    if not cert_id:
        return jsonify({'error': 'cert_id_buscador no disponible (cal fer un refresh)'}), 404

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': _CERT_BASE + '/buscador',
        })
        session.get(_CERT_BASE + '/buscador', timeout=10)

        data = {
            'certificadoID': str(cert_id),
            'limite': '0', 'paso': '10', 'total': '1',
            'codigo': codigo, 'denominacion': '', 'familia': '0',
            'nivelFiltro': '0', 'origen': 'busquedaCP',
        }
        resp = session.post(_CERT_BASE + '/fichaCP', data=data, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        boe_link = soup.find('a', class_='enlace-ficha-boe',
                             href=re.compile(r'boe\.es'))
        url_boe = boe_link['href'] if boe_link else None

        return jsonify({'codigo': codigo, 'url_boe': url_boe})

    except Exception as exc:
        logger.error("get_certificado_detail: error cridant fichaCP per %s: %s", codigo, exc)
        return jsonify({'error': str(exc)}), 502


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Debug NOMÉS en desenvolupament explícit: FLASK_DEBUG=1 python app.py
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
