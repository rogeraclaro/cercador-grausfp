"""
feed.py — Generació del feed de novetats RSS 2.0 i JSON Feed 1.1.

Llegeix l'historial existent (history.HISTORY_PATH) i retorna només
les entrades amb canvis reals (has_changes == True).
"""
import html
import json

from history import HISTORY_PATH, _load_json


def load_feed_items(max_items: int = 20) -> list:
    """Retorna entrades d'historial amb canvis, màx max_items."""
    history = _load_json(HISTORY_PATH) or []
    items = []
    for entry in history:
        ch = entry.get("changes")
        if not ch or not ch.get("has_changes"):
            continue
        items.append({
            "ts": entry["ts"],
            "total": entry.get("total", 0),
            "changes": ch,
            "guid": f"fp-cercador-refresh-{entry['ts']}",
        })
        if len(items) >= max_items:
            break
    return items


def item_summary(ch: dict) -> str:
    """Text pla del resum de canvis (sense HTML, safe per a email)."""
    lines = []
    if ch.get("new_by_grado"):
        parts = ", ".join(
            f"{g}: {len(v)}" for g, v in sorted(ch["new_by_grado"].items())
        )
        lines.append(f"Nous ensenyaments per grado: {parts}")
    if ch.get("removed_by_grado"):
        parts = ", ".join(
            f"{g}: {len(v)}" for g, v in sorted(ch["removed_by_grado"].items())
        )
        lines.append(f"Baixa per grado: {parts}")
    if ch.get("new_families"):
        lines.append(f"Noves famílies: {', '.join(ch['new_families'])}")
    return "\n".join(lines) if lines else "Canvis sense detall disponible."


def render_rss(items: list, base_url: str = "https://grausfp.masellas.info") -> str:
    """Genera el XML RSS 2.0 complet."""
    xml_items = []
    for it in items:
        title = f"Novetats FP — {it['total']} ensenyaments ({it['ts'][:10]})"
        desc = html.escape(item_summary(it["changes"]))
        guid = html.escape(it["guid"])
        xml_items.append(
            f"    <item>\n"
            f"      <title>{html.escape(title)}</title>\n"
            f"      <description>{desc}</description>\n"
            f"      <pubDate>{it['ts']}</pubDate>\n"
            f"      <guid isPermaLink=\"false\">{guid}</guid>\n"
            f"    </item>"
        )
    body = "\n".join(xml_items) if xml_items else "    <!-- Sense novetats recents -->"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '    <title>Cercador FP España — Novetats</title>\n'
        f'    <link>{base_url}</link>\n'
        '    <description>Nous ensenyaments i canvis a l\'oferta FP publicats pel Ministeri.</description>\n'
        '    <language>ca</language>\n'
        f'{body}\n'
        '  </channel>\n'
        '</rss>'
    )


def render_json_feed(items: list, base_url: str = "https://grausfp.masellas.info") -> dict:
    """Genera l'estructura JSON Feed 1.1."""
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Cercador FP España — Novetats",
        "home_page_url": base_url,
        "feed_url": f"{base_url}/api/feed.json",
        "items": [
            {
                "id": it["guid"],
                "date_published": it["ts"],
                "title": f"Novetats FP — {it['total']} ensenyaments ({it['ts'][:10]})",
                "content_text": item_summary(it["changes"]),
            }
            for it in items
        ],
    }
