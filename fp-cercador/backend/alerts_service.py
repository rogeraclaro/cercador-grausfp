"""
alerts_service.py — Motor de matching i dispatching d'alertes personalitzades (F3).

Interfície pública:
  match_alert(filter_dict, changes)         → list[dict]  — items matchejats
  build_alert_description(filter_dict)      → str         — text llegible del filtre
  dispatch_alerts(result, base_url)         → int         — nombre d'emails enviats
"""
import json
import logging
import unicodedata
from datetime import datetime, timezone, timedelta
import secrets

import db as _db
import email_service

logger = logging.getLogger(__name__)

ALERTS_MAX_PER_USER = 10
UNSUBSCRIBE_TOKEN_DAYS = 365


def _normalize(text: str) -> str:
    """NFD + elimina diacrítics + lowercase. Idèntic a index.html del frontend."""
    return (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def match_alert(filter_dict: dict, changes: dict) -> list:
    """
    Retorna la llista de dicts {denominacio, familia, nivel, grado} que encaixen
    amb el filtre. Utilitza `new_by_grado_meta` dels changes (Step 2 de history.py).

    Args:
        filter_dict: El filter_json deserialitzat.
        changes: El retorn de history.compute_changes() (ha de tenir new_by_grado_meta).

    Returns:
        Llista de dicts matchejats. Buida si cap match o si changes és None.
    """
    if not changes:
        return []
    return _filter_items(filter_dict, changes.get("new_by_grado_meta") or {})


def match_removed(filter_dict: dict, changes: dict) -> list:
    """Baixes que encaixen amb el filtre, amb els mateixos criteris que les altes."""
    removed_meta = (changes or {}).get("removed_by_grado_meta")
    if removed_meta is None:
        # Entrada d'historial anterior a removed_by_grado_meta: només se'n sap el grau i el nom.
        removed_meta = {
            g: [{"denominacio": d} for d in denoms]
            for g, denoms in ((changes or {}).get("removed_by_grado") or {}).items()
        }
    return _filter_items(filter_dict, removed_meta)


def _filter_items(filter_dict: dict, new_by_grado_meta: dict) -> list:
    """Aplica grado/familia/nivel/texto a un dict {grado: [{denominacio, familia, nivel}]}."""
    if not new_by_grado_meta:
        return []

    grado_filter = filter_dict.get("grado")
    familia_filter = filter_dict.get("familia")
    nivel_filter = filter_dict.get("nivel")
    texto_filter = filter_dict.get("texto")

    # 1. Candidats inicials per grado
    if grado_filter:
        grado_items = new_by_grado_meta.get(grado_filter, [])
        candidates = [dict(item, grado=grado_filter) for item in grado_items]
    else:
        candidates = []
        for g, items in new_by_grado_meta.items():
            for item in items:
                candidates.append(dict(item, grado=g))

    if not candidates:
        return []

    # 2. Filtre per família (case-insensitive exact)
    if familia_filter:
        fam_q = familia_filter.lower()
        candidates = [c for c in candidates if (c.get("familia") or "").lower() == fam_q]

    # 3. Filtre per nivel (cast a int si cal per comparació)
    if nivel_filter is not None:
        try:
            niv_q = int(nivel_filter)
        except (TypeError, ValueError):
            niv_q = nivel_filter
        candidates = [c for c in candidates if c.get("nivel") == niv_q]

    # 4. Filtre per texto (substring NFD+lower)
    if texto_filter:
        q = _normalize(texto_filter)
        candidates = [c for c in candidates if q in _normalize(c.get("denominacio") or "")]

    return candidates


def build_alert_description(filter_dict: dict) -> str:
    """Genera una descripció llegible del filtre per a l'email i la UI."""
    parts = []
    if filter_dict.get("grado"):
        parts.append(f"Grado {filter_dict['grado']}")
    if filter_dict.get("familia"):
        parts.append(filter_dict["familia"])
    if filter_dict.get("nivel") is not None:
        parts.append(f"Nivell {filter_dict['nivel']}")
    if filter_dict.get("texto"):
        parts.append(f"Texto: «{filter_dict['texto']}»")
    return " · ".join(parts) if parts else "Tots els nous ensenyaments"


def _build_email_body(matched: list, description: str, alert_id: int, unsubscribe_token: str, base_url: str) -> str:
    """Genera el cos de l'email en text pla."""
    n = len(matched)
    bullets = "\n".join(f"  • {item['denominacio']}" for item in matched)
    unsubscribe_url = f"{base_url}/api/alerts/{alert_id}/unsubscribe?token={unsubscribe_token}"
    return (
        f"Hola,\n\n"
        f"Han aparegut {n} nous ensenyaments de Formació Professional que encaixen\n"
        f"amb la teva alerta \"{description}\":\n\n"
        f"{bullets}\n\n"
        f"Consulta els detalls a:\n{base_url}\n\n"
        f"---\n"
        f"Reps aquest email perquè tens una alerta activa a GrausFP.\n"
        f"Per deixar de rebre'l, clica aquí (sense necessitat d'entrar):\n"
        f"{unsubscribe_url}\n\n"
        f"GrausFP · {base_url}"
    )


def _get_or_create_unsubscribe_token(conn, alert_id: int, user_id: int, *, kind: str = "alert",
                                     token_type: str = "alert_unsubscribe") -> str:
    """Retorna el token de baixa de l'alerta, o en crea un de nou si no existeix.
    `kind` i `token_type` permeten reutilitzar-lo per a les alertes d'FPO (Pla 086)."""
    prefix = f"{kind}_{alert_id}_"  # substr i no LIKE: el '_' de LIKE és comodí
    row = _db.query_one(
        conn,
        "SELECT token FROM tokens WHERE user_id = ? AND type = ? "
        "AND substr(token, 1, ?) = ? AND expires_at > datetime('now')",
        (user_id, token_type, len(prefix), prefix),
    )
    if row:
        return row["token"][len(prefix):]  # extreu el token real
    # Caducat (o inexistent): l'endpoint de baixa el rebutjaria; se'n fa un de nou.
    conn.execute(
        "DELETE FROM tokens WHERE user_id = ? AND type = ? "
        "AND substr(token, 1, ?) = ?",
        (user_id, token_type, len(prefix), prefix),
    )

    raw_token = secrets.token_hex(32)
    stored_token = f"{prefix}{raw_token}"
    expires = (datetime.now(timezone.utc) + timedelta(days=UNSUBSCRIBE_TOKEN_DAYS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, stored_token, token_type, expires),
    )
    conn.commit()
    return raw_token


def dispatch_alerts(result: dict, base_url: str = "https://grausfp.es") -> int:
    """
    Llegeix el darrer entry de l'historial (ja calculat per history.append) i envia
    emails per a les alertes actives que tinguin matches.

    Idempotència: skip si `last_sent_at` és d'avui (format YYYY-MM-DD).
    Retorna el nombre d'emails enviats.
    """
    import history as _history

    # Obtenir changes del darrer entry de l'historial (ja calculat per history.append)
    history_data = _history._load_json(_history.HISTORY_PATH) or []
    if not history_data:
        return 0
    changes = history_data[0].get("changes")
    if not changes or not changes.get("has_changes"):
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _db.get_db()
    sent = 0
    try:
        alerts = _db.query_all(
            conn,
            "SELECT a.id, a.user_id, a.filter_json, a.last_sent_at, u.email "
            "FROM alerts a JOIN users u ON u.id = a.user_id "
            "WHERE a.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
        )
        for alert in alerts:
            # Idempotència: no enviar si ja s'ha enviat avui
            if alert["last_sent_at"] and alert["last_sent_at"][:10] == today:
                continue

            try:
                filter_dict = json.loads(alert["filter_json"])
            except (json.JSONDecodeError, TypeError):
                logger.warning("alerts_service: filter_json invàlid per alert id=%s", alert["id"])
                continue

            try:
                matched = match_alert(filter_dict, changes)
            except Exception as exc:
                logger.warning("alerts_service: filtre no avaluable per alert id=%s: %s", alert["id"], exc)
                continue

            # Afegir baixes si l'usuari les vol
            if filter_dict.get("alertar_baixes"):
                try:
                    removed = match_removed(filter_dict, changes)
                except Exception as exc:
                    logger.warning("alerts_service: baixes no avaluables per alert id=%s: %s", alert["id"], exc)
                    removed = []
                for item in removed:
                    matched.append(dict(item, denominacio=f"[BAIXA] {item['denominacio']}"))

            if not matched:
                continue

            description = build_alert_description(filter_dict)
            unsubscribe_token = _get_or_create_unsubscribe_token(conn, alert["id"], alert["user_id"])
            body = _build_email_body(matched, description, alert["id"], unsubscribe_token, base_url)
            subject = f"Novetats FP — {len(matched)} nous ensenyaments que t'interessen ({today})"

            try:
                email_service.send_email(alert["email"], subject, body)
                conn.execute(
                    "UPDATE alerts SET last_sent_at = ? WHERE id = ?",
                    (today, alert["id"]),
                )
                conn.commit()
                sent += 1
                logger.info("alerts_service: alerta %s → email enviat a %s (%d matches)",
                            alert["id"], alert["email"], len(matched))
            except Exception as exc:
                logger.error("alerts_service: error enviant email per alerta %s: %s", alert["id"], exc)

    finally:
        conn.close()

    return sent
