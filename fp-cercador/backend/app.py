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
  POST   /api/admin/refresh-ocupaciones → regenera ocupaciones.json (requereix Bearer token)
  GET    /api/admin/ocupaciones-status  → estat de la darrera regeneració (sense auth)
  GET    /api/favorites                → favorits de l'usuari autenticat (amb centres seleccionats)
  POST   /api/favorites                → afegeix oferta als favorits
  DELETE /api/favorites/<ref>        → elimina oferta dels favorits
  POST   /api/favorites/<ref>/centres         → marca un centre dins d'un favorit
  DELETE /api/favorites/<ref>/centres/<centre_id> → desmarca un centre d'un favorit
  POST   /api/feedback               → comentari d'usuari (anònim amb email; Pla 069)
  GET    /api/admin/feedback         → llista de comentaris (admin)
  PATCH  /api/admin/feedback/<id>    → estat i nota d'un comentari (admin)

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
import sys
import threading
import time
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS

import cd_lomloe
import fpo_ext
import feed
import og_page
import grau_page
import history
import itinerary
import itinerary_graph
import centres_inherit
import notifier
import oferta_ref
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
# Pla 077: domini públic per a canonical, og:url, sitemap i robots (sense barra final).
SITE_URL = os.environ.get("SITE_URL", "https://grausfp.es").rstrip("/")

DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "ofertes.json")
)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CICLOS_PATH = os.path.join(_DATA_DIR, "ciclos_fp.json")
BC_LOE_PATH = os.path.join(_DATA_DIR, "bc_loe.json")
BC_LOMLOE_PATH = os.path.join(_DATA_DIR, "bc_lomloe.json")  # Pla 057: {codigo_c: [codigo_b]}
D_MODULOS_PATH = os.path.join(_DATA_DIR, "d_modulos.json")  # Pla 058: {str(id_d): {modulos, ensenanzaFP}}
B_CONTINGUT_PATH = os.path.join(_DATA_DIR, "b_contingut.json")  # Pla 068: {codigo_b: {ecp, ra}}
A_LOE_PARES_PATH = os.path.join(_DATA_DIR, "a_loe_pares.json")  # Pla 068: {codigo_uf: [codigo_mf]}
CE_ACCES_PATH = os.path.join(_DATA_DIR, "ce_acces.json")  # Pla 074: {str(id_e): {d_ids, unmatched}}
SOC_CURSOS_PATH = os.path.join(_DATA_DIR, "soc_cursos.json")    # Pla 059: cursos FPO (SOC)
SOC_ESPECS_PATH = os.path.join(_DATA_DIR, "soc_especs.json")    # Pla 059: especialitats formatives (SOC)
SOC_CENTRES_PATH = os.path.join(_DATA_DIR, "soc_centres.json")  # Pla 059: centres de formació (SOC)
EXT_CURSOS_PATH = os.path.join(_DATA_DIR, "ext_cursos.json")   # Pla 062: cursos FPO de PIMEC i Foment
_SOC_STALE_DAYS = 7  # llindar per avisar de dades FPO velles
OCUPACIONES_PATH = os.path.join(_DATA_DIR, "ocupaciones.json")
_CENTRES_PATH = os.path.join(_DATA_DIR, "centres.json")
_OFERTA_CENTRES_PATH = os.path.join(_DATA_DIR, "oferta_centres.json")
_CENTRES_NOUS_PATH = os.path.join(_DATA_DIR, "centres_nous_per_oferta.json")
_CENTRES_REFRESH_HISTORY_PATH = os.path.join(_DATA_DIR, "centres_refresh_history.json")
SOC_REFRESH_HISTORY_PATH = os.path.join(_DATA_DIR, "soc_refresh_history.json")  # Pla 059


def _append_centres_history(entry: dict) -> None:
    """Afegeix una entrada a l'historial de scraping de centres (fail-soft).

    Historial separat del de refresh d'ofertes (history.py) perquè aquell
    mòdul està especialitzat en families/denominacions/grados — forçar-hi
    el domini de centres seria pitjor que aquesta petita duplicació.
    """
    try:
        if os.path.exists(_CENTRES_REFRESH_HISTORY_PATH):
            with open(_CENTRES_REFRESH_HISTORY_PATH, encoding="utf-8") as f:
                hist = json.load(f)
        else:
            hist = []
    except (OSError, json.JSONDecodeError):
        hist = []
    hist.insert(0, entry)
    try:
        with open(_CENTRES_REFRESH_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False)
    except OSError as exc:
        logger.error("No s'ha pogut escriure %s: %s", _CENTRES_REFRESH_HISTORY_PATH, exc)
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


_effective_oc_cache: dict = {"key": None, "data": None}


def _get_effective_oferta_centres() -> dict:
    """
    oferta_centres.json (dades crues del scraping) + centres heretats per a
    A/B LOE via el certificat C pare (Pla 056), amb clau str(id) com D/E.
    Cache invalidada per mtimes de ofertes.json, bc_loe.json i
    oferta_centres.json. No es persisteix mai: seria ~20 MB de duplicats.
    """
    _load_centres_data()

    def _mtime(path):
        return os.path.getmtime(path) if os.path.exists(path) else None

    key = (_mtime(DATA_PATH), _mtime(BC_LOE_PATH), _mtime(BC_LOMLOE_PATH),
           _mtime(_OFERTA_CENTRES_PATH), _mtime(A_LOE_PARES_PATH))
    if _effective_oc_cache["key"] == key and _effective_oc_cache["data"] is not None:
        return _effective_oc_cache["data"]

    inherited: dict = {}
    catalog = _get_catalog()
    if catalog:
        inherited = centres_inherit.build_inherited(
            catalog["records"], _get_itinerary_index(), _get_bc_loe_inverse(), _oferta_centres,
            bc_lomloe=_get_bc_lomloe(),
        )

    data = {**_oferta_centres, **inherited}
    _effective_oc_cache.update(key=key, data=data)
    return data


# ---------------------------------------------------------------------------
# Pla 076 — catàleg per ref (clau estable) i traducció dels paràmetres antics
# ---------------------------------------------------------------------------

_catalog_cache: dict = {"key": None, "data": None}


def _get_catalog() -> dict | None:
    """
    ofertes.json amb `ref` garantit (els fitxers d'abans del Pla 076 no en
    porten) i índexs per ref, per id vigent i per codi. None si no es pot llegir.
    """
    try:
        key = (DATA_PATH, os.path.getmtime(DATA_PATH))
    except OSError:
        return None
    if _catalog_cache["key"] == key:
        return _catalog_cache["data"]
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            records = oferta_ref.ensure_refs(json.load(f))
    except (OSError, ValueError) as exc:
        logger.error("_get_catalog: ofertes.json il·legible o amb refs repetits: %s", exc)
        return None
    by_codigo: dict = {}
    for r in records:
        if r.get("codigo"):
            by_codigo.setdefault(r["codigo"], []).append(r)
    data = {
        "records": records,
        "by_ref": {r["ref"]: r for r in records},
        "by_id": {r["id"]: r for r in records},
        "by_codigo": by_codigo,
    }
    _catalog_cache.update(key=key, data=data)
    return data


def _resolve_oferta(ref=None, oferta_id=None, codigo=None) -> dict | None:
    """
    Registre vigent per ref; o, per als paràmetres antics, per id (pot apuntar
    a un altre grau si hi ha hagut un refresc pel mig) i per codi, que mana si
    no coincideix amb el registre de l'id.
    """
    catalog = _get_catalog()
    if not catalog:
        return None
    if ref is not None:
        return catalog["by_ref"].get(ref) if isinstance(ref, str) else None
    rec = catalog["by_id"].get(oferta_id) if isinstance(oferta_id, int) else None
    if codigo and (not rec or rec.get("codigo") != codigo):
        rec = (catalog["by_codigo"].get(codigo) or [None])[0]
    return rec


def _ref_from_url_key(key: str) -> str | None:
    """Clau d'una ruta /api/favorites/<key>: un ref, o un id antic (només dígits)."""
    if key.isascii() and key.isdigit():
        rec = _resolve_oferta(oferta_id=int(key))
        return rec["ref"] if rec else None
    return key if oferta_ref.REF_RE.match(key) else None


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
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


def _needs_auth_cors(path):
    return (path.startswith("/api/auth/") or path.startswith("/api/favorites")
            or path.startswith("/api/fpo/favorites")
            or path.startswith("/api/alerts") or path.startswith("/api/centres-watch")
            or path.startswith("/api/feedback") or path.startswith("/api/admin/feedback"))


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
    GET /api/centres?ref=<ref>         (qualsevol grau; Pla 076)
    GET /api/centres?codigo=ADGG0408   (antic: codi del grau)
    GET /api/centres?id=12664          (antic: id vigent; millor esforç)
    Retorna array JSON de centres per a l'oferta indicada.
    """
    try:
        oferta_centres = _get_effective_oferta_centres()
    except FileNotFoundError:
        return jsonify({"error": "centres.json no disponible"}), 503

    clau = request.args.get("ref")
    if not clau and (request.args.get("codigo") or request.args.get("id")):
        id_ = request.args.get("id") or ""
        rec = _resolve_oferta(oferta_id=int(id_) if id_.isascii() and id_.isdigit() else None,
                              codigo=request.args.get("codigo"))
        clau = rec["ref"] if rec else request.args.get("codigo")
    if not clau:
        return jsonify({"error": "cal el paràmetre ref"}), 400

    ids = oferta_centres.get(clau, [])
    centres = [_centres_index[i] for i in ids if i in _centres_index]
    return jsonify(centres)


@app.route("/api/centres/count")
def get_centres_count():
    """GET /api/centres/count → {clau: recompte} per a totes les ofertes (heretats inclosos)."""
    try:
        oferta_centres = _get_effective_oferta_centres()
    except FileNotFoundError:
        return jsonify({}), 200
    return jsonify({k: len(v) for k, v in oferta_centres.items()})


@app.route("/api/centres-refresh-history")
def get_centres_refresh_history():
    """
    GET /api/centres-refresh-history → historial paginat (més recent
    primer) del scraping de centres. Públic, sense auth (mateix criteri
    que /api/refresh-history). Query params: page, limit (mateix contracte).
    """
    if not os.path.exists(_CENTRES_REFRESH_HISTORY_PATH):
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20}), 200
    try:
        with open(_CENTRES_REFRESH_HISTORY_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20}), 200
    page, limit = _parse_pagination(request)
    start = (page - 1) * limit
    return jsonify({
        "items": data[start:start + limit],
        "total": len(data),
        "page": page,
        "limit": limit,
    }), 200


@app.route("/api/fpo-refresh-history")
def get_fpo_refresh_history():
    """Pla 059: historial paginat dels snapshots de cursos FPO (SOC). Públic."""
    if not os.path.exists(SOC_REFRESH_HISTORY_PATH):
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20}), 200
    try:
        with open(SOC_REFRESH_HISTORY_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20}), 200
    page, limit = _parse_pagination(request)
    start = (page - 1) * limit
    return jsonify({
        "items": data[start:start + limit],
        "total": len(data),
        "page": page,
        "limit": limit,
    }), 200


@app.route("/api/centres/info")
def get_centres_info():
    """
    GET /api/centres/info?ids=id1,id2,... → array de centres del catàleg,
    existeixin o no vinculats a cap oferta actualment. Pensat per mostrar
    centres que un usuari va marcar com a favorits i que ja no imparteixen
    cap grau (amb el catàleg acumulatiu, encara en tenim les dades).
    """
    try:
        _load_centres_data()
    except FileNotFoundError:
        return jsonify([]), 200
    ids = [i for i in (request.args.get("ids") or "").split(",") if i]
    return jsonify([_centres_index[i] for i in ids if i in _centres_index])


@app.route("/api/centres/nous")
def get_centres_nous():
    """
    GET /api/centres/nous → {clau: [centre_id, ...]} amb els centres que van
    aparèixer vinculats a cada oferta al darrer scraping (calculat a
    admin_refresh_centres). Buit si mai s'ha fet cap scraping des que es va
    afegir aquesta funcionalitat.
    """
    if not os.path.exists(_CENTRES_NOUS_PATH):
        return jsonify({}), 200
    try:
        with open(_CENTRES_NOUS_PATH, encoding="utf-8") as f:
            return app.response_class(f.read(), mimetype="application/json")
    except (OSError, json.JSONDecodeError):
        return jsonify({}), 200


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


def _parse_pagination(req) -> tuple[int, int]:
    """Llegeix i sanititza page/limit dels query params. page >= 1, 1 <= limit <= 100."""
    try:
        page = max(1, int(req.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = min(100, max(1, int(req.args.get("limit", 20))))
    except (TypeError, ValueError):
        limit = 20
    return page, limit


@app.route("/api/refresh-history")
def refresh_history():
    """
    Retorna l'historial de refreshos, paginat (públic, sense auth).
    Query params: page (1-indexed, default 1), limit (default 20, max 100).
    """
    if not os.path.exists(history.HISTORY_PATH):
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20}), 200
    try:
        with open(history.HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20}), 200
    page, limit = _parse_pagination(request)
    start = (page - 1) * limit
    return jsonify({
        "items": data[start:start + limit],
        "total": len(data),
        "page": page,
        "limit": limit,
    }), 200


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
    rss = feed.render_rss(items, base_url=SITE_URL)
    return app.response_class(
        rss,
        mimetype="application/rss+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.route("/api/feed.json")
def api_feed_json():
    items = feed.load_feed_items()
    data = feed.render_json_feed(items, base_url=SITE_URL)
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
        warnings=[],
        phase=None,
    )

    def _run():
        try:
            result = pipeline.run(on_progress=lambda phase: refresh_state.set_state(phase=phase))
            refresh_state.set_state(
                status="done",
                total=result["total"],
                by_grado=result["by_grado"],
                duration_seconds=result["duration_seconds"],
                errors=result["errors"],
                warnings=result.get("warnings", []),
                phase=None,
            )
            try:
                history.append(result)
            except Exception as exc_h:
                logger.error("Could not write refresh history: %s", exc_h)
            try:
                notifier.notify_if_new(SITE_URL)
            except Exception as exc_n:
                logger.error("Could not send Brevo notification: %s", exc_n)
            try:
                import alerts_service
                alerts_service.dispatch_alerts(result, base_url=BASE_URL)
            except Exception as exc_a:
                logger.error("Could not dispatch alerts: %s", exc_a)
        except Exception as exc:
            logger.error("Pipeline refresh failed: %s", exc)
            refresh_state.set_state(status="error", errors=[str(exc)], phase=None)
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
                                "total_ofertes": None, "error": None,
                                "phase": None, "phase_current": None,
                                "phase_total": None, "unique_centres": None,
                                "centres_nous": None, "centres_eliminats": None}


def _all_linked_centre_ids(oferta_centres: dict | None) -> set:
    """Unió de tots els ids de centre vinculats a alguna oferta."""
    if not oferta_centres:
        return set()
    ids: set = set()
    for lst in oferta_centres.values():
        ids.update(lst)
    return ids
_centres_scrape_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Generació de l'índex d'ocupacions (F6) — admin manual o job mensual
# ---------------------------------------------------------------------------

_ocup_build_state: dict = {
    "status": "idle", "started_at": None,
    "finished_at": None, "total_entries": None, "error": None,
}
_ocup_build_lock = threading.Lock()


@app.route("/api/admin/ocupaciones-status")
def ocupaciones_build_status():
    """Retorna l'estat de la darrera regeneració de l'índex d'ocupacions."""
    return jsonify(_ocup_build_state), 200


