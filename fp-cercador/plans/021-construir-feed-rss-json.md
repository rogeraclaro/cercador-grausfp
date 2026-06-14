# Plan 021: Construir el feed de novetats RSS 2.0 i JSON Feed

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `python -c "import history; print(history.HISTORY_MAX)"`
> Ha de retornar `20`. Si `history.py` no té `HISTORY_MAX` o `compute_changes`,
> els plans 005/006 no s'han executat — STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/005, plans/006, plans/014 (spike de disseny)
- **Category**: feature
- **Planned at**: 2026-06-14, derivat del spike `plans/014-spike-feed-de-novetats.md`

## Why this matters

El backend ja calcula, a cada refresh, exactament quins ensenyaments nous
s'han publicat i quins han desaparegut (`history.compute_changes`). Avui
aquesta informació només és consultable visitant `historial.html`. Dues rutes
noves (`/api/feed.rss` i `/api/feed.json`) la fan subscrivible per a:

- **Lectors RSS** (Feedly, NetNewsWire, etc.) usats per orientadors i centres de FP.
- **Brevo RSS-to-email**: consumint `/api/feed.rss` enviarà automàticament
  les novetats als usuaris subscrits sense codi addicional al backend
  (decisió arquitectònica del pla 014 + 017).
- **Automatitzacions** (Zapier, n8n, Make) via JSON Feed.

Cost: ~150 línies, cap dependència nova, risc baix (les dades ja existeixen).

## Current state

- `backend/history.py`: entrades amb `ts, total, by_grado, changes`, on
  `changes.new_by_grado` és `{grado: [denominacions...]}` i
  `changes.has_changes` indica si hi ha hagut canvis.
- `backend/app.py`: rutes públiques sense auth existents
  (`/api/refresh-history`) — el feed segueix el mateix patró.
- `backend/feed.py`: **no existeix** — s'ha de crear.
- `frontend/index.html` i `frontend/historial.html`: no tenen `<link rel="alternate">`.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/backend/`) | Esperat |
|---|---|---|
| Verificar drift check | `python -c "import history; print(history.HISTORY_MAX)"` | `20` |
| Executar tests | `python -m pytest tests/ -v` | Tots verds |
| Verificar ruta RSS | `curl -s http://localhost:5001/api/feed.rss \| head -5` | `<?xml version` |
| Verificar ruta JSON | `curl -s http://localhost:5001/api/feed.json \| python -m json.tool \| head -10` | JSON vàlid amb clau `version` |
| Verificar feed buit | (amb historial buit) ruta RSS → `<channel>` sense `<item>` | cap `<item>` |

## Scope

**In scope**:
- `backend/feed.py` (nou): funció de dades i generació dels dos formats.
- `backend/app.py`: dues rutes noves (`/api/feed.rss`, `/api/feed.json`) i actualització del docstring.
- `backend/tests/test_feed.py` (nou): 6 tests unitaris.
- `frontend/index.html`: afegir `<link rel="alternate">` al `<head>`.
- `frontend/historial.html`: afegir `<link rel="alternate">` al `<head>`.

