"""Tests per a feed.py: generació RSS i JSON Feed."""
import pytest
import feed as feed_module


def _make_entry(ts="2026-06-14T08:00:00+00:00", has_changes=True,
                new_by_grado=None, removed_by_grado=None, new_families=None,
                total=100):
    return {
        "ts": ts,
        "total": total,
        "changes": {
            "has_changes": has_changes,
            "new_by_grado": new_by_grado or {},
            "removed_by_grado": removed_by_grado or {},
            "new_families": new_families or [],
        },
        "guid": f"fp-cercador-refresh-{ts}",
    }


class TestLoadFeedItems:
    def test_empty_history(self, tmp_path, monkeypatch):
        monkeypatch.setattr(feed_module, "HISTORY_PATH", str(tmp_path / "h.json"))
        assert feed_module.load_feed_items() == []

    def test_skips_entries_without_changes(self, tmp_path, monkeypatch, json_file):
        path = json_file(tmp_path, [{"ts": "2026-01-01T00:00:00+00:00",
                                      "total": 10, "changes": {"has_changes": False}}])
        monkeypatch.setattr(feed_module, "HISTORY_PATH", path)
        assert feed_module.load_feed_items() == []

    def test_skips_entries_with_null_changes(self, tmp_path, monkeypatch, json_file):
        path = json_file(tmp_path, [{"ts": "2026-01-01T00:00:00+00:00",
                                      "total": 10, "changes": None}])
        monkeypatch.setattr(feed_module, "HISTORY_PATH", path)
        assert feed_module.load_feed_items() == []


class TestRenderRss:
    def test_empty_feed(self):
        rss = feed_module.render_rss([])
        assert "<item>" not in rss
        assert "<?xml" in rss

    def test_item_present(self):
        entry = _make_entry(new_by_grado={"B": ["Curs X"]})
        rss = feed_module.render_rss([entry])
        assert "<item>" in rss
        assert "2026-06-14" in rss

    def test_xml_escaping(self):
        entry = _make_entry(new_families=["Família <Especial> & Rara"])
        rss = feed_module.render_rss([entry])
        assert "<Especial>" not in rss
        assert "&lt;Especial&gt;" in rss

    def test_guid_stable(self):
        entry = _make_entry()
        rss1 = feed_module.render_rss([entry])
        rss2 = feed_module.render_rss([entry])
        import re
        guids = re.findall(r"<guid[^>]*>(.*?)</guid>", rss1)
        assert len(guids) == 1
        assert guids[0] in rss2


class TestRenderJsonFeed:
    def test_structure(self):
        data = feed_module.render_json_feed([])
        assert data["version"] == "https://jsonfeed.org/version/1.1"
        assert "items" in data

    def test_item_fields(self):
        entry = _make_entry(new_by_grado={"A": ["Curs A"]})
        data = feed_module.render_json_feed([entry])
        item = data["items"][0]
        assert "id" in item
        assert "date_published" in item
        assert "content_text" in item


# fixture auxiliar
@pytest.fixture
def json_file():
    import json

    def _write(tmp_path, data):
        p = tmp_path / "h.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    return _write
