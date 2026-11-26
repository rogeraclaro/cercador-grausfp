"""
scheduler_service.py — Wrapper APScheduler per al refresh periòdic (Fase 6, D-06/D-07/D-09).

Persisteix la config a backend/data/scheduler.json. Flask la llegeix a l'arrencada
i reprograma el job. Reutilitza refresh_state._lock per evitar concurrència amb
/api/admin/refresh manual.
"""
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

import heartbeat
import history
import refresh_state
from scrapers import pipeline

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "scheduler.json")
)

JOB_ID = "weekly_refresh"
# Pla 095: segon intent puntual d'un refresc programat fallat (només un).
RETRY_JOB_ID = "weekly_refresh_retry"
RETRY_DELAY = timedelta(hours=2)

# Segell del correu d'error del refresc (mateix patró que pipeline._notify_admin_soc_failure).
ALERT_STAMP_PATH = os.path.join(os.path.dirname(CONFIG_PATH), "last_refresh_alert.json")
_ALERT_INTERVAL = 24 * 3600
_OCUP_JOB_ID = "monthly_ocupaciones"

VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun", "*"}

DEFAULT_CONFIG = {
    "enabled": False,
    "day_of_week": "mon",
    "hour": 3,
    "minute": 0,
}

_scheduler: Optional[BackgroundScheduler] = None


def _write_atomic(data: dict, path: str) -> None:
    dir_path = os.path.dirname(path) or "."
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".json", dir=dir_path, delete=False
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def load_config() -> dict:
    """Llegeix scheduler.json o retorna DEFAULT_CONFIG si no existeix / és invàlid."""
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("scheduler.json invalid (%s); usant defaults", exc)
        return dict(DEFAULT_CONFIG)
    out = dict(DEFAULT_CONFIG)
    out["enabled"] = bool(cfg.get("enabled", False))
    dow = str(cfg.get("day_of_week", "mon")).lower()
    out["day_of_week"] = dow if dow in VALID_DAYS else "mon"
    try:
        out["hour"] = max(0, min(23, int(cfg.get("hour", 3))))
        out["minute"] = max(0, min(59, int(cfg.get("minute", 0))))
    except (TypeError, ValueError):
        out["hour"], out["minute"] = 3, 0
    return out


def save_config(cfg: dict) -> dict:
    """Valida i persisteix la config; retorna la config validada."""
    validated = dict(DEFAULT_CONFIG)
    validated["enabled"] = bool(cfg.get("enabled", False))
    dow = str(cfg.get("day_of_week", "mon")).lower()
    if dow not in VALID_DAYS:
        raise ValueError(f"day_of_week ha de ser un de {sorted(VALID_DAYS)}")
    validated["day_of_week"] = dow
    try:
        h = int(cfg.get("hour", 3))
        m = int(cfg.get("minute", 0))
    except (TypeError, ValueError):
        raise ValueError("hour i minute han de ser enters")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("hour 0-23, minute 0-59")
    validated["hour"] = h
    validated["minute"] = m
    _write_atomic(validated, CONFIG_PATH)
    return validated


def _run_ocupaciones_job() -> None:
    """Job mensual: regenera l'índex d'ocupacions (F6) via subprocess."""
    import subprocess
    import sys as _sys
    import os as _os
    repo_root = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), '..'))
    script = _os.path.join(repo_root, 'scripts', 'generate_ocupaciones.py')
    try:
        subprocess.run([_sys.executable, script], check=True)
        logger.info("monthly_ocupaciones: completat")
    except Exception as exc:
        logger.error("monthly_ocupaciones: error: %s", exc)


def last_success_iso() -> Optional[str]:
    """Data de les últimes dades bones: mtime d'ofertes.json (només l'escriu un refresc correcte)."""
    try:
        mtime = os.path.getmtime(pipeline.DATA_PATH)
    except OSError:
        return None
    return datetime.fromtimestamp(mtime, timezone.utc).isoformat()


def _notify_admin_refresh_failure() -> None:
    """Pla 095: correu a l'admin quan el refresc acaba en error (segell 24 h, no repeteix)."""
    try:
        with open(ALERT_STAMP_PATH, encoding="utf-8") as fh:
            last = json.load(fh) or {}
    except (OSError, ValueError):
        last = {}
    if time.time() - float(last.get("ts", 0)) < _ALERT_INTERVAL:
        return
    st = refresh_state.get_state()
    errors = "\n".join(str(e) for e in st.get("errors") or []) or "(sense detalls)"
    try:
        import email_service
        to = os.environ.get("ADMIN_ALERT_EMAIL") or os.environ.get("EMAIL_FROM", "noreply@grausfp.es")
        email_service.send_email(
            to,
            f"Refresc GrausFP fallat ({st.get('phase') or 'fase desconeguda'})",
            f"El refresc de dades ha fallat.\n\n"
            f"Fase: {st.get('phase') or '(desconeguda)'}\n"
            f"Error:\n{errors}\n\n"
            f"Inici de l'intent (UTC): {st.get('last_run')}\n"
            f"Últimes dades bones (ofertes.json, UTC): {last_success_iso() or '(cap)'}\n\n"
            "El cercador continua servint les dades anteriors.",
        )
    except Exception as send_exc:  # l'avís no ha de trencar el refresc
        logger.warning("refresh: no s'ha pogut avisar l'admin de l'error: %s", send_exc)
    try:
        _write_atomic({"ts": time.time()}, ALERT_STAMP_PATH)
    except OSError:
        pass


