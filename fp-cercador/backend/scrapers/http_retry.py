"""
http_retry.py — Reintents de xarxa per a les fases fatals del refresc (Pla 095).

Un sol tall de connexió (2026-11-22, ConnectionResetError a la primera fase) va
tombar el refresc de tota la setmana. Només es reintenten errors de connexió,
timeouts i respostes HTTP >= 500; un 4xx o un error de parseig es propaga igual.
"""
import logging
import time

import requests

logger = logging.getLogger(__name__)

# Espera abans de cada reintent: 1 intent + 3 reintents com a màxim.
RETRY_DELAYS = (10, 30, 90)

_RETRYABLE = (requests.ConnectionError, requests.Timeout)


def get_with_retry(get, url, *, delays=None, **kwargs):
    """
    Crida get(url, **kwargs) (requests.get o session.get) amb reintents.

    Retorna la resposta (també un 4xx, o l'últim 5xx si s'esgoten els reintents,
    perquè el raise_for_status() de qui crida el converteixi en HTTPError).
    Si l'últim intent acaba en error de connexió, el propaga.
    """
    delays = RETRY_DELAYS if delays is None else delays
    for attempt, delay in enumerate((*delays, None), start=1):
        try:
            resp = get(url, **kwargs)
        except _RETRYABLE as exc:
            if delay is None:
                raise
            reason = repr(exc)
        else:
            status = getattr(resp, "status_code", None)
            if delay is None or not (isinstance(status, int) and status >= 500):
                return resp
            reason = f"HTTP {status}"
        logger.warning("http_retry: %s ha fallat (%s); reintent %d/%d d'aquí a %d s",
                       url, reason, attempt, len(delays), delay)
        time.sleep(delay)