@app.route("/api/admin/refresh-ocupaciones", methods=["POST"])
def admin_refresh_ocupaciones():
    """Regenera ocupaciones.json en background (requereix Bearer token).

    Crida scripts/generate_ocupaciones.py com a subprocess per aïllament i per
    reutilitzar el codi existent sense moure-ho. Tarda ~2-3 min.
    Retorna 409 si ja hi ha una regeneració en curs.
    """
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    if not _ocup_build_lock.acquire(blocking=False):
        return jsonify({"error": "Regeneració d'ocupacions ja en curs"}), 409

    _ocup_build_state.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None, total_entries=None, error=None,
    )

    def _run():
        repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
        script = os.path.join(repo_root, 'scripts', 'generate_ocupaciones.py')
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True, text=True, check=True,
            )
            logger.info("refresh-ocupaciones: completat\n%s", result.stdout[-2000:])
            # Recompta les entrades del fitxer generat
            total = 0
            if os.path.exists(OCUPACIONES_PATH):
                try:
                    with open(OCUPACIONES_PATH, encoding='utf-8') as f:
                        total = len(json.load(f))
                except (OSError, json.JSONDecodeError):
                    pass
            # Invalida la cache en memòria perquè el proper /api/ocupaciones llegeixi
            # el fitxer nou.
            _ocupaciones_cache.update(mtime=None, entries=None)
            _ocup_build_state.update(
                status="done",
                finished_at=datetime.now(timezone.utc).isoformat(),
                total_entries=total, error=None,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("refresh-ocupaciones: error\n%s", exc.stderr[-2000:])
            _ocup_build_state.update(
                status="error", error=exc.stderr[-500:],
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:
            logger.error("refresh-ocupaciones: error inesperat: %s", exc)
            _ocup_build_state.update(
                status="error", error=str(exc),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        finally:
            _ocup_build_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"}), 200


# ---------------------------------------------------------------------------
# Refresc del snapshot FPO (SOC) — admin manual  (Pla 061)
# ---------------------------------------------------------------------------

_fpo_refresh_state: dict = {
    "status": "idle",          # idle | running | done | error
    "started_at": None, "finished_at": None,
    "cursos": None, "especs": None, "centres": None,
    "last_error": None,
}
_fpo_refresh_lock = threading.Lock()


@app.route("/api/admin/fpo-status")
def fpo_refresh_status():
    """Estat del darrer refresc del snapshot FPO + data de l'últim fitxer."""
    st = dict(_fpo_refresh_state)
    st["last_snapshot"] = (
        os.path.getmtime(SOC_CURSOS_PATH) if os.path.exists(SOC_CURSOS_PATH) else None
    )
    return jsonify(st), 200


def _run_fpo_refresh(data_dir):
    """Regenera els soc_*.json. Actualitza _fpo_refresh_state. Allibera el lock."""
    try:
        from scrapers.soc_scraper import build_soc_data, write_soc_data
        soc = build_soc_data()
        write_soc_data(soc, data_dir)
        for cache in (_soc_cursos_cache, _soc_especs_cache, _soc_centres_cache):
            cache.update(mtime=None, index=None)
        _soc_espec_index_cache.update(key=None, data=None)
        try:
            from scrapers.pipeline import refresh_ext_cursos
            refresh_ext_cursos(data_dir)
        except Exception as ext_exc:  # una font extra no ha de tombar el refresc del SOC
            logger.warning("refresh-fpo: PIMEC/Foment ha fallat: %s", ext_exc)
        _ext_cursos_cache.update(mtime=None, index=None)
        _ext_index_cache.update(key=None, data=None)
        n = {k: len(soc.get(k, [])) for k in ("cursos", "especs", "centres")}
        _fpo_refresh_state.update(
            status="done", finished_at=datetime.now(timezone.utc).isoformat(),
            last_error=None, **n,
        )
        logger.info("refresh-fpo: completat (%(cursos)d cursos / %(especs)d especs / "
                    "%(centres)d centres)", n)
    except Exception as exc:
        logger.error("refresh-fpo: error: %r", exc)
        try:
            from scrapers.pipeline import _notify_admin_soc_failure
            _notify_admin_soc_failure(data_dir, exc)
        except Exception as notify_exc:
            logger.warning("refresh-fpo: no s'ha pogut avisar l'admin: %s", notify_exc)
        _fpo_refresh_state.update(
            status="error", finished_at=datetime.now(timezone.utc).isoformat(),
            last_error=str(exc),
        )
    finally:
        _fpo_refresh_lock.release()


@app.route("/api/admin/refresh-fpo", methods=["POST"])
def admin_refresh_fpo():
    """Regenera els soc_*.json i ext_cursos.json (PIMEC/Foment) en background
    (no el pipeline sencer). Requereix ADMIN_TOKEN o sessió admin.
    El client consulta l'estat a GET /api/admin/fpo-status."""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    if not _fpo_refresh_lock.acquire(blocking=False):
        return jsonify({"error": "Refresc FPO ja en curs"}), 409

    data_dir = os.path.dirname(SOC_CURSOS_PATH)
    _fpo_refresh_state.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None, last_error=None,
    )
    threading.Thread(target=_run_fpo_refresh, args=(data_dir,), daemon=True).start()
    return jsonify({"status": "started"}), 200


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
                                  total_ofertes=None, error=None,
                                  phase=None, phase_current=None,
                                  phase_total=None, unique_centres=None,
                                  centres_nous=None, centres_eliminats=None)

    def _run():
        global _centres_index, _oferta_centres
        _start_time = time.time()

        def _on_progress(phase, current, total, unique_centres):
            _centres_scrape_state.update(phase=phase, phase_current=current,
                                          phase_total=total, unique_centres=unique_centres)

        try:
            try:
                _load_centres_data()
            except FileNotFoundError:
                pass  # primer scraping — no hi ha estat previ per comparar
            ids_abans = _all_linked_centre_ids(_oferta_centres)
            oferta_centres_abans = dict(_oferta_centres) if _oferta_centres else {}

            build_centres_data(on_progress=_on_progress)
            # Recarrega la cache en memòria perquè les noves dades siguin visibles
            _centres_index = None
            _oferta_centres = None
            _effective_oc_cache.update(key=None, data=None)
            _load_centres_data()

            ids_despres = _all_linked_centre_ids(_oferta_centres)
            centres_nous = ids_despres - ids_abans
            centres_eliminats = ids_abans - ids_despres

            # Diff per oferta (per resaltar centres nous a cada fitxa) — només
            # es guarden les ofertes que en tenen algun, per no inflar el fitxer.
            nous_per_oferta = {}
            for oferta_key, ids_now in _oferta_centres.items():
                ids_abans_oferta = set(oferta_centres_abans.get(oferta_key, []))
                nous_oferta = [i for i in ids_now if i not in ids_abans_oferta]
                if nous_oferta:
                    nous_per_oferta[oferta_key] = nous_oferta
            try:
                with open(_CENTRES_NOUS_PATH, "w", encoding="utf-8") as f:
                    json.dump(nous_per_oferta, f, ensure_ascii=False)
            except OSError as exc_w:
                logger.error("No s'ha pogut escriure %s: %s", _CENTRES_NOUS_PATH, exc_w)

            _append_centres_history({
                "ts": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(time.time() - _start_time, 2),
                "total_centres": len(_centres_index),
                "total_ofertes": len(_oferta_centres),
                "centres_nous": len(centres_nous),
                "centres_eliminats": len(centres_eliminats),
            })

            _centres_scrape_state.update(
                status="done",
                finished_at=datetime.now(timezone.utc).isoformat(),
                total_centres=len(_centres_index),
                total_ofertes=len(_oferta_centres),
                error=None,
                phase=None,
                centres_nous=len(centres_nous),
                centres_eliminats=len(centres_eliminats),
            )
            try:
                import centres_watch_service
                centres_watch_service.dispatch_centres_watch(base_url=BASE_URL)
            except Exception as exc_cw:
                logger.error("Could not dispatch centres watch notifications: %s", exc_cw)
        except Exception as exc:
            logger.error("Centres scraping failed: %s", exc)
            _centres_scrape_state.update(status="error", error=str(exc), phase=None,
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
_BOE_HOSTS = {'boe.es', 'www.boe.es'}


def _is_boe_url(href):
    """True només per a URLs http(s) amb host boe.es: el valor acaba a window.open al frontend."""
    if not href:
        return False
    try:
        parts = urlsplit(href.strip())
    except ValueError:
        return False
    return parts.scheme in ('http', 'https') and (parts.hostname or '') in _BOE_HOSTS


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
        boe_link = soup.find('a', class_='enlace-ficha-boe', href=_is_boe_url)
        url_boe = boe_link['href'].strip() if boe_link else None

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
# Marge mínim entre reconstruccions (també si fallen): sense ell, cada codigo
# inventat (anònim) disparava ~10 peticions a todofp sota el lock global.
_FICHA_MISS_REBUILD_FLOOR = 300  # segons
# {codigo: id_viu}. Reconstruït quan expira el TTL o davant un miss.
_ficha_index = {"built_at": 0.0, "map": {}, "last_attempt": float("-inf")}
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
        needs_rebuild = (now - _ficha_index["built_at"]) >= _FICHA_INDEX_TTL or codigo not in _ficha_index["map"]
        if needs_rebuild and (now - _ficha_index["last_attempt"]) >= _FICHA_MISS_REBUILD_FLOOR:
            _ficha_index["last_attempt"] = now
            new_map = _build_ficha_index()
            _ficha_index.update(built_at=time.monotonic(), map=new_map)
        return _ficha_index["map"].get(codigo)


@app.route('/api/og-page/<page>')
def og_page_es(page):
    """Pàgina pública amb les metadades de previsualització en castellà (nginx hi envia ?lang=es)."""
    body = og_page.render_es(page, SITE_URL)
    if body is None:
        return jsonify({'error': 'not found'}), 404
    return body, 200, {'Content-Type': 'text/html; charset=utf-8'}


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
_a_loe_pares_cache: dict = {"mtime": None, "index": None}


def _get_a_loe_pares() -> dict:
    """
    Ampliació 068: {codigo_uf: [codigo_mf, ...]} de a_loe_pares.json (pares
    reals dels A LOE segons la seva fitxa). Cache per mtime. {} si no existeix.
    """
    if not os.path.exists(A_LOE_PARES_PATH):
        return {}
    mtime = os.path.getmtime(A_LOE_PARES_PATH)
    if _a_loe_pares_cache["mtime"] == mtime and _a_loe_pares_cache["index"] is not None:
        return _a_loe_pares_cache["index"]
    try:
        with open(A_LOE_PARES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("_get_a_loe_pares: a_loe_pares.json no és un objecte — s'ignora")
            return {}
        _a_loe_pares_cache.update(mtime=mtime, index=data)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_a_loe_pares: error llegint a_loe_pares.json: %s", exc)
        return {}


def _get_itinerary_index() -> dict:
    """Retorna l'índex A→B, reconstruint-lo si ofertes.json o a_loe_pares.json han canviat."""
    if not os.path.exists(DATA_PATH):
        return {}
    pares_mtime = os.path.getmtime(A_LOE_PARES_PATH) if os.path.exists(A_LOE_PARES_PATH) else None
    mtime = (os.path.getmtime(DATA_PATH), pares_mtime)
    if _itinerary_index_cache["mtime"] == mtime and _itinerary_index_cache["index"]:
        return _itinerary_index_cache["index"]
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            records = json.load(f)
        idx = itinerary.build_ab_index(records, _get_a_loe_pares())
        _itinerary_index_cache.update(mtime=mtime, index=idx)
        return idx
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("_get_itinerary_index: error: %s", exc)
        return {}


_bc_lomloe_cache: dict = {"mtime": None, "index": None}


def _get_bc_lomloe() -> dict:
    """
    Pla 057: {codigo_c: [codigo_b, ...]} de bc_lomloe.json (C LOMLOE → mòduls B).
    Cache invalidada per mtime. {} si el fitxer no existeix o és corrupte.
    """
    if not os.path.exists(BC_LOMLOE_PATH):
        return {}
    mtime = os.path.getmtime(BC_LOMLOE_PATH)
    if _bc_lomloe_cache["mtime"] == mtime and _bc_lomloe_cache["index"] is not None:
        return _bc_lomloe_cache["index"]
    try:
        with open(BC_LOMLOE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("_get_bc_lomloe: bc_lomloe.json no és un objecte — s'ignora")
            return {}
        _bc_lomloe_cache.update(mtime=mtime, index=data)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_bc_lomloe: error llegint bc_lomloe.json: %s", exc)
        return {}


def _get_bc_lomloe_inverse() -> dict:
    """{codigo_b: [codigo_c, ...]} derivat de _get_bc_lomloe()."""
    inverse: dict = {}
    for codigo_c, b_codes in _get_bc_lomloe().items():
        for codigo_b in b_codes:
            inverse.setdefault(codigo_b, []).append(codigo_c)
    return inverse


_d_modulos_cache: dict = {"mtime": None, "index": None}


def _get_d_modulos() -> dict:
    """
    Pla 058: {str(id_d): {modulos: [{num, name}], ensenanzaFP}} de d_modulos.json.
    Cache invalidada per mtime. {} si el fitxer no existeix o és corrupte.
    """
    if not os.path.exists(D_MODULOS_PATH):
        return {}
    mtime = os.path.getmtime(D_MODULOS_PATH)
    if _d_modulos_cache["mtime"] == mtime and _d_modulos_cache["index"] is not None:
        return _d_modulos_cache["index"]
    try:
        with open(D_MODULOS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("_get_d_modulos: d_modulos.json no és un objecte — s'ignora")
            return {}
        _d_modulos_cache.update(mtime=mtime, index=data)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_d_modulos: error llegint d_modulos.json: %s", exc)
        return {}


_b_contingut_cache: dict = {"mtime": None, "index": None}


def _get_b_contingut() -> dict:
    """
    Pla 068: {codigo_b: {ecp: [{codigo, text}], ra: [{codigo, text}]}} de b_contingut.json.
    Cache invalidada per mtime. {} si el fitxer no existeix o és corrupte.
    """
    if not os.path.exists(B_CONTINGUT_PATH):
        return {}
    mtime = os.path.getmtime(B_CONTINGUT_PATH)
    if _b_contingut_cache["mtime"] == mtime and _b_contingut_cache["index"] is not None:
        return _b_contingut_cache["index"]
    try:
        with open(B_CONTINGUT_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("_get_b_contingut: b_contingut.json no és un objecte — s'ignora")
            return {}
        _b_contingut_cache.update(mtime=mtime, index=data)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_b_contingut: error llegint b_contingut.json: %s", exc)
        return {}


_cd_lomloe_cache: dict = {"key": None, "data": None}


def _get_c_lomloe_to_d() -> dict:
    """
    Pla 058: derivació C LOMLOE → [cicles D] via mòduls compartits.
    Retorna {'index': {codigo_c: [{id, shared, total}]}, 'd_by_id': {str(id): rec_d}}.
    Cache invalidada per mtimes d'ofertes.json, bc_lomloe.json i d_modulos.json.
    """
    def _mt(path):
        return os.path.getmtime(path) if os.path.exists(path) else None

    key = (_mt(DATA_PATH), _mt(BC_LOMLOE_PATH), _mt(D_MODULOS_PATH))
    if _cd_lomloe_cache["key"] == key and _cd_lomloe_cache["data"] is not None:
        return _cd_lomloe_cache["data"]
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_c_lomloe_to_d: error llegint ofertes.json: %s", exc)
        records = []
    index = cd_lomloe.build_c_lomloe_to_d(records, _get_bc_lomloe(), _get_d_modulos())
    d_by_id = {str(r['id']): r for r in records if r.get('grado') == 'D'}
    try:
        oferta_ref.ensure_refs(records)  # 'ref' als cicles D retornats (Pla 076)
    except ValueError as exc:
        logger.warning("_get_c_lomloe_to_d: sense refs: %s", exc)
    data = {'index': index, 'd_by_id': d_by_id}
    _cd_lomloe_cache.update(key=key, data=data)
    return data


# ---------------------------------------------------------------------------
# Pla 059 — FPO (SOC Catalunya): soc_*.json + /api/fpo/*
# ---------------------------------------------------------------------------

_soc_cursos_cache: dict = {"mtime": None, "index": None}
_soc_especs_cache: dict = {"mtime": None, "index": None}
_soc_centres_cache: dict = {"mtime": None, "index": None}
_soc_espec_index_cache: dict = {"key": None, "data": None}
_ext_cursos_cache: dict = {"mtime": None, "index": None}
_ext_index_cache: dict = {"key": None, "data": None}

_SOC_FITXA_CURS_URL = ("https://serveiocupacio.gencat.cat/ca/persones/vull-formar-me/"
                       "cercadors-formacio-especialitats/cercador-integrat/fitxa-curs.html")


def _read_soc_list(path: str, cache: dict) -> list:
    """Llegeix un soc_*.json (llista). Cache per mtime. [] si falta/corrupte."""
    if not os.path.exists(path):
        return []
    mtime = os.path.getmtime(path)
    if cache["mtime"] == mtime and cache["index"] is not None:
        return cache["index"]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning("_read_soc_list: %s no és una llista — s'ignora", path)
            return []
        cache.update(mtime=mtime, index=data)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_read_soc_list: error llegint %s: %s", path, exc)
        return []


def _get_soc_cursos() -> list:
    return _read_soc_list(SOC_CURSOS_PATH, _soc_cursos_cache)


def _get_soc_especs() -> list:
    return _read_soc_list(SOC_ESPECS_PATH, _soc_especs_cache)


def _get_soc_centres() -> list:
    return _read_soc_list(SOC_CENTRES_PATH, _soc_centres_cache)


def _get_ext_cursos() -> list:
    return _read_soc_list(EXT_CURSOS_PATH, _ext_cursos_cache)


def _fpo_today() -> str:
    """Data d'avui (ISO). Funció a part perquè els tests la puguin fixar (Pla 063)."""
    return date.today().isoformat()


def _fpo_families() -> dict:
    """{codi_familia: {'ca':.., 'es':..}} a partir dels soc_especs.json."""
    out: dict = {}
    for e in _get_soc_especs():
        f = e.get('familia') or {}
        if f.get('codi') and f['codi'] not in out:
            out[f['codi']] = f.get('desc') or {'ca': f['codi'], 'es': f['codi']}
    return out


def _ext_index() -> dict:
    """Índex dels cursos externs (fpo_ext.build_index). Cache per mtimes + dia (l'estat
    'finalitzat' depèn de la data)."""
    def _mt(path):
        return os.path.getmtime(path) if os.path.exists(path) else None

    key = (_mt(EXT_CURSOS_PATH), _mt(SOC_ESPECS_PATH), _fpo_today())
    if _ext_index_cache["key"] == key and _ext_index_cache["data"] is not None:
        return _ext_index_cache["data"]
    data = fpo_ext.build_index(_get_ext_cursos(), _fpo_families(), _fpo_today())
    _ext_index_cache.update(key=key, data=data)
    return data


def _fpo_llista() -> list:
    """Especialitats SOC (font='soc') + externes, ordenades per títol."""
    soc = [{**e, 'font': 'soc', 'tipus': ['Subvencionat']} for e in _soc_espec_index()['list']]
    llista = soc + _ext_index()['list']
    llista.sort(key=lambda x: ((x['titol'].get('ca') or x['codi']).lower(), x['codi']))
    return llista


def _soc_warning() -> str | None:
    if not os.path.exists(SOC_ESPECS_PATH) or not _get_soc_especs():
        return "L'oferta de cursos FPO no està disponible temporalment."
    age = time.time() - os.path.getmtime(SOC_ESPECS_PATH)
    if age > _SOC_STALE_DAYS * 86400:
        return "Les dades de cursos FPO poden estar desactualitzades."
    return None


def _soc_fitxa_url(curs: dict) -> str:
    """Enllaç a la fitxa del curs concret (centre inclòs) al cercador del SOC.

    És el mateix GET que fa el formulari `formFitxaCursos` del cercador del SOC.
    """
    from urllib.parse import quote
    return f"{_SOC_FITXA_CURS_URL}?codi_curso_seleccionado={quote(curs.get('idCurs') or '', safe='/')}"


def _soc_espec_index() -> dict:
    """
    {'list': [entrada_llista, ...], 'cursos_by_espec': {codi: [curs, ...]}}
    Només especialitats amb ≥1 curs. Cache per mtimes de cursos+especs.
    """
    def _mt(path):
        return os.path.getmtime(path) if os.path.exists(path) else None

    key = (_mt(SOC_CURSOS_PATH), _mt(SOC_ESPECS_PATH))
    if _soc_espec_index_cache["key"] == key and _soc_espec_index_cache["data"] is not None:
        return _soc_espec_index_cache["data"]

    cursos_by_espec: dict = {}
    for c in _get_soc_cursos():
        codi = (c.get('especialitat') or {}).get('codi')
        if codi:
            cursos_by_espec.setdefault(codi, []).append(c)

    llista = []
    for e in _get_soc_especs():
        codi = e.get('codi')
        cursos = cursos_by_espec.get(codi)
        if not codi or not cursos:
            continue
        llista.append({
            'codi': codi,
            'titol': e.get('titol', {'ca': '', 'es': ''}),
            'familia': e.get('familia', {}),
            'area': e.get('area', {}),
            'nivell': e.get('nivell', 0),
            'hores': e.get('hores', 0.0),
            'esCertProf': bool(e.get('esCertProf')),
            'rd': e.get('rd'),
            'programaUrl': e.get('programaUrl', ''),
            'nCursos': len(cursos),
            'comarques': sorted({c.get('comarca', '') for c in cursos if c.get('comarca')}),
            'municipis': sorted({c.get('municipi', '') for c in cursos if c.get('municipi')}),
            'estats': sorted({c.get('estat', '') for c in cursos if c.get('estat')}),
            'modalitats': sorted({c.get('modalitat', '') for c in cursos if c.get('modalitat')}),
        })
    llista.sort(key=lambda x: (x['titol'].get('ca') or x['codi']).lower())
    data = {'list': llista, 'cursos_by_espec': cursos_by_espec}
    _soc_espec_index_cache.update(key=key, data=data)
    return data


def _soc_curs_public(c: dict) -> dict:
    return {
        'idCurs': c.get('idCurs', ''),
        'titol': c.get('titol', {'ca': '', 'es': ''}),
        'centre': c.get('centre', {}),
        'dataInici': c.get('dataInici'),
        'dataFi': c.get('dataFi'),
        'estat': c.get('estat', ''),
        'modalitat': c.get('modalitat', ''),
        'fitxaUrl': _soc_fitxa_url(c),
    }


@app.route('/api/fpo/especialitats')
def api_fpo_especialitats():
    """Pla 059: especialitats FPO amb ≥1 curs actiu a Catalunya."""
    resp = {'especialitats': _fpo_llista()}
    w = _soc_warning()
    if w:
        resp['warning'] = w
    return jsonify(resp)


@app.route('/api/fpo/especialitat/<path:codi>')
def api_fpo_especialitat(codi):
    """Pla 059: detall d'una especialitat FPO (mòduls + cursos actius)."""
    if fpo_ext.is_ext_codi(codi):
        cursos = _ext_index()['cursos_by_codi'].get(codi)
        if not cursos:
            return jsonify({}), 404
        avui = _fpo_today()
        buit = {'ca': '', 'es': ''}
        return jsonify({
            'codi': codi,
            'descripcio': fpo_ext.titol_net(cursos[0].get('titol')),
            'queAprendras': buit, 'requisits': buit, 'sortides': buit,
            'moduls': [], 'programaUrl': '',
            'cursos': [fpo_ext.curs_public(c, avui) for c in cursos],
        })
    idx = _soc_espec_index()
    cursos = idx['cursos_by_espec'].get(codi)
    if not cursos:
        return jsonify({}), 404
    espec = next((e for e in _get_soc_especs() if e.get('codi') == codi), {})

    def _first_nonempty(field):
        for c in cursos:
            v = c.get(field) or {}
            if v.get('ca') or v.get('es'):
                return v
        return {'ca': '', 'es': ''}

    return jsonify({
        'codi': codi,
        'descripcio': espec.get('titol', {'ca': '', 'es': ''}),
        'queAprendras': _first_nonempty('queAprendras'),
        'requisits': _first_nonempty('requisits'),
        'sortides': _first_nonempty('sortides'),
        'moduls': espec.get('moduls', []),
        'programaUrl': espec.get('programaUrl', ''),
        'cursos': [_soc_curs_public(c) for c in cursos],
    })


@app.route('/api/fpo/by-cert')
def api_fpo_by_cert():
    """Pla 059: cursos FPO l'especialitat dels quals és un certificat de
    professionalitat concret (codi = codigo d'un Grado C de pla antic)."""
    codigo = request.args.get('codigo') or ''
    cursos = _soc_espec_index()['cursos_by_espec'].get(codigo)
    if not cursos:
        return jsonify({})
    return jsonify({
        'especialitat': codigo,
        'nCursos': len(cursos),
        'cursos': [_soc_curs_public(c) for c in cursos],
    })


_bc_loe_inverse_cache: dict = {"mtime": None, "index": None}


def _get_bc_loe_inverse() -> dict:
    """
    Retorna l'índex invers de bc_loe.json: {uc_key: [codigo_c]}.
    Cache invalidat per mtime. Retorna {} si bc_loe.json no existeix.
    """
    if not os.path.exists(BC_LOE_PATH):
        return {}
    mtime = os.path.getmtime(BC_LOE_PATH)
    if _bc_loe_inverse_cache["mtime"] == mtime and _bc_loe_inverse_cache["index"] is not None:
        return _bc_loe_inverse_cache["index"]
    try:
        with open(BC_LOE_PATH, 'r', encoding='utf-8') as f:
            bc_loe = json.load(f)
        inverse: dict = {}
        for codigo_c, uc_codes in bc_loe.items():
            for uc in uc_codes:
                inverse.setdefault(uc, []).append(codigo_c)
        _bc_loe_inverse_cache.update(mtime=mtime, index=inverse)
        return inverse
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_bc_loe_inverse: error llegint bc_loe.json: %s", exc)
        return {}


import re as _re_ocup
import unicodedata as _ud_ocup

# Diccionari CA→ES per a arrels divergents (termes comuns del domini FP).
# Claus i valors ja estan en forma normalitzada (minúscules, sense accents).
_CA_ES_TERMS: dict[str, str] = {
    # Alimentació i hoteleria
    'cuina': 'cocina', 'cuiner': 'cocinero', 'cuinera': 'cocinera',
    'pastisseria': 'pasteleria', 'hostaleria': 'hosteleria',
    'turisme': 'turismo',
    # Artesania i fusta
    'fusteria': 'carpinteria', 'fuster': 'carpintero',
    'cuir': 'cuero', 'vidre': 'vidrio',
    # Bellesa i imatge personal
    'perruqueria': 'peluqueria', 'bellesa': 'belleza',
    # Construcció i instal·lacions
    'paleta': 'albanil',
    # Comerç i màrqueting
    'comerc': 'comercio',  # comerç normalitzat: comerc (ç→c)
    'vendes': 'ventas', 'venda': 'venta',
    'publicitat': 'publicidad',
    # Educació i serveis socials
    'infermeria': 'enfermeria', 'infermer': 'enfermero', 'infermera': 'enfermera',
    # Esport i activitats físiques
    'esport': 'deporte', 'esports': 'deportes',
    # Finances i assegurances
    'assegurances': 'seguros', 'asseguranca': 'seguro',  # ç→c
    'inmobiliaria': 'inmobiliaria',  # immobiliària→inmobiliaria (doble m→m)
    # Imatge i so
    'imatge': 'imagen',
    # Seguretat i emergències
    'bombers': 'bomberos',
    # Arts i espectacle
    'dansa': 'danza', 'teatre': 'teatro', 'cinema': 'cine',
    'arts': 'artes', 'art': 'arte',
    'grafic': 'grafico',  # gràfic→grafic
    # Transport
    'transport': 'transporte',
    # Muntatge i instal·lació
    'muntatge': 'montaje', 'muntador': 'montador',
}

# Regles de sufix CA→ES (sobre text ja normalitzat, en ordre d'aplicació).
# Exemple: 'comunicacio' → 'comunicacion', 'electricitat' → 'electricidad'.
_CA_ES_SUFFIXES: list[tuple[str, str]] = [
    ('acio', 'acion'),   # -ació → -ación   (comunicació, educació, animació…)
    ('itat', 'idad'),    # -itat → -idad     (electricitat, seguretat, activitat…)
    ('ment', 'miento'),  # -ment → -miento   (manteniment, funcionament…)
    ('atge', 'aje'),     # -atge → -aje      (muntatge, emmagatzematge…)
]


def _expand_token(t: str) -> list[str]:
    """Retorna [t] + variants ES si t sembla un terme en català.

    Ordre: primer el diccionari d'arrels (prioritat), després les regles de sufix.
    Si es troba coincidència al diccionari, NO s'apliquen les regles de sufix
    (evita dobles transformacions).
    """
    if t in _CA_ES_TERMS:
        es = _CA_ES_TERMS[t]
        return [t, es] if es != t else [t]
    for ca_sfx, es_sfx in _CA_ES_SUFFIXES:
        if t.endswith(ca_sfx) and len(t) > len(ca_sfx) + 2:
            es_form = t[:-len(ca_sfx)] + es_sfx
            return [t, es_form]
    return [t]


@app.route('/api/ca-es-terms')
def api_ca_es_terms():
    """Taules d'expansió CA→ES (mateixa font que la cerca d'ocupació).

    El frontend les fa servir perquè la cerca de la taula principal accepti
    termes en català. Contingut estàtic: es pot cachejar al navegador.
    """
    resp = jsonify({
        'terms': _CA_ES_TERMS,
        'suffixes': [list(p) for p in _CA_ES_SUFFIXES],
    })
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


_ocupaciones_cache: dict = {"mtime": None, "entries": None}


def _get_ocupaciones() -> list[dict]:
    """
    Retorna la llista d'entrades ocupació→grau de ocupaciones.json.
    Cache invalidat per mtime. Retorna [] si el fitxer no existeix.
    """
    if not os.path.exists(OCUPACIONES_PATH):
        return []
    mtime = os.path.getmtime(OCUPACIONES_PATH)
    if _ocupaciones_cache["mtime"] == mtime and _ocupaciones_cache["entries"] is not None:
        return _ocupaciones_cache["entries"]
    try:
        with open(OCUPACIONES_PATH, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        _ocupaciones_cache.update(mtime=mtime, entries=entries)
        return entries
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_ocupaciones: error llegint ocupaciones.json: %s", exc)
        return []


def _norm_ocup(s: str) -> str:
    s = (s or '').lower()
    s = ''.join(c for c in _ud_ocup.normalize('NFD', s) if _ud_ocup.category(c) != 'Mn')
    s = _re_ocup.sub(r'/\s+', '/', s)
    return _re_ocup.sub(r'\s+', ' ', s).strip()


@app.route('/api/ocupaciones')
def api_ocupaciones():
    """F6: cerca de graus per ocupació/sortida professional (castellà).

    GET /api/ocupaciones?q=soldador
      → {"query": "soldador", "n": 8, "resultados": [
            {"grado": "C", "codigo": "FMEC0110", "id": 123,
             "denominacion": "...", "familia": "...", "ficha_url": null,
             "ocupaciones": ["Soldadores por TIG", ...]}, ...]}
    """
    q = request.args.get('q', '')
    tokens = [t for t in _norm_ocup(q).split() if len(t) >= 2]
    if not tokens:
        return jsonify({'query': q, 'n': 0, 'resultados': []})

    entries = _get_ocupaciones()
    # Match per paraula completa: cada token ha de ser una paraula del 'norm'.
    # Cada token s'expandeix a [original, equivalent_ES] (si és terme en català).
    token_groups = [_expand_token(t) for t in tokens]
    # Compile patterns per grup: per a cada grup, almenys una variant ha de coincidir.
    compiled_groups = [
        [_re_ocup.compile(r'\b' + _re_ocup.escape(v) + r'\b') for v in grp]
        for grp in token_groups
    ]

    grouped: dict = {}
    for e in entries:
        hay = e.get('norm', '')
        if all(any(p.search(hay) for p in grp) for grp in compiled_groups):
            key = e['codigo'] if e['grado'] == 'C' else f"{e['grado']}-{e['id']}"
            g = grouped.setdefault(key, {
                'grado': e['grado'], 'codigo': e.get('codigo'), 'id': e.get('id'),
                'denominacion': e['denominacion'], 'familia': e.get('familia', ''),
                'ficha_url': e.get('ficha_url'), 'ocupaciones': [],
            })
            g['ocupaciones'].append(e['ocupacio'])

    resultados = sorted(grouped.values(), key=lambda g: -len(g['ocupaciones']))
    return jsonify({'query': q, 'n': len(resultados), 'resultados': resultados})


@app.route('/api/a-loe-pares')
def api_a_loe_pares():
    """Ampliació 068: {codigo_uf: [codigo_mf, ...]} tal qual (badge i panell dels A LOE).
    {} si el fitxer encara no s'ha generat."""
    return jsonify(_get_a_loe_pares())


def _contingut_a(codigo: str, idx: dict) -> tuple[list, dict]:
    """
    Pla 068: B pares d'un A i "en què consisteix" l'A = el seu RA (mateix sufix,
    _A_ → _RA_) dins la fitxa del B pare, més l'ECP de tots els pares sense
    duplicats. Els B LOE no tenen RA. Retorna (pares, {'ra': … | None, 'ecp': [...]}).
    """
    parents = itinerary.get_parents_b({'grado': 'A', 'codigo': codigo}, idx)
    b_contingut = _get_b_contingut()
    ra_codigo = codigo.replace('_A_', '_RA_', 1)
    ra = None
    ecp: list = []
    for p in parents:
        b_cont = b_contingut.get(p['codigo'], {})
        ra = ra or next((x for x in b_cont.get('ra', []) if x.get('codigo') == ra_codigo), None)
        ecp += [x for x in b_cont.get('ecp', []) if x not in ecp]
    return parents, {'ra': ra, 'ecp': ecp}


@app.route('/api/itinerari')
def api_itinerari():
    """F5: Retorna l'itinerari local per a un registre A, B o C LOE.

    GET /api/itinerari?grado=A&codigo=ADG_A_3001_01
      → {"parent_b": {"codigo": "ADG_B_3001", "denominacion": "...", "grado": "B"},
         "contingut": {"ra": {"codigo": "ADG_RA_3001_01", "text": "..."} | null, "ecp": [...]}}

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
        # Pla 057: C LOMLOE → mòduls B (bc_lomloe.json). Buit per a C LOE.
        _idx_c = _get_itinerary_index()
        _b_by_code = _idx_c.get('b_by_code', {}) if _idx_c else {}
        parent_b_lomloe = [_serialize(_b_by_code[b]) for b in _get_bc_lomloe().get(codigo, [])
                           if b in _b_by_code]

        # Pla 058: C LOMLOE → cicles D via mòduls compartits (no passa per ciclos_fp.json).
        if re.match(r'^[A-Z]{3}_C_\d+_\w+$', codigo):
            cd = _get_c_lomloe_to_d()
            d_by_id = cd['d_by_id']
            ciclos_lomloe = []
            for e in cd['index'].get(codigo, []):
                d = d_by_id.get(str(e['id']))
                if not d:
                    continue
                ciclos_lomloe.append({
                    'id': int(e['id']),
                    'ref': d.get('ref'),
                    'denominacion': d.get('denominacion'),
                    'familia': d.get('familia'),
                    'ficha_url': d.get('ficha_url'),
                    'shared': e['shared'],
                    'total': e['total'],
                })
            return jsonify({'ciclos_d': ciclos_lomloe, 'parent_b_loe': [],
                            'parent_b_lomloe': parent_b_lomloe})

        if not os.path.exists(CICLOS_PATH):
            return jsonify({'ciclos_d': [], 'parent_b_loe': [],
                            'parent_b_lomloe': parent_b_lomloe,
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

        return jsonify({'ciclos_d': ciclos, 'parent_b_loe': parent_b_loe,
                        'parent_b_lomloe': parent_b_lomloe})

    idx = _get_itinerary_index()
    if not idx:
        return jsonify({'error': 'Dades no disponibles'}), 503

    if grado == 'A':
        # Ampliació 068: un A LOE pot tenir diversos B pares; 'parent_b' (el
        # primer) es manté per compatibilitat.
        parents, contingut = _contingut_a(codigo, idx)
        return jsonify({'parent_b': _serialize(parents[0]) if parents else None,
                        'parents_b': [_serialize(p) for p in parents],
                        'contingut': contingut})

    # grado == 'B'
    mock_rec = {'grado': 'B', 'codigo': codigo}
    children = itinerary.get_children_a(mock_rec, idx)
    response: dict = {'children_a': [_serialize(c) for c in children]}

    # B→C: certificats C que contenen aquest mòdul B.
    #   LOE    (MF####_N):   via UC####_N → bc_loe.json
    #   LOMLOE (FAM_B_NNNN): via bc_lomloe.json (Pla 057)
    # 'children_c' és el camp canònic; 'children_c_loe' es manté com a àlies
    # per a frontends cachejats.
    children_c: list = []
    _m_b_loe = re.match(r'^MF(\d{4})_(\d+)$', codigo)
    if _m_b_loe:
        uc_key = f"UC{_m_b_loe.group(1)}_{_m_b_loe.group(2)}"
        c_loe_by_code = idx.get('c_loe_by_code', {})
        for cc in _get_bc_loe_inverse().get(uc_key, []):
            c_rec = c_loe_by_code.get(cc)
            if c_rec:
                children_c.append(_serialize(c_rec))
    elif re.match(r'^[A-Z]{3}_B_\d{4}$', codigo):
        c_lomloe_by_code = idx.get('c_lomloe_by_code', {})
        for cc in _get_bc_lomloe_inverse().get(codigo, []):
            c_rec = c_lomloe_by_code.get(cc)
            if c_rec:
                children_c.append(_serialize(c_rec))
    response['children_c'] = children_c
    response['children_c_loe'] = children_c

    return jsonify(response)


# ---------------------------------------------------------------------------
# Pla 071 — Itinerari complet A→B→C→D(→E) com a nodes + arestes
# ---------------------------------------------------------------------------

_itinerary_graph_cache: dict = {"key": None, "data": None}


def _load_json_dict(path: str):
    """Contingut d'un JSON objecte, o None si no existeix / és corrupte."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_load_json_dict: error llegint %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


def _get_itinerary_graph():
    """
    Graf complet (itinerary_graph.build_graph) + avisos de fonts que falten.
    Cache invalidada per mtimes de tots els fitxers que hi intervenen.
    None si ofertes.json no es pot llegir.
    """
    def _mt(path):
        return os.path.getmtime(path) if os.path.exists(path) else None

    sources = {'a_loe_pares.json': A_LOE_PARES_PATH, 'bc_loe.json': BC_LOE_PATH,
               'bc_lomloe.json': BC_LOMLOE_PATH, 'd_modulos.json': D_MODULOS_PATH,
               'ciclos_fp.json': CICLOS_PATH}
    key = (_mt(DATA_PATH), _mt(CE_ACCES_PATH), *(_mt(p) for p in sources.values()))
    if _itinerary_graph_cache["key"] == key and _itinerary_graph_cache["data"] is not None:
        return _itinerary_graph_cache["data"]
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("_get_itinerary_graph: error llegint ofertes.json: %s", exc)
        return None

    graph = itinerary_graph.build_graph(
        records,
        a_loe_pares=_get_a_loe_pares(),
        bc_loe=_load_json_dict(BC_LOE_PATH),
        bc_lomloe=_get_bc_lomloe(),
        c_lomloe_to_d=_get_c_lomloe_to_d()['index'],
        ciclos_fp=_load_json_dict(CICLOS_PATH),
        ce_acces=_load_json_dict(CE_ACCES_PATH),  # opcional (Pla 074): sense avís si falta
    )
    warnings = [f'{name} no disponible — cal fer un refresh'
                for name, path in sources.items() if not os.path.exists(path)]
    data = {'graph': graph, 'warnings': warnings}
    _itinerary_graph_cache.update(key=key, data=data)
    return data


@app.route('/api/itinerari/complet')
def api_itinerari_complet():
    """Pla 071: cadena completa d'un grau (ascendents + descendents).

    GET /api/itinerari/complet?grado=A|B|C|D|E&ref=…  [&depth=1]   (Pla 076)
      → {"focus": "C:ADG_C_001_3B", "nodes": [...], "edges": [...], "warnings": [...]}
    Paràmetres antics, millor esforç: ?grado=A|B|C&codigo=… i ?grado=D|E&id=… (id vigent).
    """
    grado = (request.args.get('grado') or '').upper()
    ref = request.args.get('ref')
    codigo = request.args.get('codigo')
    id_ = request.args.get('id')
    depth = request.args.get('depth')

    if grado not in ('A', 'B', 'C', 'D', 'E'):
        return jsonify({'error': 'grado ha de ser A, B, C, D o E'}), 400
    if sum(p is not None for p in (ref, codigo, id_)) != 1:
        return jsonify({'error': 'cal un sol paràmetre: ref'}), 400
    if ref is not None:
        if not oferta_ref.REF_RE.match(ref):
            return jsonify({'error': 'ref invàlid'}), 400
    elif codigo is not None:
        if grado not in ('A', 'B', 'C') or not _CODIGO_RE.match(codigo):
            return jsonify({'error': 'Codi invàlid'}), 400
        rec = next((r for r in ((_get_catalog() or {}).get('by_codigo', {}).get(codigo) or [])
                    if r.get('grado') == grado), None)
        ref = rec['ref'] if rec else codigo
    else:
        if grado not in ('D', 'E') or not (id_.isascii() and id_.isdigit()):
            return jsonify({'error': 'id invàlid'}), 400
        rec = _resolve_oferta(oferta_id=int(id_))
        if not rec:
            return jsonify({'error': 'Grau no trobat'}), 404
        ref = rec['ref']
    focus = f'{grado}:{ref}'
    if depth not in (None, '1'):
        return jsonify({'error': 'depth només admet 1'}), 400

    data = _get_itinerary_graph()
    if data is None:
        return jsonify({'error': 'Dades no disponibles'}), 503
    if focus not in data['graph']['records']:
        return jsonify({'error': 'Grau no trobat'}), 404

    body = itinerary_graph.subgraph(data['graph'], focus, depth=1 if depth else None)
    body['warnings'] = data['warnings'] + body['warnings']
    return jsonify(body)


# ---------------------------------------------------------------------------
# Pla 077 — Pàgines públiques per grau i família, sitemap i robots (SEO)
# nginx reescriu /grau/…, /familia/…, /families, /sitemap.xml i /robots.txt cap aquí.
# ---------------------------------------------------------------------------

_seo_cache: dict = {"key": None, "data": None}
_SEO_CACHE_CONTROL = 'public, max-age=3600'


def _get_seo_data() -> dict | None:
    """
    Índexs derivats per a les pàgines públiques: ocupacions per grau, bc_loe,
    ce_acces, famílies i sitemap. Es refan quan canvia el mtime d'ofertes.json
    (o d'un dels fitxers que hi intervenen). None si el catàleg no es pot llegir.
    """
    catalog = _get_catalog()
    if not catalog:
        return None

    def _mt(path):
        return os.path.getmtime(path) if os.path.exists(path) else None

    key = (_catalog_cache["key"], _mt(OCUPACIONES_PATH), _mt(BC_LOE_PATH), _mt(CE_ACCES_PATH),
           SITE_URL)
    if _seo_cache["key"] == key and _seo_cache["data"] is not None:
        return _seo_cache["data"]

    # Ocupacions: els C per codi; els D/E per ficha_url (estable) o, si no, per id vigent.
    ocupacions: dict = {}
    for e in _get_ocupaciones():
        if e.get('grado') == 'C':
            k = ('C', e.get('codigo'))
        else:
            k = ('url', e['ficha_url']) if e.get('ficha_url') else ('id', e.get('id'))
        noms = ocupacions.setdefault(k, [])
        if e.get('ocupacio') and e['ocupacio'] not in noms:
            noms.append(e['ocupacio'])

    families: dict = {}  # prefix → (família, [registres])
    for r in catalog["records"]:
        prefix = oferta_ref.family_prefix(r.get('familia'))
        if prefix:
            families.setdefault(prefix, (r['familia'], []))[1].append(r)
    families_list = sorted(((p, f, len(recs)) for p, (f, recs) in families.items()),
                           key=lambda t: t[1])

    lastmod = date.fromtimestamp(os.path.getmtime(DATA_PATH)).isoformat()
    entries = [(SITE_URL + path, lastmod) for path in grau_page.STATIC_PAGES]
    entries += [(f'{SITE_URL}/familia/{p}', lastmod) for p, _, _ in families_list]
    entries += [(SITE_URL + grau_page.grau_path(r['ref']), lastmod) for r in catalog["records"]]

    data = {
        'ocupacions': ocupacions,
        'bc_loe': _load_json_dict(BC_LOE_PATH) or {},
        'ce_acces': _load_json_dict(CE_ACCES_PATH) or {},
        'families': families,
        'families_list': families_list,
        'lastmod': lastmod,
        'sitemap': grau_page.render_sitemap(entries),
    }
    _seo_cache.update(key=key, data=data)
    return data


def _grau_centres(ref: str) -> dict:
    """Recompte de centres (el mateix que /api/centres/count, heretats inclosos) i per comunitat."""
    try:
        ids = _get_effective_oferta_centres().get(ref, [])
    except (OSError, ValueError) as exc:
        logger.warning("_grau_centres: centres no disponibles: %s", exc)
        return {'total': 0, 'per_ccaa': []}
    per_ccaa: dict = {}
    for i in ids:
        ccaa = (_centres_index.get(i) or {}).get('ccaa')
        if ccaa:
            per_ccaa[ccaa] = per_ccaa.get(ccaa, 0) + 1
    return {'total': len(ids),
            'per_ccaa': sorted(per_ccaa.items(), key=lambda kv: (-kv[1], kv[0]))}


def _grau_context(rec: dict, seo: dict) -> dict:
    """Dades de la pàgina d'un grau (grau_page.render_grau) a partir dels índexs en memòria."""
    grado, codigo, ref = rec.get('grado'), rec.get('codigo'), rec['ref']

    previs: list = []
    seguents: list = []
    graph_data = _get_itinerary_graph()
    focus = f'{grado}:{ref}'
    if graph_data and focus in graph_data['graph']['records']:
        sub = itinerary_graph.subgraph(graph_data['graph'], focus, depth=1)
        nodes = {n['key']: n for n in sub['nodes']}
        for e in sub['edges']:
            if e['to'] == focus and nodes[e['from']] not in previs:
                previs.append(nodes[e['from']])
            elif e['from'] == focus and nodes[e['to']] not in seguents:
                seguents.append(nodes[e['to']])
    order = lambda n: (n.get('grado') or '', n.get('denominacion') or '')  # noqa: E731
    previs.sort(key=order)
    seguents.sort(key=order)

    contingut: dict = {}
    if grado == 'A' and codigo:
        _, c = _contingut_a(codigo, _get_itinerary_index())
        contingut = {'ra': [c['ra']] if c['ra'] else [], 'ecp': c['ecp']}
    elif grado == 'B' and codigo:
        c = _get_b_contingut().get(codigo) or {}
        contingut = {'ecp': c.get('ecp') or [], 'ra': c.get('ra') or []}
    elif grado == 'C' and rec.get('plan_antiguo') and codigo:
        b_by_uc = _get_itinerary_index().get('b_by_uc', {})
        contingut = {'uc': [{'codigo': uc, 'nombre': (b_by_uc.get(uc) or {}).get('denominacion')}
                            for uc in seo['bc_loe'].get(codigo, [])]}
    elif grado == 'D':
        modulos = (_get_d_modulos().get(str(rec.get('id'))) or {}).get('modulos') or []
        contingut = {'modulos': [m['name'] for m in modulos if m.get('name')]}
    elif grado == 'E':
        # Els D que hi donen accés ja són els veïns "previs" del graf (ce_acces.json):
        # es mostren com a requisits d'accés i no es repeteixen a l'itinerari.
        entry = seo['ce_acces'].get(str(rec.get('id'))) or {}
        contingut = {'acceso': previs, 'acceso_otros': entry.get('unmatched') or []}
        previs = []

    if grado == 'C':
        ocup_key = ('C', codigo)
    else:
        ocup_key = ('url', rec['ficha_url']) if rec.get('ficha_url') else ('id', rec.get('id'))

    return {
        'contingut': contingut,
        'ocupaciones': seo['ocupacions'].get(ocup_key, []),
        'centres': _grau_centres(ref),
        'previs': previs,
        'seguents': seguents,
        'familia_prefix': oferta_ref.family_prefix(rec.get('familia')),
        'lastmod': seo['lastmod'],
    }


def _seo_response(body: str, status: int = 200, mimetype: str = 'text/html'):
    cache = _SEO_CACHE_CONTROL if status == 200 else 'public, max-age=300'
    return body, status, {'Content-Type': f'{mimetype}; charset=utf-8', 'Cache-Control': cache}


def _seo_error(status: int):
    return _seo_response(grau_page.render_error(SITE_URL, not_found=status == 404), status)


@app.route('/api/grau/<path:ref>')
def grau_publica(ref):
    """Pàgina pública d'un grau (/grau/<ref>). 404 en HTML si el ref no existeix."""
    seo = _get_seo_data()
    if seo is None:
        return _seo_error(503)
    rec = _resolve_oferta(ref=ref) if oferta_ref.REF_RE.match(ref) else None
    if not rec:
        return _seo_error(404)
    return _seo_response(grau_page.render_grau(rec, _grau_context(rec, seo), SITE_URL))


@app.route('/api/familia/<path:prefix>')
def familia_publica(prefix):
    """Graus d'una família professional (/familia/<prefix>), agrupats per grau."""
    seo = _get_seo_data()
    if seo is None:
        return _seo_error(503)
    if prefix not in seo['families']:
        return _seo_error(404)
    familia, records = seo['families'][prefix]
    return _seo_response(grau_page.render_familia(familia, prefix, records, SITE_URL))


@app.route('/api/families')
def families_publica():
    """Llista de famílies professionals (/families)."""
    seo = _get_seo_data()
    if seo is None:
        return _seo_error(503)
    return _seo_response(grau_page.render_families(seo['families_list'], SITE_URL))


@app.route('/api/sitemap.xml')
def sitemap_xml():
    """Sitemap dinàmic: pàgines estàtiques, famílies i un URL per grau (/sitemap.xml)."""
    seo = _get_seo_data()
    if seo is None:
        return _seo_error(503)
    return _seo_response(seo['sitemap'], mimetype='application/xml')


@app.route('/api/robots.txt')
def robots_txt():
    """robots.txt amb la línia Sitemap: segons SITE_URL (/robots.txt)."""
    return _seo_response(grau_page.render_robots(SITE_URL), mimetype='text/plain')


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


# Límit per IP dels endpoints anònims que envien email (register, forgot-password).
# Generós perquè una classe sencera pot registrar-se des de la IP d'una escola.
_AUTH_EMAIL_IP_LIMIT = 20
_AUTH_EMAIL_IP_WINDOW = 3600
_AUTH_RESET_COOLDOWN_MINUTES = 15   # un sol email de reset per compte i finestra

# En memòria, com _feedback_hits: gunicorn corre amb 1 worker.
_auth_rate_hits: dict = {}
_auth_rate_lock = threading.Lock()


def _auth_rate_ok(bucket: str, ip: str) -> bool:
    """Registra una petició de `bucket` per a `ip` i diu si és dins del límit."""
    key = (bucket, ip)
    now = time.time()
    with _auth_rate_lock:
        recent = [t for t in _auth_rate_hits.get(key, []) if now - t < _AUTH_EMAIL_IP_WINDOW]
        if len(recent) >= _AUTH_EMAIL_IP_LIMIT:
            _auth_rate_hits[key] = recent
            return False
        recent.append(now)
        _auth_rate_hits[key] = recent
        return True


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
    if not _auth_rate_ok("register", _client_ip(request)):
        return jsonify({"error": "Massa intents. Torna-ho a provar més tard."}), 429
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
    # Darrere nginx remote_addr és sempre 127.0.0.1: sense això el límit és global.
    ip = _client_ip(request)
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


@app.route("/api/auth/google", methods=["GET"])
def auth_google_start():
    """Pas 1 OAuth: redirigeix a Google amb state anti-CSRF."""
    import secrets as _secrets
    import urllib.parse
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        return jsonify({"error": "Google OAuth no configurat"}), 503
    state = _secrets.token_hex(16)
    redirect_uri = BASE_URL + "/api/auth/google/callback"
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "prompt": "select_account",
    })
    resp = redirect("https://accounts.google.com/o/oauth2/v2/auth?" + params, code=302)
    secure = not app.debug
    resp.set_cookie("oauth_state", state, httponly=True, secure=secure,
                    samesite="Lax", max_age=300)
    return resp


@app.route("/api/auth/google/callback", methods=["GET"])
def auth_google_callback():
    """Pas 2 OAuth: intercanvia el codi, crea/troba l'usuari i inicia sessió."""
    import secrets as _secrets
    import db as _db
    from datetime import datetime, timezone, timedelta
    from flask import redirect as _redirect

    # Verificació anti-CSRF
    state_cookie = request.cookies.get("oauth_state", "")
    state_param  = request.args.get("state", "")
    if not state_cookie or state_cookie != state_param:
        return _redirect("/?google_error=state")

    code = request.args.get("code", "")
    if not code:
        return _redirect("/?google_error=no_code")

    client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri  = BASE_URL + "/api/auth/google/callback"

    # Intercanvi codi → tokens
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if not token_resp.ok:
        logger.error("Google token error: %s", token_resp.text)
        return _redirect("/?google_error=token")

    access_token = token_resp.json().get("access_token", "")
    if not access_token:
        return _redirect("/?google_error=no_token")

    # Obtenir info de l'usuari
    userinfo_resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": "Bearer " + access_token},
        timeout=10,
    )
    if not userinfo_resp.ok:
        return _redirect("/?google_error=userinfo")

    info       = userinfo_resp.json()
    google_sub = info.get("sub", "")
    email      = (info.get("email") or "").strip().lower()
    if not email or not google_sub:
        return _redirect("/?google_error=no_email")
    # L'email és la clau de vinculació amb comptes existents: només si Google l'ha verificat.
    if info.get("email_verified") is not True:
        return _redirect("/?google_error=unverified_email")

    conn = _db.get_db()
    try:
        # Cerca per google_id primer, després per email (merge de compte existent)
        user = _db.query_one(conn, "SELECT id, is_admin FROM users WHERE google_id = ?", (google_sub,))
        if not user:
            user = _db.query_one(
                conn,
                "SELECT id, is_admin, verified FROM users WHERE email = ? AND deleted_at IS NULL AND is_active = 1",
                (email,),
            )
            if user:
                if not user["verified"]:
                    # Ningú no havia demostrat ser el titular de l'email: la contrasenya,
                    # sessions i tokens previs poden ser d'un tercer (pre-hijack).
                    conn.execute("UPDATE users SET password_hash = 'google' WHERE id = ?", (user["id"],))
                    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
                    conn.execute("DELETE FROM tokens WHERE user_id = ?", (user["id"],))
                # Vincula google_id a compte existent
                conn.execute("UPDATE users SET google_id = ?, verified = 1 WHERE id = ?",
                             (google_sub, user["id"]))
            else:
                # Nou usuari
                conn.execute(
                    "INSERT INTO users (email, password_hash, verified, google_id) VALUES (?, 'google', 1, ?)",
                    (email, google_sub),
                )
                conn.commit()
                user = _db.query_one(conn, "SELECT id, is_admin FROM users WHERE google_id = ?", (google_sub,))

        conn.commit()
        uid      = user["id"]
        is_admin = bool(user["is_admin"])

        # Crea sessió (idèntic al login normal)
        session_token = _secrets.token_hex(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        ip = _client_ip(request)
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at, ip, user_agent) VALUES (?, ?, ?, ?, ?)",
            (uid, session_token, expires, ip, request.headers.get("User-Agent", "")),
        )
        conn.commit()
    finally:
        conn.close()

    secure = not app.debug
    resp = _redirect("/?google=1")
    resp.set_cookie("session", session_token,
                    httponly=True, secure=secure, samesite="Lax",
                    max_age=30 * 24 * 3600)
    resp.set_cookie("oauth_state", "", max_age=0)
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
    if not _auth_rate_ok("forgot", _client_ip(request)):
        return jsonify({"error": "Massa intents. Torna-ho a provar més tard."}), 429
    conn = _db.get_db()
    try:
        user = _db.query_one(
            conn, "SELECT id FROM users WHERE email = ? AND deleted_at IS NULL AND is_active = 1", (email,)
        )
        recent_reset = user and _db.query_one(
            conn,
            "SELECT 1 FROM tokens WHERE user_id = ? AND type = 'password_reset' "
            "AND created_at > datetime('now', ?)",
            (user["id"], f"-{_AUTH_RESET_COOLDOWN_MINUTES} minutes"),
        )
        # Resposta idèntica encara que no s'enviï res: no revela si el compte existeix.
        if user and not recent_reset:
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
        # Recuperar el compte ha d'expulsar qualsevol sessió o reset previ.
        conn.execute(
            "DELETE FROM tokens WHERE user_id = ? AND type = 'password_reset'", (row["user_id"],)
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["user_id"],))
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
    """Retorna els favorits de l'usuari autenticat. `ref` és la clau estable (Pla 076);
    `oferta_id` és l'id vigent del grau (canvia a cada refresc del catàleg)."""
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
            "SELECT id, oferta_id, oferta_codigo, oferta_ref, added_at FROM list_items "
            "WHERE list_id = ? ORDER BY added_at DESC",
            (list_id_row["id"],),
        )
        result = []
        for item in items:
            centres = _db.query_all(
                conn,
                "SELECT centre_id FROM list_item_centres WHERE list_item_id = ? ORDER BY added_at",
                (item["id"],),
            )
            rec = _resolve_oferta(ref=item["oferta_ref"]) if item["oferta_ref"] else None
            result.append({
                "ref": item["oferta_ref"],
                "oferta_id": rec["id"] if rec else item["oferta_id"],
                "oferta_codigo": item["oferta_codigo"],
                "added_at": item["added_at"],
                "centres": [c["centre_id"] for c in centres],
            })
        return jsonify(result), 200
    finally:
        conn.close()


@app.route("/api/favorites", methods=["POST"])
def favorites_add():
    """
    Afegeix una oferta als favorits. Body: {ref} (Pla 076), validat contra el catàleg.
    Període de transició: també {oferta_id, oferta_codigo}, traduït al ref vigent.
    """
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    if "ref" in data:
        rec = _resolve_oferta(ref=data.get("ref"))
    elif isinstance(data.get("oferta_id"), int):
        rec = _resolve_oferta(oferta_id=data["oferta_id"], codigo=data.get("oferta_codigo") or None)
    else:
        return jsonify({"error": "ref és obligatori"}), 400
    if not rec:
        return jsonify({"error": "Grau desconegut"}), 400
    conn = _db.get_db()
    try:
        list_id = _get_or_create_favorites_list(conn, user_id)
        existing = _db.query_one(
            conn, "SELECT id FROM list_items WHERE list_id = ? AND oferta_ref = ?", (list_id, rec["ref"])
        )
        if existing:
            return jsonify({"status": "already_exists"}), 200
        conn.execute(
            "INSERT INTO list_items (list_id, oferta_id, oferta_codigo, oferta_ref) VALUES (?, ?, ?, ?)",
            (list_id, rec["id"], rec.get("codigo"), rec["ref"]),
        )
        conn.commit()
        return jsonify({"status": "added", "ref": rec["ref"]}), 201
    finally:
        conn.close()


@app.route("/api/favorites/<key>", methods=["DELETE"])
def favorites_remove(key):
    """Elimina una oferta dels favorits. <key> = ref (o id antic, millor esforç)."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    ref = _ref_from_url_key(key)
    conn = _db.get_db()
    try:
        list_id_row = _db.query_one(conn, "SELECT id FROM lists WHERE user_id = ? LIMIT 1", (user_id,))
        if not list_id_row or not ref:
            return jsonify({"status": "not_found"}), 404
        conn.execute(
            "DELETE FROM list_items WHERE list_id = ? AND oferta_ref = ?",
            (list_id_row["id"], ref),
        )
        conn.commit()
        return "", 204
    finally:
        conn.close()



def _get_favorite_list_item(conn, user_id, key):
    """Retorna la fila de list_items del favorit indicat (ref o id antic), o None."""
    import db as _db
    ref = _ref_from_url_key(key)
    if not ref:
        return None
    return _db.query_one(
        conn,
        "SELECT list_items.id FROM list_items "
        "JOIN lists ON lists.id = list_items.list_id "
        "WHERE lists.user_id = ? AND list_items.oferta_ref = ?",
        (user_id, ref),
    )


@app.route("/api/favorites/<key>/centres", methods=["POST"])
def favorites_add_centre(key):
    """Marca un centre dins d'un favorit. Body: {centre_id}."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    centre_id = data.get("centre_id")
    if not isinstance(centre_id, str) or not centre_id.strip():
        return jsonify({"error": "centre_id és obligatori i ha de ser una cadena no buida"}), 400
    conn = _db.get_db()
    try:
        item = _get_favorite_list_item(conn, user_id, key)
        if not item:
            return jsonify({"error": "Favorit no trobat"}), 404
        existing = _db.query_one(
            conn,
            "SELECT id FROM list_item_centres WHERE list_item_id = ? AND centre_id = ?",
            (item["id"], centre_id),
        )
        if existing:
            return jsonify({"status": "already_exists"}), 200
        conn.execute(
            "INSERT INTO list_item_centres (list_item_id, centre_id) VALUES (?, ?)",
            (item["id"], centre_id),
        )
        conn.commit()
        return jsonify({"status": "added"}), 201
    finally:
        conn.close()


@app.route("/api/favorites/<key>/centres/<centre_id>", methods=["DELETE"])
def favorites_remove_centre(key, centre_id):
    """Desmarca un centre d'un favorit."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        item = _get_favorite_list_item(conn, user_id, key)
        if not item:
            return jsonify({"status": "not_found"}), 404
        conn.execute(
            "DELETE FROM list_item_centres WHERE list_item_id = ? AND centre_id = ?",
            (item["id"], centre_id),
        )
        conn.commit()
        return "", 204
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Favorits FPO — /api/fpo/favorites  (Pla 061)
# ---------------------------------------------------------------------------


def _fpo_espec_by_codi(codi):
    """Especialitat FPO per codi (SOC o externa), o {} si no hi és."""
    if fpo_ext.is_ext_codi(codi):
        return next((e for e in _ext_index()["list"] if e["codi"] == codi), {})
    for e in _get_soc_especs():
        if e.get("codi") == codi:
            return e
    return {}


def _fpo_curs_by_id(curs_id):
    """Curs FPO per idCurs (SOC o extern), o None si ja no hi és."""
    if fpo_ext.is_ext_codi(curs_id):
        return next((c for c in _get_ext_cursos() if c.get("idCurs") == curs_id), None)
    for c in _get_soc_cursos():
        if c.get("idCurs") == curs_id:
            return c
    return None


def _fpo_fav_course_public(row):
    """Enriqueix una fila de fpo_favorite_courses amb dades del snapshot (SOC o extern)."""
    curs = _fpo_curs_by_id(row["curs_id"])
    ext = curs is not None and curs.get("font") in fpo_ext.FONTS
    estat = ""
    if curs is not None:
        estat = fpo_ext.estat(curs, _fpo_today()) if ext else curs.get("estat", "")
    out = {
        "curs_id": row["curs_id"],
        "centre_id": row["centre_id"],
        "created_at": row["created_at"],
        # Els estats del SOC mai són 'finalitzat': aquest valor només surt dels externs.
        "finalitzat": curs is None or estat == "finalitzat",
    }
    if curs is not None:
        out.update({
            "titol": fpo_ext.titol_net(curs.get("titol")) if ext else curs.get("titol", {"ca": "", "es": ""}),
            "centre": curs.get("centre", {}),
            "dataInici": curs.get("dataInici"),
            "dataFi": curs.get("dataFi"),
            "estat": estat,
            "modalitat": curs.get("modalitat", ""),
            "fitxaUrl": curs.get("fitxaUrl", "") if ext else _soc_fitxa_url(curs),
            "font": curs.get("font", "soc"),
            "tipus": curs.get("tipus", ""),
            "horariText": curs.get("horariText", ""),
        })
    return out


@app.route("/api/fpo/favorites", methods=["GET"])
def fpo_favorites_get():
    """Especialitats FPO desades per l'usuari, enriquides amb el snapshot."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        favs = _db.query_all(
            conn,
            "SELECT especialitat_codi, created_at FROM fpo_favorites "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        result = []
        for fav in favs:
            codi = fav["especialitat_codi"]
            espec = _fpo_espec_by_codi(codi)
            courses = _db.query_all(
                conn,
                "SELECT curs_id, centre_id, created_at FROM fpo_favorite_courses "
                "WHERE user_id = ? AND especialitat_codi = ? ORDER BY created_at",
                (user_id, codi),
            )
            result.append({
                "especialitat_codi": codi,
                "font": espec.get("font", "soc"),
                "created_at": fav["created_at"],
                "titol": espec.get("titol", {"ca": "", "es": ""}),
                "familia": espec.get("familia", {}),
                "area": espec.get("area", {}),
                "nivell": espec.get("nivell", 0),
                "hores": espec.get("hores", 0.0),
                "esCertProf": bool(espec.get("esCertProf")),
                "programaUrl": espec.get("programaUrl", ""),
                "cursos": [_fpo_fav_course_public(c) for c in courses],
            })
        return jsonify(result), 200
    finally:
        conn.close()


@app.route("/api/fpo/favorites", methods=["POST"])
def fpo_favorites_add():
    """Desa una especialitat FPO. Body: {especialitat_codi}. Idempotent."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    codi = (data.get("especialitat_codi") or "").strip()
    if not codi:
        return jsonify({"error": "especialitat_codi és obligatori"}), 400
    conn = _db.get_db()
    try:
        existing = _db.query_one(
            conn,
            "SELECT 1 FROM fpo_favorites WHERE user_id = ? AND especialitat_codi = ?",
            (user_id, codi),
        )
        if existing:
            return jsonify({"status": "already_exists"}), 200
        conn.execute(
            "INSERT INTO fpo_favorites (user_id, especialitat_codi) VALUES (?, ?)",
            (user_id, codi),
        )
        conn.commit()
        return jsonify({"status": "added"}), 201
    finally:
        conn.close()


@app.route("/api/fpo/favorites/<codi>", methods=["DELETE"])
def fpo_favorites_remove(codi):
    """Treu una especialitat FPO desada i tots els seus cursos marcats."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        conn.execute(
            "DELETE FROM fpo_favorite_courses WHERE user_id = ? AND especialitat_codi = ?",
            (user_id, codi),
        )
        conn.execute(
            "DELETE FROM fpo_favorites WHERE user_id = ? AND especialitat_codi = ?",
            (user_id, codi),
        )
        conn.commit()
        return "", 204
    finally:
        conn.close()


