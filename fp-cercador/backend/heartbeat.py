"""
heartbeat.py — avisa Uptime Kuma (monitor de tipus push) del resultat del refresc programat.

Si KUMA_PUSH_URL no hi és, no fa res. Un refresc amb errors o avisos es marca "down"
amb el motiu, i Kuma envia el correu; si no arriba cap avís dins l'interval del
monitor (p. ex. 8 dies), Kuma també avisa que el refresc no s'ha fet.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

_MAX_MSG = 250  # Kuma guarda el missatge a l'historial; n'hi ha prou amb el resum


def report_refresh(result, error=None):
    url = os.environ.get("KUMA_PUSH_URL", "").strip()
    if not url:
        return
    problems = [error] if error else list(result.get("errors", [])) + list(result.get("warnings", []))
    if problems:
        status, msg = "down", " | ".join(str(p) for p in problems)
    else:
        status, msg = "up", f"refresc OK: {result.get('total')} registres"
    try:
        requests.get(url, params={"status": status, "msg": msg[:_MAX_MSG]}, timeout=10)
    except Exception as exc:
        logger.error("heartbeat: no s'ha pogut avisar Kuma: %s", exc)
