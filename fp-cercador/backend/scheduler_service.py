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
from datetime import datetime, timezone
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


def run_refresh_job() -> None:
    """
    Refresc complet: pipeline + historial + novetats de Brevo + alertes + heartbeat.

    L'únic camí per al refresc programat i per al manual del panell d'admin, perquè
    facin exactament el mateix. Qui el crida ja té refresh_state._lock; aquí s'allibera.
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
    )
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
        logger.error("refresh failed: %s", exc)
        refresh_state.set_state(status="error", errors=[str(exc)], phase=None)
        heartbeat.report_refresh(None, error=str(exc))
    finally:
        refresh_state._lock.release()


def _scheduled_refresh() -> None:
    """Funció invocada per APScheduler. Reutilitza el mateix lock que admin_refresh."""
    if not refresh_state._lock.acquire(blocking=False):
        logger.info("scheduled_refresh: refresh ja en curs, omès")
        return
    run_refresh_job()


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