@app.route("/api/fpo/favorites/<codi>/courses", methods=["POST"])
def fpo_favorites_add_course(codi):
    """Marca un curs concret dins d'un favorit. Body: {curs_id, centre_id}."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    curs_id = (data.get("curs_id") or "").strip()
    centre_id = data.get("centre_id") or None
    if not curs_id:
        return jsonify({"error": "curs_id és obligatori"}), 400
    conn = _db.get_db()
    try:
        fav = _db.query_one(
            conn,
            "SELECT 1 FROM fpo_favorites WHERE user_id = ? AND especialitat_codi = ?",
            (user_id, codi),
        )
        if not fav:
            return jsonify({"error": "Especialitat no desada"}), 404
        existing = _db.query_one(
            conn,
            "SELECT 1 FROM fpo_favorite_courses "
            "WHERE user_id = ? AND especialitat_codi = ? AND curs_id = ?",
            (user_id, codi, curs_id),
        )
        if existing:
            return jsonify({"status": "already_exists"}), 200
        conn.execute(
            "INSERT INTO fpo_favorite_courses (user_id, especialitat_codi, curs_id, centre_id) "
            "VALUES (?, ?, ?, ?)",
            (user_id, codi, curs_id, centre_id),
        )
        conn.commit()
        return jsonify({"status": "added"}), 201
    finally:
        conn.close()


@app.route("/api/fpo/favorites/<codi>/courses/<curs_id>", methods=["DELETE"])
def fpo_favorites_remove_course(codi, curs_id):
    """Desmarca un curs d'un favorit (l'especialitat es manté)."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        conn.execute(
            "DELETE FROM fpo_favorite_courses "
            "WHERE user_id = ? AND especialitat_codi = ? AND curs_id = ?",
            (user_id, codi, curs_id),
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
        # substr i no LIKE: a LIKE el '_' és comodí i 'alert_1_%' també casava 'alert_10_...'.
        prefix = f"alert_{alert_id}_"
        conn.execute(
            "DELETE FROM tokens WHERE user_id = ? AND type = 'alert_unsubscribe' "
            "AND substr(token, 1, ?) = ?",
            (user_id, len(prefix), prefix),
        )
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
            conn, "SELECT id, active FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
        )
        if not row:
            return jsonify({"error": "Alerta no trobada"}), 404
        # El límit de creació també s'ha de complir en reactivar (si no, desactivar-crear-reactivar el salta).
        if active and not row["active"]:
            count = _db.query_one(
                conn, "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND active = 1", (user_id,)
            )[0]
            if count >= 10:
                return jsonify({"error": "Màxim 10 alertes actives per usuari"}), 429
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
            "SELECT id, oferta_key, oferta_denom, provincia_filter, active, created_at, "
            "last_sent_at, last_new_count "
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
    oferta_key és el ref del grau (Pla 076); un id antic (només dígits) es tradueix al ref vigent.
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
    if oferta_key.isascii() and oferta_key.isdigit():
        rec = _resolve_oferta(oferta_id=int(oferta_key))
        oferta_key = rec["ref"] if rec else oferta_key

    # Snapshot inicial: centres actuals per a aquesta oferta (heretats inclosos)
    try:
        initial_ids = list(_get_effective_oferta_centres().get(oferta_key, []))
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
        prefix = f"cw_{watch_id}_"  # substr i no LIKE (vegeu alerts_delete)
        conn.execute(
            "DELETE FROM tokens WHERE user_id = ? AND type = 'centres_watch_unsubscribe' "
            "AND substr(token, 1, ?) = ?",
            (user_id, len(prefix), prefix),
        )
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
            conn, "SELECT id, active FROM centres_watch WHERE id = ? AND user_id = ?", (watch_id, user_id)
        )
        if not row:
            return jsonify({"error": "Seguiment no trobat"}), 404
        # El límit de creació també s'ha de complir en reactivar (vegeu alerts_toggle).
        if active and not row["active"]:
            count = _db.query_one(
                conn, "SELECT COUNT(*) FROM centres_watch WHERE user_id = ? AND active = 1", (user_id,)
            )[0]
            if count >= CENTRES_WATCH_MAX_PER_USER:
                return jsonify({"error": "Màxim 10 seguiments actius per usuari"}), 429
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
# Comentaris d'usuaris (Pla 069)
# ---------------------------------------------------------------------------

