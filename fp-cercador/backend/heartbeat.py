"""
heartbeat.py — avisa Uptime Kuma (monitor de tipus push) del resultat del refresc programat.

Si KUMA_PUSH_URL no hi és, no fa res. Un refresc amb errors es marca "down" amb el
motiu, i Kuma envia el correu; amb només avisos queda "up" amb els avisos al missatge
(Pla 095: un avís deixava el monitor caigut i l'error de debò ja no avisava). Si no
arriba cap avís dins l'interval del monitor (p. ex. 8 dies), Kuma també avisa que el
refresc no s'ha fet.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

_MAX_MSG = 250  # Kuma guarda el missatge a l'historial; n'hi ha prou amb el resum


def report_refresh(result, error=None):
    # Kuma mostra l'URL amb "?status=up&msg=OK&ping=" al darrere: ens quedem només amb la base
    url = os.environ.get("KUMA_PUSH_URL", "").strip().split("?")[0]
    if not url:
        return
    errors = [error] if error else list(result.get("errors", []))
    warnings = [] if error else list(result.get("warnings", []))
    if errors:
        status, msg = "down", " | ".join(str(p) for p in errors)
    else:
        status, msg = "up", f"refresc OK: {result.get('total')} registres"
        if warnings:
            msg += f" ({len(warnings)} avisos: " + " | ".join(str(w) for w in warnings) + ")"
    try:
        requests.get(url, params={"status": status, "msg": msg[:_MAX_MSG]}, timeout=10)
    except Exception as exc:
        logger.error("heartbeat: no s'ha pogut avisar Kuma: %s", exc)