def run_refresh_job(notify_on_error: bool = True) -> bool:
    """
    Refresc complet: pipeline + historial + novetats de Brevo + alertes + heartbeat.

    L'únic camí per al refresc programat i per al manual del panell d'admin, perquè
    facin exactament el mateix. Qui el crida ja té refresh_state._lock; aquí s'allibera.

    Retorna True si ha acabat bé. Si falla i notify_on_error, envia el correu a l'admin
    (el refresc programat el desactiva quan encara li queda el reintent, Pla 095).
    """
    import alerts_service
    import notifier

    # Mateixos valors per defecte que app.py (no es pot importar: seria circular).
    base_url = os.environ.get("BASE_URL", "http://localhost:5001")
    site_url = os.environ.get("SITE_URL", "https://grausfp.es").rstrip("/")
    refresh_state.set_state(
        status="running",
        last_run=datetime.now(timezone.utc).isoformat(),
        total=None,
        by_grado=None,
        duration_seconds=None,
        errors=[],
        warnings=[],
        phase=None,
        retry_at=None,
    )
    ok = False
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
        ok = True
        _cancel_retry()
        # El heartbeat va abans dels correus: un SMTP lent no ha de fer saltar l'alarma.
        heartbeat.report_refresh(result)
        try:
            history.append(result)
        except Exception as exc_h:
            logger.error("Could not write refresh history: %s", exc_h)
        try:
            notifier.notify_if_new(site_url)
        except Exception as exc_n:
            logger.error("Could not send Brevo notification: %s", exc_n)
        try:
            alerts_service.dispatch_alerts(result, base_url=base_url)
        except Exception as exc_a:
            logger.error("Could not dispatch alerts: %s", exc_a)
    except Exception as exc:
        # Pla 095: es conserva la fase on ha petat perquè l'error digui on ha fallat.
        phase = refresh_state.get_state().get("phase")
        msg = f"{phase}: {exc}" if phase else str(exc)
        logger.error("refresh failed: %s", msg)
        refresh_state.set_state(status="error", errors=[msg], phase=phase)
        heartbeat.report_refresh(None, error=msg)
        if notify_on_error:
            _notify_admin_refresh_failure()
    finally:
        refresh_state._lock.release()
    return ok


def _cancel_retry() -> None:
    """Un refresc correcte fa innecessari el reintent pendent."""
    if _scheduler is None:
        return
    try:
        if _scheduler.get_job(RETRY_JOB_ID) is not None:
            _scheduler.remove_job(RETRY_JOB_ID)
            logger.info("scheduler: reintent del refresc anul·lat (ja hi ha dades noves)")
    except Exception as exc:  # el job pot haver desaparegut entremig
        logger.warning("scheduler: no s'ha pogut anul·lar el reintent: %s", exc)


def _schedule_retry() -> bool:
    """Programa un sol reintent puntual al cap de RETRY_DELAY. False si no s'ha pogut."""
    if _scheduler is None:
        return False
    run_date = datetime.now(timezone.utc) + RETRY_DELAY
    try:
        _scheduler.add_job(
            func=_scheduled_refresh,
            trigger="date",
            run_date=run_date,
            kwargs={"is_retry": True},
            id=RETRY_JOB_ID,
            replace_existing=True,
        )
    except Exception as exc:
        logger.error("scheduler: no s'ha pogut programar el reintent: %s", exc)
        return False
    refresh_state.set_state(retry_at=run_date.isoformat())
    logger.info("scheduler: refresc fallat; reintent programat per a %s", run_date.isoformat())
    return True


def _scheduled_refresh(is_retry: bool = False) -> None:
    """
    Funció invocada per APScheduler. Reutilitza el mateix lock que admin_refresh.

    Pla 095: si el refresc setmanal falla, se'n programa un segon intent al cap de
    2 h (només un: el reintent no es reprograma). El correu a l'admin s'envia quan
    ja no queda cap intent.
    """
    if not refresh_state._lock.acquire(blocking=False):
        logger.info("scheduled_refresh: refresh ja en curs, omès")
        return
    will_retry = not is_retry and _scheduler is not None
    if not run_refresh_job(notify_on_error=not will_retry) and will_retry:
        if not _schedule_retry():
            _notify_admin_refresh_failure()


def apply_config(cfg: dict) -> None:
    """Programa o desprograma el job segons cfg.enabled."""
    if _scheduler is None:
        raise RuntimeError("scheduler not initialized; call init_scheduler() first")
    existing = _scheduler.get_job(JOB_ID)
    if cfg.get("enabled"):
        _scheduler.add_job(
            func=_scheduled_refresh,
            trigger="cron",
            day_of_week=cfg["day_of_week"],
            hour=cfg["hour"],
            minute=cfg["minute"],
            id=JOB_ID,
            replace_existing=True,
        )
        logger.info("scheduler job programat: %s %02d:%02d",
                    cfg["day_of_week"], cfg["hour"], cfg["minute"])
    elif existing is not None:
        _scheduler.remove_job(JOB_ID)
        logger.info("scheduler job eliminat")


def get_next_run_iso() -> Optional[str]:
    if _scheduler is None:
        return None
    job = _scheduler.get_job(JOB_ID)
    if job is None or job.next_run_time is None:
        return None
    return job.next_run_time.isoformat()


def init_scheduler() -> None:
    """Arrenca el BackgroundScheduler i aplica la config persistida."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.start()
    cfg = load_config()
    apply_config(cfg)
    # Job mensual per regenerar l'índex d'ocupacions de F6.
    # S'executa el 1r de cada mes a les 04:00 UTC, DESPRÉS del refresh setmanal
    # (que sol ser dilluns a les 03:00).
    if _scheduler.get_job(_OCUP_JOB_ID) is None:
        _scheduler.add_job(
            _run_ocupaciones_job, 'cron',
            day=1, hour=4, minute=0,
            id=_OCUP_JOB_ID, replace_existing=True,
        )