**Out of scope**:
- Cap canvi a `history.py`, `scheduler_service.py` ni cap altre mòdul existent.
- Cap canvi visual al frontend (el `<link>` és invisible per a l'usuari).
- Integració amb Brevo (és configuració externa, no codi d'aquest projecte).

## Git workflow

- Un commit a `master`: `feat(backend): feed RSS 2.0 i JSON Feed de novetats (/api/feed.rss, /api/feed.json)`
- NO push sense instrucció explícita.

## Steps

### Step 1: Crear `backend/feed.py`

Crea el fitxer `backend/feed.py` amb el contingut següent:

```python
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


def render_rss(items: list, base_url: str = "https://fp.lamosca.com") -> str:
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


def render_json_feed(items: list, base_url: str = "https://fp.lamosca.com") -> dict:
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
```

**Verify**: `python -c "import feed; print('OK')"` (des de `backend/`) → `OK`

### Step 2: Afegir les dues rutes a `app.py`

**2a. Actualitza el docstring** a la capçalera de `app.py` (bloc de "Rutes"):

Afegeix dues línies al comentari de rutes:
```
  GET    /api/feed.rss               → Feed RSS 2.0 de novetats (sense auth)
  GET    /api/feed.json              → Feed JSON Feed 1.1 de novetats (sense auth)
```

**2b. Afegeix l'import** de `feed` just sota dels altres imports locals (al costat de `import history`):
```python
import feed
```

**2c. Afegeix les dues rutes** just abans o just després de la ruta `/api/refresh-history` (per mantenir agrupades les rutes públiques sense auth):

```python
@app.route("/api/feed.rss")
def api_feed_rss():
    items = feed.load_feed_items()
    rss = feed.render_rss(items)
    return app.response_class(
        rss,
        mimetype="application/rss+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.route("/api/feed.json")
def api_feed_json():
    items = feed.load_feed_items()
    data = feed.render_json_feed(items)
    return jsonify(data), 200, {"Cache-Control": "public, max-age=3600"}
```

**Verify**: `python -c "from app import app; print([r.rule for r in app.url_map.iter_rules() if 'feed' in r.rule])"` (des de `backend/`) → `['/api/feed.rss', '/api/feed.json']` (ordre pot variar)

### Step 3: Crear `backend/tests/test_feed.py`

Crea el fitxer `backend/tests/test_feed.py`:

```python
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
        entry = _make_entry(new_by_grado={"B": ["Tècnic en <Res> & Coses"]})
        rss = feed_module.render_rss([entry])
        assert "<Res>" not in rss
        assert "&lt;Res&gt;" in rss

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
```

**Verify**: `python -m pytest tests/test_feed.py -v` → tots els tests verds.

### Step 4: Afegir `<link rel="alternate">` als HTMLs

A `frontend/index.html`, dins el `<head>`, afegeix (just abans del `</head>`):
```html
<link rel="alternate" type="application/rss+xml" title="Cercador FP España — Novetats" href="/api/feed.rss">
```

A `frontend/historial.html`, dins el `<head>`, afegeix la mateixa línia.

**Verify**: `grep 'feed.rss' frontend/index.html frontend/historial.html` → 2 resultats (un per fitxer).

### Step 5: Executar la suite completa de tests

```bash
cd backend && python -m pytest tests/ -v
```

Ha de passar tota la suite (no només `test_feed.py`). Si algun test falla per
causes no relacionades amb els canvis d'aquest pla, STOP i informa.

### Step 6: Verificació manual amb el servidor local

```bash
cd backend && python app.py
```

En una altra terminal:
```bash
curl -s http://localhost:5001/api/feed.rss | head -8
curl -s http://localhost:5001/api/feed.json | python -m json.tool | head -12
```

Confirma:
- `/api/feed.rss` retorna XML vàlid amb `Content-Type: application/rss+xml`.
- `/api/feed.json` retorna JSON vàlid amb clau `version`.
- Si l'historial no té entrades amb canvis, els feeds retornen buits (sense error 500).

## Test plan

6 tests unitaris a `tests/test_feed.py` cobreixen:
- Historial buit → feed buit.
- Entrades sense `has_changes` → omeses.
- Entrades amb `changes: null` → omeses.
- Presència d'ítems quan hi ha canvis.
- Escapat XML (precedent del pla 009).
- GUID estable entre crides.
- Estructura JSON Feed 1.1.

No es fan tests d'integració HTTP per a les rutes (l'arquitectura actual no té
client de test Flask configurat per a rutes; els tests de `feed.py` cobreixen
la lògica).

## Done criteria

- [ ] `backend/feed.py` existeix i `python -c "import feed; print('OK')"` retorna `OK`
- [ ] `GET /api/feed.rss` retorna XML vàlid (status 200, Content-Type `application/rss+xml`)
- [ ] `GET /api/feed.json` retorna JSON vàlid amb clau `version` (status 200)
- [ ] `python -m pytest tests/test_feed.py -v` → tots verds
- [ ] `python -m pytest tests/ -v` → tota la suite verda (sense regressions)
- [ ] `grep 'feed.rss' frontend/index.html frontend/historial.html` → 2 resultats
- [ ] `git status` mostra només els 5 fitxers esperats: `backend/feed.py`, `backend/app.py`, `backend/tests/test_feed.py`, `frontend/index.html`, `frontend/historial.html`
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- El drift check falla (`history.HISTORY_MAX` no existeix) — plans 005/006 pendents.
- `python -m pytest tests/ -v` falla en tests NO relacionats amb `test_feed.py` — hi ha una regressió preexistent; no és culpa d'aquest pla però cal informar.
- Les rutes de feed retornen 500 amb l'historial real (pot indicar un camp `changes` amb estructura inesperada).

## Maintenance notes

- **Brevo RSS-to-email**: un cop desplegat, configurar a Brevo una campanya
  RSS que apunti a `https://fp.lamosca.com/api/feed.rss`. No cal cap canvi
  de codi addicional per enviar emails de novetats als subscrits.
- **HISTORY_MAX i cobertura del feed**: amb 20 entrades i refreshos diaris, el
  feed cobreix ~20 dies. Si cal més cobertura, augmentar `HISTORY_MAX` a 60
  a `history.py` (les entrades slim pesen ~1–2 KB cadascuna).
- **Escapat XML**: tota dada scrapejada que vagi al RSS passa per `html.escape()`
  — el mateix principi que el pla 009 per a `historial.html`.