_FEEDBACK_KINDS = {"error", "idea", "data", "other"}
_FEEDBACK_KIND_LABELS = {"error": "Error", "idea": "Idea", "data": "Dades incorrectes", "other": "Altre"}
_FEEDBACK_MAX_CHARS = 2000
_FEEDBACK_CONTEXT_KEYS = ("path", "query", "lang")
_FEEDBACK_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FEEDBACK_ANON_LIMIT = 5        # comentaris anònims...
_FEEDBACK_ANON_WINDOW = 3600    # ...per IP i hora

# Límit en memòria: gunicorn corre amb 1 worker (pla 004), així no cal desar IPs a la BD.
_feedback_hits: dict = {}
_feedback_lock = threading.Lock()


def _feedback_now() -> float:
    return time.time()


def _run_in_background(fn) -> None:
    threading.Thread(target=fn, daemon=True).start()


def _client_ip(req) -> str:
    """IP del client. Les capçaleres de nginx només es creuen si la petició ve de loopback."""
    peer = req.remote_addr or ""
    if peer in ("127.0.0.1", "::1"):
        real = req.headers.get("X-Real-IP", "").strip()
        if real:
            return real
        forwarded = req.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return peer


def _feedback_rate_ok(ip: str) -> bool:
    """Registra un intent anònim i diu si és dins del límit."""
    now = _feedback_now()
    with _feedback_lock:
        recent = [t for t in _feedback_hits.get(ip, []) if now - t < _FEEDBACK_ANON_WINDOW]
        if len(recent) >= _FEEDBACK_ANON_LIMIT:
            _feedback_hits[ip] = recent
            return False
        recent.append(now)
        _feedback_hits[ip] = recent
        return True


