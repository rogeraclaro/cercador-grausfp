"""
test_heartbeat.py — el refresc programat avisa Uptime Kuma (monitor de tipus push).
Sense KUMA_PUSH_URL no fa res; amb errors o avisos el refresc es marca com a caigut.
"""
import heartbeat


class FakeGet:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if self.fail:
            raise OSError("xarxa caiguda")


def test_sense_url_no_fa_cap_peticio(monkeypatch):
    fake = FakeGet()
    monkeypatch.delenv("KUMA_PUSH_URL", raising=False)
    monkeypatch.setattr(heartbeat.requests, "get", fake)
    heartbeat.report_refresh({"total": 10, "errors": [], "warnings": []})
    assert fake.calls == []


def test_refresc_net_envia_up(monkeypatch):
    fake = FakeGet()
    monkeypatch.setenv("KUMA_PUSH_URL", "https://status.example/api/push/abc")
    monkeypatch.setattr(heartbeat.requests, "get", fake)
    heartbeat.report_refresh({"total": 13006, "errors": [], "warnings": []})
    url, params, timeout = fake.calls[0]
    assert url == "https://status.example/api/push/abc"
    assert params["status"] == "up"
    assert "13006" in params["msg"]
    assert timeout


def test_avisos_o_errors_envien_down_amb_el_motiu(monkeypatch):
    fake = FakeGet()
    monkeypatch.setenv("KUMA_PUSH_URL", "https://status.example/api/push/abc")
    monkeypatch.setattr(heartbeat.requests, "get", fake)
    heartbeat.report_refresh({"total": 13006, "errors": [], "warnings": ["foment: 51 cursos (abans 178)"]})
    heartbeat.report_refresh({"total": 0, "errors": ["todofp no respon"], "warnings": []})
    assert [c[1]["status"] for c in fake.calls] == ["down", "down"]
    assert "foment" in fake.calls[0][1]["msg"]
    assert "todofp" in fake.calls[1][1]["msg"]


def test_excepcio_del_refresc_envia_down(monkeypatch):
    fake = FakeGet()
    monkeypatch.setenv("KUMA_PUSH_URL", "https://status.example/api/push/abc")
    monkeypatch.setattr(heartbeat.requests, "get", fake)
    heartbeat.report_refresh(None, error="pipeline petat")
    assert fake.calls[0][1]["status"] == "down"
    assert "pipeline petat" in fake.calls[0][1]["msg"]


def test_si_kuma_no_respon_no_peta(monkeypatch):
    monkeypatch.setenv("KUMA_PUSH_URL", "https://status.example/api/push/abc")
    monkeypatch.setattr(heartbeat.requests, "get", FakeGet(fail=True))
    heartbeat.report_refresh({"total": 1, "errors": [], "warnings": []})
