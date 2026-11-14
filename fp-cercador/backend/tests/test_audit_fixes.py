"""Regressions de l'auditoria 2026-11-14."""
import json
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("ADMIN_TOKEN", "test-token")

from app import app as flask_app  # noqa: E402
import alerts_service  # noqa: E402
import centres_watch_service  # noqa: E402
import db  # noqa: E402
from scrapers import centres_scraper  # noqa: E402

flask_app.config["TESTING"] = True


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    test_db = str(tmp_path / "test.db")
    original = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = test_db
    db.init_db(db_path=test_db)
    yield
    if original is None:
        os.environ.pop("DB_PATH", None)
    else:
        os.environ["DB_PATH"] = original


def _client_for(email):
    c = flask_app.test_client()
    with patch("email_service.send_verification_email"):
        c.post("/api/auth/register", data=json.dumps({"email": email, "password": "password123"}),
               content_type="application/json")
    conn = db.get_db()
    conn.execute("UPDATE users SET verified = 1 WHERE email = ?", (email,))
    conn.commit()
    uid = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
    conn.close()
    assert c.post("/api/auth/login", data=json.dumps({"email": email, "password": "password123"}),
                  content_type="application/json").status_code == 200
    return c, uid


def _post_alert(c, filter_json):
    return c.post("/api/alerts", data=json.dumps({"filter_json": filter_json}),
                  content_type="application/json")


@pytest.mark.parametrize("filter_json", [
    {"familia": 123},
    {"texto": ["a"]},
    {"texto": "x" * 201},
    {"grado": "D", "nivel": "alt"},
])
def test_alert_rejects_filters_the_matcher_cannot_evaluate(filter_json):
    c, _ = _client_for("a@test.com")
    assert _post_alert(c, filter_json).status_code == 400


def test_alert_accepts_numeric_nivel():
    c, _ = _client_for("a@test.com")
    assert _post_alert(c, {"grado": "D", "nivel": 2}).status_code == 201


@pytest.mark.parametrize("service, token_type, prefix", [
    (alerts_service, "alert_unsubscribe", "alert_7_"),
    (centres_watch_service, "centres_watch_unsubscribe", "cw_7_"),
])
def test_expired_unsubscribe_token_is_replaced(service, token_type, prefix):
    _, uid = _client_for("a@test.com")
    conn = db.get_db()
    conn.execute(
        "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, ?, '2000-01-01 00:00:00')",
        (uid, prefix + "old", token_type),
    )
    conn.commit()
    fresh = service._get_or_create_unsubscribe_token(conn, 7, uid)
    conn.commit()
    rows = conn.execute("SELECT token, expires_at FROM tokens WHERE type = ?", (token_type,)).fetchall()
    conn.close()
    assert fresh != "old"
    assert [r["token"] for r in rows] == [prefix + fresh]
    assert rows[0]["expires_at"] > "2026"


def test_observatory_returns_the_latest_rows_in_chronological_order():
    conn = db.get_db()
    for day in range(1, 6):
        conn.execute(
            "INSERT INTO observatory_snapshots (ts, total, total_a, total_b, total_c, total_d, total_e, "
            "n_altes, n_baixes, families_amb_altes) VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, '[]')",
            (f"2026-01-0{day}T00:00:00", day),
        )
    conn.commit()
    rows = db.query_observatory(conn, limit=3)
    conn.close()
    assert [r["total"] for r in rows] == [3, 4, 5]


def test_centres_refresh_keeps_enriched_url_web(tmp_path, monkeypatch):
    centres_path = tmp_path / "centres.json"
    monkeypatch.setattr(centres_scraper, "_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(centres_scraper, "_CENTRES_PATH", str(centres_path))
    monkeypatch.setattr(centres_scraper, "_OFERTA_CENTRES_PATH", str(tmp_path / "oferta_centres.json"))
    centres_path.write_text(json.dumps([{"id": "1", "url_web": "https://a.example"}, {"id": "2", "url_web": None}]))
    scraped = {"1": {"id": "1", "url_web": None}, "2": {"id": "2", "url_web": None},
               "3": {"id": "3", "url_web": None}}
    monkeypatch.setattr(centres_scraper, "scrape_centres", lambda on_progress=None: (scraped, {"K": ["1"]}))

    centres_scraper.build_centres_data()

    saved = {c["id"]: c["url_web"] for c in json.loads(centres_path.read_text())}
    assert saved == {"1": "https://a.example", "2": None, "3": None}
    assert not list(tmp_path.glob("*.tmp"))


def test_persistent_429_raises_instead_of_reporting_no_centres(monkeypatch):
    class _Resp:
        status_code = 429

    class _Session:
        def get(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr(centres_scraper.time, "sleep", lambda s: None)
    with pytest.raises(centres_scraper.requests.RequestException):
        centres_scraper._fetch(_Session(), {})


def _records(**counts):
    return [{"grado": g} for g, n in counts.items() for _ in range(n)]


@pytest.mark.parametrize("new", [
    _records(A=100, D=0),      # un scraper ha tornat [] sense error
    _records(A=100, D=9),      # menys de la meitat
    _records(D=20),            # un grau sencer ha desaparegut
])
def test_implausible_catalog_is_rejected(new, monkeypatch):
    from scrapers import pipeline
    monkeypatch.delenv("REFRESH_ALLOW_DROP", raising=False)
    with pytest.raises(pipeline.ImplausibleCatalogError):
        pipeline.check_catalog_plausible(_records(A=100, D=20), new)


def test_plausible_catalog_passes(monkeypatch):
    from scrapers import pipeline
    monkeypatch.delenv("REFRESH_ALLOW_DROP", raising=False)
    pipeline.check_catalog_plausible(_records(A=100, D=20), _records(A=90, D=10, E=3))
    pipeline.check_catalog_plausible([], _records(A=1))  # primer refresc
    monkeypatch.setenv("REFRESH_ALLOW_DROP", "1")
    pipeline.check_catalog_plausible(_records(A=100), [])
