"""
centres_watch_service.py — Dispatch de notificacions de nous centres per oferta (F4).

Interfície pública:
  dispatch_centres_watch(base_url)  → int   nombre d'emails enviats
"""
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta

import db as _db
import email_service

logger = logging.getLogger(__name__)

WATCH_MAX_PER_USER = 10
UNSUBSCRIBE_TOKEN_DAYS = 365

_DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "data"))
_OFERTA_CENTRES_PATH = os.path.join(_DATA_DIR, "oferta_centres.json")
_CENTRES_PATH = os.path.join(_DATA_DIR, "centres.json")


def _load_centres_data() -> tuple[dict, dict]:
    """Llegeix oferta_centres.json i centres.json des de disc. Retorna (oferta_centres, centres_index)."""
    with open(_OFERTA_CENTRES_PATH, encoding="utf-8") as f:
        oferta_centres = json.load(f)
    with open(_CENTRES_PATH, encoding="utf-8") as f:
        centres_list = json.load(f)
    centres_index = {c["id"]: c for c in centres_list}
    return oferta_centres, centres_index


def _get_new_centres(oferta_key: str, snapshot_ids: set, oferta_centres: dict, centres_index: dict,
                     provincia_filter: str | None) -> list[dict]:
    """
    Retorna la llista de nous centres per a oferta_key respecte al snapshot.
    Aplica provincia_filter si és no-None.
    """
    current_ids = set(oferta_centres.get(oferta_key, []))
    new_ids = current_ids - snapshot_ids
    new_centres = [centres_index[i] for i in new_ids if i in centres_index]
    if provincia_filter:
        prov_q = provincia_filter.upper()
        new_centres = [c for c in new_centres if (c.get("provincia") or "").upper() == prov_q]
    return new_centres


def _build_email_body(new_centres: list, watch: dict, unsubscribe_token: str, base_url: str) -> str:
    n = len(new_centres)
    lines = []
    for c in new_centres:
        parts = [c["nombre"]]
        if c.get("localitat"):
            parts.append(c["localitat"])
        if c.get("provincia"):
            parts.append(c["provincia"])
        lines.append("  • " + ", ".join(parts))
    bullets = "\n".join(lines)
    prov_note = f" a {watch['provincia_filter']}" if watch.get("provincia_filter") else ""
    unsubscribe_url = (
        f"{base_url}/api/centres-watch/{watch['id']}/unsubscribe?token={unsubscribe_token}"
    )
    return (
        f"Hola,\n\n"
        f"Han aparegut {n} nous centres que impartiran «{watch['oferta_denom']}»{prov_note}:\n\n"
        f"{bullets}\n\n"
        f"Consulta'ls al cercador:\n{base_url}\n\n"
        f"---\n"
        f"Reps aquest email perquè segueixes centres d'aquest ensenyament al Cercador FP España.\n"
        f"Per deixar de rebre'l:\n{unsubscribe_url}\n\n"
        f"Cercador FP España · {base_url}"
    )


def _get_or_create_unsubscribe_token(conn, watch_id: int, user_id: int) -> str:
    row = _db.query_one(
        conn,
        "SELECT token FROM tokens WHERE user_id = ? AND type = 'centres_watch_unsubscribe' "
        "AND token LIKE ?",
        (user_id, f"cw_{watch_id}_%"),
    )
    if row:
        return row["token"].split("_", 2)[2]
    raw_token = secrets.token_hex(32)
    stored_token = f"cw_{watch_id}_{raw_token}"
    expires = (datetime.now(timezone.utc) + timedelta(days=UNSUBSCRIBE_TOKEN_DAYS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'centres_watch_unsubscribe', ?)",
        (user_id, stored_token, expires),
    )
    conn.commit()
    return raw_token


def dispatch_centres_watch(base_url: str = "https://grausfp.masellas.info") -> int:
    """
    Llegeix oferta_centres.json (ja actualitzat pel scraping), calcula nous centres
    per a cada watch actiu i envia emails.

    Idempotència: si last_sent_at és d'avui, l'watch s'omet.
    Actualitza snapshot_json a l'estat actual després d'enviar (o si no hi ha nous centres,
    l'actualitza igualment per reflectir l'estat actual).
    Retorna el nombre d'emails enviats.
    """
    try:
        oferta_centres, centres_index = _load_centres_data()
    except FileNotFoundError as exc:
        logger.warning("centres_watch_service: fitxers de centres no disponibles: %s", exc)
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _db.get_db()
    sent = 0
    try:
        watches = _db.query_all(
            conn,
            "SELECT cw.id, cw.user_id, cw.oferta_key, cw.oferta_denom, cw.provincia_filter, "
            "cw.last_sent_at, cw.snapshot_json, u.email "
            "FROM centres_watch cw JOIN users u ON u.id = cw.user_id "
            "WHERE cw.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
        )
        for watch in watches:
            if watch["last_sent_at"] and watch["last_sent_at"][:10] == today:
                continue

            snapshot_ids = set(json.loads(watch["snapshot_json"])) if watch["snapshot_json"] else set()
            watch_dict = dict(watch)

            new_centres = _get_new_centres(
                watch["oferta_key"], snapshot_ids, oferta_centres, centres_index,
                watch["provincia_filter"]
            )

            current_ids = list(oferta_centres.get(watch["oferta_key"], []))
            new_snapshot = json.dumps(current_ids)

            if new_centres:
                unsubscribe_token = _get_or_create_unsubscribe_token(conn, watch["id"], watch["user_id"])
                body = _build_email_body(new_centres, watch_dict, unsubscribe_token, base_url)
                subject = (
                    f"Nous centres FP — {len(new_centres)} nous centres per «{watch['oferta_denom']}» ({today})"
                )
                try:
                    email_service.send_email(watch["email"], subject, body)
                    conn.execute(
                        "UPDATE centres_watch SET last_sent_at = ?, snapshot_json = ? WHERE id = ?",
                        (today, new_snapshot, watch["id"]),
                    )
                    conn.commit()
                    sent += 1
                    logger.info(
                        "centres_watch: watch %s → email enviat a %s (%d nous centres)",
                        watch["id"], watch["email"], len(new_centres)
                    )
                except Exception as exc:
                    logger.error("centres_watch: error enviant email per watch %s: %s", watch["id"], exc)
            else:
                # Actualitza el snapshot sense enviar email
                conn.execute(
                    "UPDATE centres_watch SET snapshot_json = ? WHERE id = ?",
                    (new_snapshot, watch["id"]),
                )
                conn.commit()
    finally:
        conn.close()

    return sent
