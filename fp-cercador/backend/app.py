"""
app.py — Flask application: rutes REST per al Cercador FP España.

Rutes:
  GET    /health                       → {"status": "ok"} (sense auth)
  GET    /api/ofertes                  → array JSON dels registres (200) o 503 si no hi ha dades
  GET    /api/refresh-status           → estat del darrer refresh (idle/running/done/error)
  GET    /api/refresh-history          → historial de refreshos (sense auth, màx 20 entrades)
  GET    /api/observatory              → dades agregades Observatori FP (públic)
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
  GET    /api/favorites                → favorits de l'usuari autenticat
  POST   /api/favorites                → afegeix oferta als favorits
  DELETE /api/favorites/<oferta_id>   → elimina oferta dels favorits

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
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS

import feed
import history
import itinerary
import notifier
import refresh_state
import scheduler_service
from scrapers import buscador_scraper, pipeline
from scrapers.centres_scraper import build_centres_data

# ---------------------------------------------------------------------------
# Inicialització
# ---------------------------------------------------------------------------

load_dotenv()

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    raise RuntimeError("ADMIN_TOKEN not set. Create .env from .env.example.")

SECRET_KEY = os.environ.get("SECRET_KEY", "")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5001")

DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "ofertes.json")
)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CICLOS_PATH = os.path.join(_DATA_DIR, "ciclos_fp.json")
BC_LOE_PATH = os.path.join(_DATA_DIR, "bc_loe.json")
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
CORS(app)  # wildcard per a l'API pública
_AUTH_ORIGINS = {"https://cercadorfp.com", "http://localhost:5001", "http://localhost:8080"}


def _set_auth_cors(response):
    """Afegeix headers CORS amb credentials per a les rutes /api/auth/* i /api/favorites*."""
    origin = request.headers.get("Origin", "")
    if origin in _AUTH_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


def _needs_auth_cors(path):
    return (path.startswith("/api/auth/") or path.startswith("/api/favorites")
            or path.startswith("/api/alerts") or path.startswith("/api/centres-watch"))


@app.before_request
def _auth_preflight():
    """Respon directament als preflight OPTIONS per a /api/auth/* i /api/favorites*."""
    if request.method == "OPTIONS" and _needs_auth_cors(request.path):
        from flask import make_response
        return _set_auth_cors(make_response("", 204))


@app.after_request
def _auth_cors(response):
    """Afegeix CORS amb credentials a les respostes de /api/auth/* i /api/favorites*."""
    if _needs_auth_cors(request.path):
        _set_auth_cors(response)
    return response

# Inicialitza la BD (crea les taules si no existeixen via migracions).
# Neteja les entrades antigues de login_attempts (> 1 dia) a cada restart;
# evita creixement il·limitat sense necessitat de cron extern.
import db as _db_init
_db_conn = _db_init.init_db()
_db_conn.execute(
    "DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-1 day')"
)
_db_conn.commit()
_db_conn.close()
del _db_conn, _db_init

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


def _check_admin(req) -> bool:
    """Accepta Bearer ADMIN_TOKEN (scripts) O sessió d'usuari amb is_admin=1 (UI)."""
    if _check_auth(req):
        return True
    import db as _db
    token = req.cookies.get("session")
    if not token:
        return False
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            """SELECT u.id FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > datetime('now')
               AND u.is_admin = 1 AND u.is_active = 1 AND u.deleted_at IS NULL""",
            (token,),
        )
        return bool(row)
    finally:
        conn.close()


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


@app.route("/api/observatory")
def observatory():
    """Retorna les dades agregades de l'Observatori FP (públic, sense auth)."""
    import db as _db
    try:
        conn = _db.init_db()
        rows = _db.query_observatory(conn)
        conn.close()
    except Exception as exc:
        logger.warning("observatory endpoint error: %s", exc)
        return jsonify({"error": "unavailable"}), 503

    series = [
        {
            "ts": row["ts"],
            "total": row["total"],
            "A": row["total_a"],
            "B": row["total_b"],
            "C": row["total_c"],
            "D": row["total_d"],
            "E": row["total_e"],
            "n_altes": row["n_altes"],
            "n_baixes": row["n_baixes"],
        }
        for row in rows
    ]

    current = series[-1] if series else {}

    # Darreres novetats: de refresh_history.json (les 5 darreres amb altes)
    recent_changes = []
    try:
        import json as _json
        with open(history.HISTORY_PATH, "r", encoding="utf-8") as f:
            hist = _json.load(f)
        for entry in hist[:10]:
            c = entry.get("changes") or {}
            if not c.get("has_changes"):
                continue
            recent_changes.append({
                "ts": entry["ts"],
                "new_by_grado": c.get("new_by_grado") or {},
            })
            if len(recent_changes) >= 5:
                break
    except Exception:
        pass

    return jsonify({
        "current": current,
        "series": series,
        "recent_changes": recent_changes,
    }), 200


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
    if not _check_admin(request):
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
            try:
                import alerts_service
                alerts_service.dispatch_alerts(result, base_url=BASE_URL)
            except Exception as exc_a:
                logger.error("Could not dispatch alerts: %s", exc_a)
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
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401
    cfg = scheduler_service.load_config()
    cfg["next_run"] = scheduler_service.get_next_run_iso()
    return jsonify(cfg), 200


@app.route("/api/admin/scheduler", methods=["POST"])
def scheduler_set():
    """D-08: Actualitza la config del scheduler i la persisteix."""
    if not _check_admin(request):
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
    if not _check_admin(request):
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
# Gestió d'usuaris (admin)
# ---------------------------------------------------------------------------


@app.route("/api/admin/users", methods=["GET"])
def admin_users_list():
    """Retorna la llista d'usuaris registrats (sense password_hash)."""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    conn = _db.get_db()
    try:
        rows = _db.query_all(
            conn,
            "SELECT id, email, verified, is_active, created_at FROM users WHERE deleted_at IS NULL ORDER BY created_at DESC",
        )
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/api/admin/users/<int:user_id>", methods=["PATCH"])
def admin_users_toggle(user_id):
    """Activa o desactiva un compte d'usuari."""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    body = request.get_json(silent=True) or {}
    if "is_active" not in body:
        return jsonify({"error": "Cal el camp is_active (0 o 1)"}), 400
    is_active = 1 if body["is_active"] else 0
    conn = _db.get_db()
    try:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ? AND deleted_at IS NULL",
            (is_active, user_id),
        )
        conn.commit()
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            return jsonify({"error": "Usuari no trobat"}), 404
        return jsonify({"id": user_id, "is_active": is_active}), 200
    finally:
        conn.close()


@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
def admin_users_delete(user_id):
    """Elimina permanentment un usuari i totes les seves dades (CASCADE)."""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    conn = _db.get_db()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            return jsonify({"error": "Usuari no trobat"}), 404
        return jsonify({"deleted": user_id}), 200
    finally:
        conn.close()


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
    if not _check_admin(request):
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
            try:
                import centres_watch_service
                centres_watch_service.dispatch_centres_watch(base_url=BASE_URL)
            except Exception as exc_cw:
                logger.error("Could not dispatch centres watch notifications: %s", exc_cw)
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
# Redirecció a la fitxa oficial dels Graus A/B/C (pla nou)
#
# El ministeri reassigna els 'id' interns cada cop que refà la seva BD, així que
# el ficha_id guardat al refresc queda obsolet i l'enllaç directe acaba portant
# a una fitxa equivocada. Aquest endpoint resol l'id VIU per codigo (estable)
# en el moment del clic i redirigeix, amb una cache TTL per no escanejar a cada
# petició. Vegeu el mòdul buscador_scraper per al detall del scraping.
# ---------------------------------------------------------------------------

_FICHA_BASE = 'https://www.todofp.es/buscadorgradosfp'
_FICHA_INDEX_TTL = 3600  # segons
# {codigo: id_viu}. Reconstruït quan expira el TTL o davant un miss.
_ficha_index = {"built_at": 0.0, "map": {}}
_ficha_index_lock = threading.Lock()


def _build_ficha_index() -> dict:
    """Escaneja l'API viva de todofp i retorna {codigo: id} per a tots els A/B/C."""
    data = buscador_scraper.parse_buscador_all()
    index = {}
    for records in data.values():
        for r in records:
            fid = r.get('ficha_id')
            if r.get('codigo') and fid is not None:
                index[r['codigo']] = fid
    return index


def _resolve_ficha_id(codigo: str):
    """Retorna l'id viu per codigo, reconstruint la cache si cal (amb lock)."""
    now = time.monotonic()
    cached = _ficha_index["map"].get(codigo)
    fresh = (now - _ficha_index["built_at"]) < _FICHA_INDEX_TTL
    if cached is not None and fresh:
        return cached

    with _ficha_index_lock:
        # Pot haver-se reconstruït mentre esperàvem el lock.
        now = time.monotonic()
        if (now - _ficha_index["built_at"]) >= _FICHA_INDEX_TTL or codigo not in _ficha_index["map"]:
            new_map = _build_ficha_index()
            _ficha_index.update(built_at=time.monotonic(), map=new_map)
        return _ficha_index["map"].get(codigo)


@app.route('/api/ficha-redirect')
def ficha_redirect():
    """302 cap a la fitxa oficial del Grau, resolent l'id viu per codigo.

    GET /api/ficha-redirect?grado=A&codigo=AGA_A_3050_01
    Si no es pot resoldre l'id, redirigeix a la pàgina del buscador del grau
    perquè l'usuari no acabi en una fitxa equivocada.
    """
    grado = (request.args.get('grado') or '').upper()
    codigo = request.args.get('codigo') or ''

    if grado not in ('A', 'B', 'C'):
        return jsonify({'error': 'grado ha de ser A, B o C'}), 400
    if not _CODIGO_RE.match(codigo):
        return jsonify({'error': 'Codi invàlid'}), 400

    fallback = f'{_FICHA_BASE}/buscador?grado={grado}'
    try:
        ficha_id = _resolve_ficha_id(codigo)
    except Exception as exc:
        logger.error("ficha_redirect: no s'ha pogut resoldre %s: %s", codigo, exc)
        return redirect(fallback, code=302)

    if ficha_id is None:
        logger.warning("ficha_redirect: codigo %s no trobat a l'índex viu", codigo)
        return redirect(fallback, code=302)

    return redirect(f'{_FICHA_BASE}/ficha?grado={grado}&id={ficha_id}', code=302)


# ---------------------------------------------------------------------------
# F5 — Itineraris formatius A→B (local) + C→D via ciclosFP
# ---------------------------------------------------------------------------

_itinerary_index_cache: dict = {"mtime": None, "index": None}


def _get_itinerary_index() -> dict:
    """Retorna l'índex A→B, reconstruint-lo si ofertes.json ha canviat."""
    if not os.path.exists(DATA_PATH):
        return {}
    mtime = os.path.getmtime(DATA_PATH)
    if _itinerary_index_cache["mtime"] == mtime and _itinerary_index_cache["index"]:
        return _itinerary_index_cache["index"]
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            records = json.load(f)
        idx = itinerary.build_ab_index(records)
        _itinerary_index_cache.update(mtime=mtime, index=idx)
        return idx
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("_get_itinerary_index: error: %s", exc)
        return {}


@app.route('/api/itinerari')
def api_itinerari():
    """F5: Retorna l'itinerari local per a un registre A, B o C LOE.

    GET /api/itinerari?grado=A&codigo=ADG_A_3001_01
      → {"parent_b": {"codigo": "ADG_B_3001", "denominacion": "...", "grado": "B"}}

    GET /api/itinerari?grado=B&codigo=ADG_B_3001
      → {"children_a": [{"codigo": "ADG_A_3001_01", "denominacion": "...", "grado": "A"}, ...]}

    GET /api/itinerari?grado=C&codigo=COML0110
      → {"ciclos_d": [{"denominacion": "...", "familia": "..."}]}
    """
    grado = (request.args.get('grado') or '').upper()
    codigo = request.args.get('codigo') or ''

    if grado not in ('A', 'B', 'C'):
        return jsonify({'error': 'grado ha de ser A, B o C'}), 400
    if not codigo:
        return jsonify({'error': 'falta el paràmetre codigo'}), 400

    def _serialize(r):
        return {
            'codigo': r.get('codigo'),
            'denominacion': r.get('denominacion'),
            'grado': r.get('grado'),
            'nivel': r.get('nivel'),
            'familia': r.get('familia'),
        }

    if grado == 'C':
        if not os.path.exists(CICLOS_PATH):
            return jsonify({'ciclos_d': [], 'parent_b_loe': [],
                            'warning': 'ciclos_fp.json no disponible — cal fer un refresh'}), 200
        try:
            with open(CICLOS_PATH, 'r', encoding='utf-8') as f:
                ciclos_index = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("api_itinerari C: error llegint ciclos_fp.json: %s", exc)
            return jsonify({'error': 'Error llegint dades de cicles'}), 503
        ciclos = ciclos_index.get(codigo, [])

        # B→C LOE: mòduls B LOE acreditats per aquest certificat C
        parent_b_loe: list[dict] = []
        if os.path.exists(BC_LOE_PATH):
            try:
                with open(BC_LOE_PATH, 'r', encoding='utf-8') as f:
                    bc_loe_index = json.load(f)
                uc_codes = bc_loe_index.get(codigo, [])
                if uc_codes:
                    it_idx = _get_itinerary_index()
                    b_by_uc = it_idx.get('b_by_uc', {})
                    for uc in uc_codes:
                        b_rec = b_by_uc.get(uc)
                        if b_rec:
                            parent_b_loe.append(_serialize(b_rec))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("api_itinerari C: error llegint bc_loe.json: %s", exc)

        return jsonify({'ciclos_d': ciclos, 'parent_b_loe': parent_b_loe})

    idx = _get_itinerary_index()
    if not idx:
        return jsonify({'error': 'Dades no disponibles'}), 503

    if grado == 'A':
        mock_rec = {'grado': 'A', 'codigo': codigo}
        parent = itinerary.get_parent_b(mock_rec, idx)
        return jsonify({'parent_b': _serialize(parent) if parent else None})

    # grado == 'B'
    mock_rec = {'grado': 'B', 'codigo': codigo}
    children = itinerary.get_children_a(mock_rec, idx)
    return jsonify({'children_a': [_serialize(c) for c in children]})


# ---------------------------------------------------------------------------
# Auth — /api/auth/*
# ---------------------------------------------------------------------------


def _get_session_user(req):
    """Retorna el user_id de la sessió activa, o None si no hi ha sessió vàlida."""
    import db as _db
    token = req.cookies.get("session")
    if not token:
        return None
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            """SELECT s.user_id FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > datetime('now')
               AND u.is_active = 1 AND u.deleted_at IS NULL""",
            (token,),
        )
        return row["user_id"] if row else None
    finally:
        conn.close()


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    import secrets as _secrets
    import db as _db
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timezone, timedelta
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or "@" not in email or len(password) < 8:
        return jsonify({"error": "Email o contrasenya invàlids"}), 400
    conn = _db.get_db()
    try:
        existing = _db.query_one(conn, "SELECT id FROM users WHERE email = ?", (email,))
        if existing:
            return jsonify({"error": "Aquest email ja està registrat"}), 409
        pw_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, pw_hash)
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        token = _secrets.token_hex(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'email_verify', ?)",
            (user_id, token, expires),
        )
        conn.commit()
    finally:
        conn.close()
    try:
        import email_service
        email_service.send_verification_email(email, token, BASE_URL)
    except Exception as exc:
        logger.error("Error enviant email de verificació: %s", exc)
    return jsonify({"message": "Compte creat. Revisa el teu email per verificar-lo."}), 201


@app.route("/api/auth/verify", methods=["GET"])
def auth_verify():
    import db as _db
    from flask import redirect
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "Token invàlid"}), 400
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT user_id FROM tokens WHERE token = ? AND type = 'email_verify' AND expires_at > datetime('now')",
            (token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 400
        conn.execute("UPDATE users SET verified = 1 WHERE id = ?", (row["user_id"],))
        conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
    return redirect("/?verified=1")


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    import secrets as _secrets
    import db as _db
    from werkzeug.security import check_password_hash
    from datetime import datetime, timezone, timedelta
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    ip = request.remote_addr or ""
    conn = _db.get_db()
    try:
        attempts = _db.query_one(
            conn,
            "SELECT COUNT(*) FROM login_attempts WHERE ip = ? AND success = 0 AND attempted_at > datetime('now', '-15 minutes')",
            (ip,),
        )[0]
        if attempts >= 5:
            return jsonify({"error": "Massa intents. Espera 15 minuts."}), 429
        user = _db.query_one(
            conn,
            "SELECT id, password_hash, verified, is_admin FROM users WHERE email = ? AND deleted_at IS NULL AND is_active = 1",
            (email,),
        )
        ok = bool(user and check_password_hash(user["password_hash"], password))
        conn.execute(
            "INSERT INTO login_attempts (ip, email, success) VALUES (?, ?, ?)",
            (ip, email, 1 if ok else 0),
        )
        conn.commit()
        if not ok:
            return jsonify({"error": "Email o contrasenya incorrectes"}), 401
        if not user["verified"]:
            return jsonify({"error": "Compte no verificat. Revisa el teu email."}), 403
        session_token = _secrets.token_hex(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at, ip, user_agent) VALUES (?, ?, ?, ?, ?)",
            (user["id"], session_token, expires, ip, request.headers.get("User-Agent", "")),
        )
        conn.commit()
        uid = user["id"]
        is_admin = bool(user["is_admin"])
    finally:
        conn.close()
    resp = jsonify({"user": {"id": uid, "email": email, "is_admin": is_admin}})
    secure = not app.debug
    resp.set_cookie(
        "session", session_token,
        httponly=True, secure=secure, samesite="Lax",
        max_age=30 * 24 * 3600,
    )
    return resp


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    import db as _db
    token = request.cookies.get("session")
    if token:
        conn = _db.get_db()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()
    resp = jsonify({"message": "Sessió tancada"})
    resp.set_cookie("session", "", max_age=0)
    return resp


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        user = _db.query_one(
            conn,
            "SELECT id, email, is_admin FROM users WHERE id = ? AND deleted_at IS NULL AND is_active = 1",
            (user_id,),
        )
    finally:
        conn.close()
    if not user:
        return jsonify({"error": "Usuari no trobat"}), 404
    return jsonify({"id": user["id"], "email": user["email"], "is_admin": bool(user["is_admin"])})


@app.route("/api/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    import secrets as _secrets
    import db as _db
    from datetime import datetime, timezone, timedelta
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"message": "Si l'email existeix, rebràs un missatge."}), 200
    conn = _db.get_db()
    try:
        user = _db.query_one(
            conn, "SELECT id FROM users WHERE email = ? AND deleted_at IS NULL AND is_active = 1", (email,)
        )
        if user:
            token = _secrets.token_hex(32)
            expires = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'password_reset', ?)",
                (user["id"], token, expires),
            )
            conn.commit()
            try:
                import email_service
                email_service.send_password_reset_email(email, token, BASE_URL)
            except Exception as exc:
                logger.error("Error enviant email de reset: %s", exc)
    finally:
        conn.close()
    return jsonify({"message": "Si l'email existeix, rebràs un missatge."}), 200


@app.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    import db as _db
    from werkzeug.security import generate_password_hash
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    new_password = data.get("password") or ""
    if not token or len(new_password) < 8:
        return jsonify({"error": "Token o contrasenya invàlids"}), 400
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT user_id FROM tokens WHERE token = ? AND type = 'password_reset' AND expires_at > datetime('now')",
            (token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 400
        pw_hash = generate_password_hash(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, row["user_id"])
        )
        conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Contrasenya actualitzada correctament."})


# ---------------------------------------------------------------------------
# Favorits — /api/favorites
# ---------------------------------------------------------------------------


def _get_or_create_favorites_list(conn, user_id):
    """Retorna l'id de la llista 'Favorits' de l'usuari, creant-la si cal."""
    import db as _db
    row = _db.query_one(conn, "SELECT id FROM lists WHERE user_id = ? LIMIT 1", (user_id,))
    if row:
        return row["id"]
    conn.execute("INSERT INTO lists (user_id, name) VALUES (?, 'Favorits')", (user_id,))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


@app.route("/api/favorites", methods=["GET"])
def favorites_get():
    """Retorna els favorits de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        list_id_row = _db.query_one(conn, "SELECT id FROM lists WHERE user_id = ? LIMIT 1", (user_id,))
        if not list_id_row:
            return jsonify([]), 200
        items = _db.query_all(
            conn,
            "SELECT oferta_id, oferta_codigo, added_at FROM list_items WHERE list_id = ? ORDER BY added_at DESC",
            (list_id_row["id"],),
        )
        return jsonify([dict(r) for r in items]), 200
    finally:
        conn.close()


@app.route("/api/favorites", methods=["POST"])
def favorites_add():
    """Afegeix una oferta als favorits. Body: {oferta_id, oferta_codigo}."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    oferta_id = data.get("oferta_id")
    oferta_codigo = data.get("oferta_codigo") or None
    if not isinstance(oferta_id, int):
        return jsonify({"error": "oferta_id és obligatori i ha de ser enter"}), 400
    conn = _db.get_db()
    try:
        list_id = _get_or_create_favorites_list(conn, user_id)
        existing = _db.query_one(
            conn, "SELECT id FROM list_items WHERE list_id = ? AND oferta_id = ?", (list_id, oferta_id)
        )
        if existing:
            return jsonify({"status": "already_exists"}), 200
        conn.execute(
            "INSERT INTO list_items (list_id, oferta_id, oferta_codigo) VALUES (?, ?, ?)",
            (list_id, oferta_id, oferta_codigo),
        )
        conn.commit()
        return jsonify({"status": "added"}), 201
    finally:
        conn.close()


@app.route("/api/favorites/<int:oferta_id>", methods=["DELETE"])
def favorites_remove(oferta_id):
    """Elimina una oferta dels favorits."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        list_id_row = _db.query_one(conn, "SELECT id FROM lists WHERE user_id = ? LIMIT 1", (user_id,))
        if not list_id_row:
            return jsonify({"status": "not_found"}), 404
        conn.execute(
            "DELETE FROM list_items WHERE list_id = ? AND oferta_id = ?",
            (list_id_row["id"], oferta_id),
        )
        conn.commit()
        return "", 204
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Alertes — /api/alerts  (F3)
# ---------------------------------------------------------------------------

VALID_GRADOS = {"A", "B", "C", "D", "E"}
CENTRES_WATCH_MAX_PER_USER = 10


@app.route("/api/alerts", methods=["GET"])
def alerts_get():
    """Retorna les alertes actives i inactives de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        rows = _db.query_all(
            conn,
            "SELECT id, filter_json, active, created_at, last_sent_at FROM alerts "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/api/alerts", methods=["POST"])
def alerts_create():
    """Crea una nova alerta. Body: {"filter_json": {...}}. Màxim 10 alertes actives/usuari."""
    import db as _db
    import json as _json
    import secrets as _secrets
    from datetime import datetime, timezone, timedelta
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    filter_dict = data.get("filter_json")
    if not isinstance(filter_dict, dict):
        return jsonify({"error": "filter_json ha de ser un objecte JSON"}), 400
    criteria_keys = {"grado", "familia", "nivel", "texto"}
    if not any(filter_dict.get(k) for k in criteria_keys):
        return jsonify({"error": "L'alerta ha de tenir almenys un criteri (grado, familia, nivel o texto)"}), 400
    if filter_dict.get("grado") and filter_dict["grado"] not in VALID_GRADOS:
        return jsonify({"error": "grado ha de ser A, B, C, D o E"}), 400
    conn = _db.get_db()
    try:
        count = _db.query_one(
            conn,
            "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND active = 1",
            (user_id,),
        )[0]
        if count >= 10:
            return jsonify({"error": "Màxim 10 alertes actives per usuari"}), 429
        filter_str = _json.dumps(filter_dict, ensure_ascii=False)
        conn.execute(
            "INSERT INTO alerts (user_id, filter_json) VALUES (?, ?)",
            (user_id, filter_str),
        )
        conn.commit()
        alert_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        raw_token = _secrets.token_hex(32)
        stored_token = f"alert_{alert_id}_{raw_token}"
        expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'alert_unsubscribe', ?)",
            (user_id, stored_token, expires),
        )
        conn.commit()
        row = _db.query_one(
            conn,
            "SELECT id, filter_json, active, created_at, last_sent_at FROM alerts WHERE id = ?",
            (alert_id,),
        )
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
def alerts_delete(alert_id):
    """Esborra una alerta de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn, "SELECT id FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
        )
        if not row:
            return jsonify({"error": "Alerta no trobada"}), 404
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.execute("DELETE FROM tokens WHERE token LIKE ?", (f"alert_{alert_id}_%",))
        conn.commit()
        return "", 204
    finally:
        conn.close()


@app.route("/api/alerts/<int:alert_id>", methods=["PATCH"])
def alerts_toggle(alert_id):
    """Activa o desactiva una alerta. Body: {"active": true/false}."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    if "active" not in data:
        return jsonify({"error": "Cal el camp active"}), 400
    active = 1 if data["active"] else 0
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn, "SELECT id FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
        )
        if not row:
            return jsonify({"error": "Alerta no trobada"}), 404
        conn.execute("UPDATE alerts SET active = ? WHERE id = ?", (active, alert_id))
        conn.commit()
        updated = _db.query_one(
            conn,
            "SELECT id, filter_json, active, created_at, last_sent_at FROM alerts WHERE id = ?",
            (alert_id,),
        )
        return jsonify(dict(updated)), 200
    finally:
        conn.close()


@app.route("/api/alerts/<int:alert_id>/unsubscribe", methods=["GET"])
def alerts_unsubscribe(alert_id):
    """Baixa sense login via token signat. GET /api/alerts/<id>/unsubscribe?token=<tok>"""
    import db as _db
    from flask import redirect
    raw_token = request.args.get("token", "")
    if not raw_token:
        return jsonify({"error": "Token invàlid"}), 400
    stored_token = f"alert_{alert_id}_{raw_token}"
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT id, user_id FROM tokens WHERE token = ? AND type = 'alert_unsubscribe' "
            "AND expires_at > datetime('now')",
            (stored_token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 400
        conn.execute("UPDATE alerts SET active = 0 WHERE id = ?", (alert_id,))
        conn.execute("DELETE FROM tokens WHERE token = ?", (stored_token,))
        conn.commit()
    finally:
        conn.close()
    return redirect("/?unsubscribed=1")


# ---------------------------------------------------------------------------
# Seguiment de centres — /api/centres-watch  (F4)
# ---------------------------------------------------------------------------


@app.route("/api/centres-watch", methods=["GET"])
def centres_watch_get():
    """Retorna tots els seguiments (actius i inactius) de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        rows = _db.query_all(
            conn,
            "SELECT id, oferta_key, oferta_denom, provincia_filter, active, created_at, last_sent_at "
            "FROM centres_watch WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/api/centres-watch", methods=["POST"])
def centres_watch_create():
    """
    Crea un seguiment.
    Body: {"oferta_key": "ADGG0408", "oferta_denom": "Gestió Administrativa",
           "provincia_filter": "BARCELONA"}   (provincia_filter és opcional)
    """
    import db as _db
    import json as _json
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    oferta_key = data.get("oferta_key", "").strip()
    oferta_denom = data.get("oferta_denom", "").strip()
    provincia_filter = data.get("provincia_filter") or None
    if provincia_filter:
        provincia_filter = provincia_filter.strip().upper() or None
    if not oferta_key or not oferta_denom:
        return jsonify({"error": "oferta_key i oferta_denom són obligatoris"}), 400

    # Snapshot inicial: centres actuals per a aquesta oferta
    try:
        _load_centres_data()
        initial_ids = list(_oferta_centres.get(oferta_key, []))
    except Exception:
        initial_ids = []
    snapshot_json = _json.dumps(initial_ids)

    conn = _db.get_db()
    try:
        count = _db.query_one(
            conn,
            "SELECT COUNT(*) FROM centres_watch WHERE user_id = ? AND active = 1",
            (user_id,),
        )[0]
        if count >= CENTRES_WATCH_MAX_PER_USER:
            return jsonify({"error": "Màxim 10 seguiments actius per usuari"}), 429
        try:
            conn.execute(
                "INSERT INTO centres_watch (user_id, oferta_key, oferta_denom, provincia_filter, snapshot_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, oferta_key, oferta_denom, provincia_filter, snapshot_json),
            )
            conn.commit()
        except Exception as exc:
            if "UNIQUE" in str(exc):
                return jsonify({"error": "Ja segueixes aquest ensenyament"}), 409
            raise
        watch_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = _db.query_one(
            conn,
            "SELECT id, oferta_key, oferta_denom, provincia_filter, active, created_at, last_sent_at "
            "FROM centres_watch WHERE id = ?",
            (watch_id,),
        )
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.route("/api/centres-watch/<int:watch_id>", methods=["DELETE"])
def centres_watch_delete(watch_id):
    """Elimina un seguiment de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn, "SELECT id FROM centres_watch WHERE id = ? AND user_id = ?", (watch_id, user_id)
        )
        if not row:
            return jsonify({"error": "Seguiment no trobat"}), 404
        conn.execute("DELETE FROM centres_watch WHERE id = ?", (watch_id,))
        conn.execute("DELETE FROM tokens WHERE token LIKE ?", (f"cw_{watch_id}_%",))
        conn.commit()
        return "", 204
    finally:
        conn.close()


@app.route("/api/centres-watch/<int:watch_id>", methods=["PATCH"])
def centres_watch_toggle(watch_id):
    """Activa o desactiva un seguiment. Body: {"active": true/false}."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    if "active" not in data:
        return jsonify({"error": "Cal el camp active"}), 400
    active = 1 if data["active"] else 0
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn, "SELECT id FROM centres_watch WHERE id = ? AND user_id = ?", (watch_id, user_id)
        )
        if not row:
            return jsonify({"error": "Seguiment no trobat"}), 404
        conn.execute("UPDATE centres_watch SET active = ? WHERE id = ?", (active, watch_id))
        conn.commit()
        updated = _db.query_one(
            conn,
            "SELECT id, oferta_key, oferta_denom, provincia_filter, active, created_at, last_sent_at "
            "FROM centres_watch WHERE id = ?",
            (watch_id,),
        )
        return jsonify(dict(updated)), 200
    finally:
        conn.close()


@app.route("/api/centres-watch/<int:watch_id>/unsubscribe", methods=["GET"])
def centres_watch_unsubscribe(watch_id):
    """Baixa sense login via token a l'URL de l'email."""
    import db as _db
    token_param = request.args.get("token", "")
    if not token_param:
        return jsonify({"error": "Token requerit"}), 400
    stored_token = f"cw_{watch_id}_{token_param}"
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT user_id FROM tokens WHERE token = ? AND type = 'centres_watch_unsubscribe' "
            "AND expires_at > datetime('now')",
            (stored_token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 404
        conn.execute(
            "UPDATE centres_watch SET active = 0 WHERE id = ? AND user_id = ?",
            (watch_id, row["user_id"]),
        )
        conn.commit()
        return jsonify({"ok": True, "message": "Seguiment desactivat correctament"}), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Debug NOMÉS en desenvolupament explícit: FLASK_DEBUG=1 python app.py
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
