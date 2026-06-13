"""
test_history.py — Tests del mòdul history.py (format slim + snapshot separat).
"""
import json

import pytest

import history

RESULT_A = {
    "total": 100,
    "by_grado": {"A": 50, "B": 50},
    "families": ["Informàtica"],
    "denominacions": ["Prog", "Admin"],
    "denominacions_by_grado": {"A": ["Prog"], "B": ["Admin"]},
    "unknown_families": [],
    "duration_seconds": 1.0,
}

RESULT_B = {
    "total": 101,
    "by_grado": {"A": 51, "B": 50},
    "families": ["Informàtica", "Sanitari"],
    "denominacions": ["Prog", "Admin", "Infermeria"],
    "denominacions_by_grado": {"A": ["Prog"], "B": ["Admin"], "C": ["Infermeria"]},
    "unknown_families": [],
    "duration_seconds": 1.2,
}


@pytest.fixture(autouse=True)
def isolate_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setattr(history, "SNAPSHOT_PATH", str(tmp_path / "snapshot.json"))


def test_append_slim_entry():
    history.append(RESULT_A)
    data = json.loads(open(history.HISTORY_PATH, encoding="utf-8").read())
    entry = data[0]
    assert "families" not in entry
    assert "denominacions" not in entry
    assert "denominacions_by_grado" not in entry
    for key in ("ts", "total", "by_grado", "unknown_families", "duration_seconds", "changes"):
        assert key in entry


def test_first_append_changes_none():
    history.append(RESULT_A)
    data = json.loads(open(history.HISTORY_PATH, encoding="utf-8").read())
    assert data[0]["changes"] is None


def test_second_append_diffs_against_snapshot():
    history.append(RESULT_A)
    history.append(RESULT_B)
    data = json.loads(open(history.HISTORY_PATH, encoding="utf-8").read())
    entry = data[0]
    assert entry["changes"] is not None
    assert "Infermeria" in entry["changes"]["new_denominacions"]
    assert entry["changes"]["has_changes"] is True


def test_history_max_truncation():
    for i in range(history.HISTORY_MAX + 2):
        r = {**RESULT_A, "total": i}
        history.append(r)
    data = json.loads(open(history.HISTORY_PATH, encoding="utf-8").read())
    assert len(data) == history.HISTORY_MAX


def test_snapshot_updated():
    history.append(RESULT_A)
    snap = json.loads(open(history.SNAPSHOT_PATH, encoding="utf-8").read())
    assert snap["denominacions"] == RESULT_A["denominacions"]
    assert snap["families"] == RESULT_A["families"]
