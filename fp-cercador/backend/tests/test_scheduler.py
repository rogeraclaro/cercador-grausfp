"""test_scheduler.py — _scheduled_refresh escriu historial i gestiona el lock."""
import json
import unittest.mock as mock

import pytest

import history
import refresh_state
import scheduler_service

RESULT = {
    "total": 5, "by_grado": {"A": 5}, "families": ["Química"],
    "denominacions": ["X"], "denominacions_by_grado": {"A": ["X"]},
    "errors": [], "unknown_families": [], "duration_seconds": 1.0,
}


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_PATH", str(tmp_path / "h.json"))
    # Without this the scheduled refresh overwrites the real data/last_snapshot.json.
    monkeypatch.setattr(history, "SNAPSHOT_PATH", str(tmp_path / "snap.json"))
    if refresh_state._lock.locked():
        refresh_state._lock.release()
    yield
    if refresh_state._lock.locked():
        refresh_state._lock.release()


def test_scheduled_refresh_appends_history(tmp_path):
    with mock.patch("scheduler_service.pipeline.run", return_value=RESULT):
        scheduler_service._scheduled_refresh()
    data = json.load(open(history.HISTORY_PATH, encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["total"] == 5


def test_scheduled_refresh_skips_if_lock_held():
    refresh_state._lock.acquire()
    try:
        with mock.patch("scheduler_service.pipeline.run") as run_mock:
            scheduler_service._scheduled_refresh()
        run_mock.assert_not_called()
    finally:
        refresh_state._lock.release()


def test_scheduled_refresh_history_failure_does_not_break_state():
    with mock.patch("scheduler_service.pipeline.run", return_value=RESULT), \
         mock.patch("scheduler_service.history.append", side_effect=OSError("disc ple")):
        scheduler_service._scheduled_refresh()
    assert refresh_state.get_state()["status"] == "done"
    assert not refresh_state._lock.locked()


def test_scheduled_refresh_exposa_warnings_no_fatals():
    """Pla 074: els avisos no fatals del pipeline arriben a /api/refresh-status."""
    result = {**RESULT, "warnings": ["Requisits E «X»: títol no lligat a cap D: Y"]}
    with mock.patch("scheduler_service.pipeline.run", return_value=result):
        scheduler_service._scheduled_refresh()
    assert refresh_state.get_state()["warnings"] == result["warnings"]


def test_scheduled_refresh_sends_brevo_news_and_alerts_like_the_manual_one(monkeypatch):
    """Abans només el refresc manual enviava la campanya de Brevo i passava BASE_URL."""
    monkeypatch.setenv("BASE_URL", "https://base.example")
    monkeypatch.setenv("SITE_URL", "https://site.example/")
    with mock.patch("scheduler_service.pipeline.run", return_value=RESULT), \
         mock.patch("notifier.notify_if_new") as notify, \
         mock.patch("alerts_service.dispatch_alerts") as dispatch:
        scheduler_service._scheduled_refresh()
    notify.assert_called_once_with("https://site.example")
    dispatch.assert_called_once_with(RESULT, base_url="https://base.example")
    assert not refresh_state._lock.locked()


# --- Pla 095: refresc robust (fase a l'error, un sol reintent, correu propi) ---

@pytest.fixture
def failing_env(tmp_path, monkeypatch):
    """Pipeline que peta a la primera fase; SMTP i heartbeat substituïts."""
    monkeypatch.setattr(scheduler_service, "ALERT_STAMP_PATH", str(tmp_path / "alert.json"))
    ofertes = tmp_path / "ofertes.json"
    ofertes.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(scheduler_service.pipeline, "DATA_PATH", str(ofertes))
    sent, beats = [], []
    monkeypatch.setattr("email_service.send_email", lambda *a: sent.append(a))
    monkeypatch.setattr(scheduler_service.heartbeat, "report_refresh",
                        lambda result, error=None: beats.append(error))

    def boom(on_progress=None):
        on_progress("Buscador Graus A/B/C")
        raise ConnectionError("Connection reset by peer")

    monkeypatch.setattr(scheduler_service.pipeline, "run", boom)
    return sent, beats


class FakeScheduler:
    def __init__(self):
        self.jobs = []
        self.removed = []

    def add_job(self, func, trigger, **kw):
        self.jobs.append((func, trigger, kw))

    def get_job(self, job_id):
        return None

    def remove_job(self, job_id):
        self.removed.append(job_id)


def test_error_conserva_la_fase_al_missatge(failing_env, monkeypatch):
    sent, beats = failing_env
    monkeypatch.setattr(scheduler_service, "_scheduler", None)
    refresh_state._lock.acquire()
    assert scheduler_service.run_refresh_job() is False
    st = refresh_state.get_state()
    assert st["status"] == "error"
    assert st["phase"] == "Buscador Graus A/B/C"
    assert st["errors"] == ["Buscador Graus A/B/C: Connection reset by peer"]
    assert beats == ["Buscador Graus A/B/C: Connection reset by peer"]
    assert not refresh_state._lock.locked()


def test_refresc_programat_fallat_es_reprograma_una_sola_vegada(failing_env, monkeypatch):
    sent, _ = failing_env
    fake = FakeScheduler()
    monkeypatch.setattr(scheduler_service, "_scheduler", fake)
    scheduler_service._scheduled_refresh()
    assert len(fake.jobs) == 1
    func, trigger, kw = fake.jobs[0]
    assert func is scheduler_service._scheduled_refresh and trigger == "date"
    assert kw["kwargs"] == {"is_retry": True}
    assert kw["id"] == scheduler_service.RETRY_JOB_ID
    assert refresh_state.get_state()["retry_at"]
    assert sent == []  # encara queda el reintent: no s'avisa
    # El reintent també falla: no se'n programa cap altre i s'envia el correu.
    scheduler_service._scheduled_refresh(is_retry=True)
    assert len(fake.jobs) == 1
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert "Buscador Graus A/B/C" in subject + body
    assert "Connection reset by peer" in body


def test_refresc_manual_fallat_no_es_reprograma_i_avisa(failing_env, monkeypatch):
    sent, _ = failing_env
    fake = FakeScheduler()
    monkeypatch.setattr(scheduler_service, "_scheduler", fake)
    refresh_state._lock.acquire()
    scheduler_service.run_refresh_job()
    assert fake.jobs == []
    assert len(sent) == 1


def test_correu_d_error_una_vegada_per_fallada(failing_env, monkeypatch):
    sent, _ = failing_env
    monkeypatch.setattr(scheduler_service, "_scheduler", None)
    for _ in range(2):
        refresh_state._lock.acquire()
        scheduler_service.run_refresh_job()
    assert len(sent) == 1
    assert "Últimes dades bones" in sent[0][2]


def test_correu_d_error_que_falla_no_trenca_l_estat(failing_env, monkeypatch):
    def smtp_down(*a):
        raise OSError("smtp down")
    monkeypatch.setattr("email_service.send_email", smtp_down)
    monkeypatch.setattr(scheduler_service, "_scheduler", None)
    refresh_state._lock.acquire()
    scheduler_service.run_refresh_job()
    assert refresh_state.get_state()["status"] == "error"
    assert not refresh_state._lock.locked()


def test_refresc_correcte_anul_la_el_reintent_pendent(monkeypatch):
    fake = FakeScheduler()
    fake.get_job = lambda job_id: object() if job_id == scheduler_service.RETRY_JOB_ID else None
    monkeypatch.setattr(scheduler_service, "_scheduler", fake)
    monkeypatch.setattr(scheduler_service.heartbeat, "report_refresh", lambda *a, **k: None)
    refresh_state._lock.acquire()
    with mock.patch("scheduler_service.pipeline.run", return_value=RESULT), \
         mock.patch("notifier.notify_if_new"), mock.patch("alerts_service.dispatch_alerts"):
        assert scheduler_service.run_refresh_job() is True
    assert fake.removed == [scheduler_service.RETRY_JOB_ID]
    assert refresh_state.get_state()["retry_at"] is None


def test_last_success_iso_es_el_mtime_d_ofertes(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler_service.pipeline, "DATA_PATH", str(tmp_path / "no.json"))
    assert scheduler_service.last_success_iso() is None
    ofertes = tmp_path / "ofertes.json"
    ofertes.write_text("[]", encoding="utf-8")
    import os
    os.utime(ofertes, (1764000000, 1764000000))
    monkeypatch.setattr(scheduler_service.pipeline, "DATA_PATH", str(ofertes))
    assert scheduler_service.last_success_iso().startswith("2025-11-24T")
