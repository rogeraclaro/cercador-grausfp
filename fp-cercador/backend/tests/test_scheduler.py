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