def _sanitize_feedback_context(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    return {k: raw[k][:500] for k in _FEEDBACK_CONTEXT_KEYS if isinstance(raw.get(k), str)}


def _notify_feedback(email: str, kind: str, message: str, context: dict) -> None:
    """Avís opcional al propietari. Mai bloqueja ni fa fallar el comentari."""
    notify_to = os.environ.get("FEEDBACK_NOTIFY_EMAIL", "").strip()
    if not notify_to:
        return
    page = (context.get("path", "") + context.get("query", "")) or "—"
    body = (f"{email} ha deixat un comentari ({_FEEDBACK_KIND_LABELS.get(kind, kind)}).\n"
            f"Pàgina: {page}\n\n{message}\n")

    def send():
        try:
            import email_service
            email_service.send_email(notify_to, "Nou comentari a GrausFP", body)
        except Exception as exc:
            logger.warning("No s'ha pogut enviar l'avís de comentari: %s", exc)

    _run_in_background(send)


@app.route("/api/feedback", methods=["POST"])
def feedback_create():
    """Desa un comentari. Anònims: email obligatori, honeypot i límit per IP."""
    import db as _db
    data = request.get_json(silent=True) or {}
    if data.get("website"):  # honeypot: un humà no veu aquest camp
        return jsonify({"ok": True}), 201

    kind = data.get("kind")
    if kind not in _FEEDBACK_KINDS:
        return jsonify({"error": "Tipus de comentari no vàlid"}), 400
    message = data.get("message").strip() if isinstance(data.get("message"), str) else ""
    if not message:
        return jsonify({"error": "Escriu un comentari"}), 400
    if len(message) > _FEEDBACK_MAX_CHARS:
        return jsonify({"error": f"El comentari és massa llarg (màxim {_FEEDBACK_MAX_CHARS} caràcters)"}), 400
    context = _sanitize_feedback_context(data.get("context"))

    user_id = _get_session_user(request)
    conn = _db.get_db()
    try:
        if user_id:
            email = _db.query_one(conn, "SELECT email FROM users WHERE id = ?", (user_id,))["email"]
        else:
            email = (data.get("email") or "").strip().lower() if isinstance(data.get("email"), str) else ""
            if not email or len(email) > 254 or not _FEEDBACK_EMAIL_RE.match(email):
                return jsonify({"error": "Cal un email vàlid"}), 400
            if not _feedback_rate_ok(_client_ip(request)):
                return jsonify({"error": "Massa comentaris. Torna-ho a provar d'aquí a una estona."}), 429
        cur = conn.execute(
            "INSERT INTO feedback (user_id, email, kind, message, context) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, kind, message, json.dumps(context, ensure_ascii=False)),
        )
        conn.commit()
        feedback_id = cur.lastrowid
    finally:
        conn.close()

    _notify_feedback(email, kind, message, context)
    return jsonify({"id": feedback_id}), 201


_FEEDBACK_STATUSES = {"new", "in_progress", "done", "discarded"}
_FEEDBACK_NOTE_MAX_CHARS = 1000
_FEEDBACK_ADMIN_COLUMNS = "id, user_id, email, kind, message, context, status, admin_note, created_at, updated_at"


def _feedback_row(row) -> dict:
    item = dict(row)
    try:
        item["context"] = json.loads(item["context"] or "{}")
    except ValueError:
        item["context"] = {}
    return item


@app.route("/api/admin/feedback", methods=["GET"])
def admin_feedback_list():
    """Comentaris dels usuaris, més nous primer (màx. 500)."""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    conn = _db.get_db()
    try:
        rows = _db.query_all(
            conn,
            f"SELECT {_FEEDBACK_ADMIN_COLUMNS} FROM feedback ORDER BY created_at DESC, id DESC LIMIT 500",
        )
        return jsonify([_feedback_row(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/api/admin/feedback/<int:feedback_id>", methods=["PATCH"])
def admin_feedback_update(feedback_id):
    """Canvia l'estat i/o la nota interna d'un comentari."""
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    body = request.get_json(silent=True) or {}
    updates = {}
    if "status" in body:
        if body["status"] not in _FEEDBACK_STATUSES:
            return jsonify({"error": "Estat no vàlid"}), 400
        updates["status"] = body["status"]
    if "admin_note" in body:
        note = body["admin_note"]
        if note is not None and not isinstance(note, str):
            return jsonify({"error": "Nota no vàlida"}), 400
        note = (note or "").strip()
        if len(note) > _FEEDBACK_NOTE_MAX_CHARS:
            return jsonify({"error": f"La nota és massa llarga (màxim {_FEEDBACK_NOTE_MAX_CHARS} caràcters)"}), 400
        updates["admin_note"] = note or None
    conn = _db.get_db()
    try:
        sets = "".join(f"{col} = ?, " for col in updates)  # columnes fixes, no entrada d'usuari
        conn.execute(
            f"UPDATE feedback SET {sets}updated_at = datetime('now') WHERE id = ?",
            (*updates.values(), feedback_id),
        )
        conn.commit()
        row = _db.query_one(conn, f"SELECT {_FEEDBACK_ADMIN_COLUMNS} FROM feedback WHERE id = ?", (feedback_id,))
        if not row:
            return jsonify({"error": "Comentari no trobat"}), 404
        return jsonify(_feedback_row(row)), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Debug NOMÉS en desenvolupament explícit: FLASK_DEBUG=1 python app.py
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
