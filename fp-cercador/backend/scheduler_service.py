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
import threading
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

import history
import refresh_state
from scrapers import pipeline

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "scheduler.json")
)

JOB_ID = "weekly_refresh"

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


def _scheduled_refresh() -> None:
    """Funció invocada per APScheduler. Reutilitza el mateix lock que admin_refresh."""
    acquired = refresh_state._lock.acquire(blocking=False)
    if not acquired:
        logger.info("scheduled_refresh: refresh ja en curs, omès")
        return
    refresh_state.set_state(
        status="running",
        last_run=datetime.now(timezone.utc).isoformat(),
        total=None,
        by_grado=None,
        duration_seconds=None,
        errors=[],
    )
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
            import alerts_service
            alerts_service.dispatch_alerts(result)
        except Exception as exc_a:
            logger.error("Could not dispatch alerts: %s", exc_a)
    except Exception as exc:
        logger.error("scheduled_refresh failed: %s", exc)
        refresh_state.set_state(status="error", errors=[str(exc)])
    finally:
        refresh_state._lock.release()


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
