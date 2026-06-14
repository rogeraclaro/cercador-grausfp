"""
notifier.py — Envia email de novetats via Brevo API quan hi ha nous ítems al feed.

Crida notify_if_new() després de cada refresh reeixit. Si les variables
BREVO_API_KEY / BREVO_LIST_ID / BREVO_SENDER_EMAIL no estan configurades,
no fa res (no trenca el refresh).
"""
import json
import logging
import os
from datetime import datetime, timezone

import requests

from feed import item_summary, load_feed_items

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3"
_STATE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "notifier_state.json")
)


def _load_state() -> dict:
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)


def _build_html(items: list) -> str:
    rows = []
    for it in items:
        summary = item_summary(it["changes"]).replace("\n", "<br>")
        rows.append(
            f"<div style='margin-bottom:20px'>"
            f"<strong>{it['ts'][:10]}</strong> — {it['total']} ensenyaments publicats<br>"
            f"<span style='color:#555'>{summary}</span>"
            f"</div>"
        )
    body = "\n".join(rows)
    return (
        "<html><body style='font-family:sans-serif;max-width:600px;margin:auto;padding:24px'>"
        "<h2 style='color:#1c1410'>Novetats a l'oferta de Formació Professional</h2>"
        f"{body}"
        "<hr style='margin-top:32px'>"
        "<p style='font-size:12px;color:#888'>Consulta tots els ensenyaments a "
        "<a href='https://grausfp.masellas.info'>grausfp.masellas.info</a></p>"
        "</body></html>"
    )


def notify_if_new() -> bool:
    """Crea i envia una campanya Brevo si hi ha ítems nous al feed. Retorna True si ha enviat."""
    api_key = os.environ.get("BREVO_API_KEY", "")
    list_id = os.environ.get("BREVO_LIST_ID", "")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "Cercador FP España")

    if not api_key or not list_id or not sender_email:
        logger.debug("notifier: credencials Brevo no configurades, skip")
        return False

    items = load_feed_items(max_items=5)
    if not items:
        return False

    state = _load_state()
    last_guid = state.get("last_guid")
    if items[0]["guid"] == last_guid:
        logger.debug("notifier: cap novetat des de l'últim enviament")
        return False

    new_items = []
    for it in items:
        if it["guid"] == last_guid:
            break
        new_items.append(it)

    if not new_items:
        return False

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }
    date_str = new_items[0]["ts"][:10]

    try:
        resp = requests.post(
            f"{BREVO_API_URL}/emailCampaigns",
            headers=headers,
            json={
                "name": f"FP Novetats {date_str}",
                "subject": f"Novetats FP — {date_str}",
                "sender": {"name": sender_name, "email": sender_email},
                "type": "classic",
                "htmlContent": _build_html(new_items),
                "recipients": {"listIds": [int(list_id)]},
            },
            timeout=15,
        )
        resp.raise_for_status()
        campaign_id = resp.json()["id"]

        send_resp = requests.post(
            f"{BREVO_API_URL}/emailCampaigns/{campaign_id}/sendNow",
            headers=headers,
            timeout=15,
        )
        send_resp.raise_for_status()

        _save_state({
            "last_guid": items[0]["guid"],
            "last_sent": datetime.now(timezone.utc).isoformat(),
            "last_campaign_id": campaign_id,
        })
        logger.info("notifier: campanya %s enviada (%d ítems nous)", campaign_id, len(new_items))
        return True

    except requests.RequestException as exc:
        logger.error("notifier: error enviant campanya Brevo: %s", exc)
        return False
