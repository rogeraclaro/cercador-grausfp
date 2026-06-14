# Spike 014: Disseny del feed de novetats (RSS/JSON)

> **Lliurable del pla 014** — Document de disseny, no codi de producció.
> Cobreix Steps 1–4 del pla + decisió arquitectònica sobre missatgeria als usuaris.

---

## Step 1: Elecció de format

### Comparativa

| Criteri | RSS 2.0 | Atom 1.0 | JSON Feed 1.1 |
|---------|---------|----------|---------------|
| Compatibilitat lectors RSS | Excel·lent | Excel·lent | Bona (suport creixent) |
| Generació sense deps noves | Sí (template string) | Sí (però NS XML més complex) | Sí (json.dumps estàndard) |
| Escapat d'HTML/XML | Cal escapar `<>&"'` | Cal escapar `<>&"'` | Cap risc (JSON natiu) |
| Precedent XSS (pla 009) | Risc si no s'escapa | Risc si no s'escapa | Sense risc |
| Consum per automatitzacions | Moderat | Moderat | Excel·lent (Zapier, n8n, Make) |
| Consum per newsletters de tercers (Mailchimp, Brevo...) | Excel·lent | Bo | Bo |

### Recomanació: **ambdós** (RSS 2.0 + JSON Feed)

El cost marginal de generar tots dos és ~20 línies extra de Flask (una ruta per format, mateixa funció de dades). Avantatges:
- **RSS 2.0** per a lectors clàssics i serveis de newsletter (Mailchimp, Brevo admeten RSS→email natiu).
- **JSON Feed** per a automatitzacions (Zapier, n8n, Make) que triggerarien el pla 017.

Si l'esforç ha de ser mínim, RSS 2.0 és suficient per a la primera versió.

---

## Step 2: Contracte de la ruta

### URL i headers

```
GET /api/feed.rss    → Content-Type: application/rss+xml; charset=utf-8
GET /api/feed.json   → Content-Type: application/feed+json; charset=utf-8
```

Headers de cache recomanats:
```
Cache-Control: public, max-age=3600
ETag: <hash del ts del primer item>
```
Justificació: el feed canvia com a molt un cop cada refresh (mínim 24h); cache d'1h és conservador i adequat.

### Granularitat dels ítems

**Decisió: un ítem per refresh amb canvis** (no un ítem per ensenyament nou).

Raonament:
- Un refresh pot tenir 88 altes → 88 ítems seria soroll insofrible per al subscriptor.
- El valor és saber *que hi ha hagut canvis* i tenir un resum accionable.
- Títol de l'ítem: `"Novetats FP — {N} nous ensenyaments, {M} baixa/es ({data})"`.

Refreshos sense canvis (`changes.has_changes == False` o `changes == None`): **s'ometen** del feed.

### GUID estable

```
guid = f"fp-cercador-refresh-{entry['ts']}"
```

El timestamp ISO 8601 (`ts`) és únic per entrada i immutable — no re-notificarà el mateix event. Marcat com `isPermaLink="false"` a RSS (no és una URL navegable).

### Cos de l'ítem

Inclou resum en text pla (safe per a email):
```
Nous ensenyaments per grado: A: 3, B: 12, C: 0, D: 5
Ensenyaments donats de baixa: B: 2
Noves famílies professionals: Ciberseguretat
Total actual: 1.842 ensenyaments
```

---

## Step 3: Esbós d'implementació

### Funció de dades compartida

```python
# backend/feed.py  (~30 línies)
import json, html, os
from history import HISTORY_PATH, _load_json

def _load_feed_items(max_items=20):
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

def _item_summary(ch: dict) -> str:
    """Text pla del resum de canvis (safe, sense HTML)."""
    lines = []
    if ch.get("new_by_grado"):
        parts = ", ".join(f"{g}: {len(v)}" for g, v in sorted(ch["new_by_grado"].items()))
        lines.append(f"Nous ensenyaments per grado: {parts}")
    if ch.get("removed_by_grado"):
        parts = ", ".join(f"{g}: {len(v)}" for g, v in sorted(ch["removed_by_grado"].items()))
        lines.append(f"Baixa per grado: {parts}")
    if ch.get("new_families"):
        lines.append(f"Noves famílies: {', '.join(ch['new_families'])}")
    return "\n".join(lines) if lines else "Canvis sense detall disponible."
```

### Ruta RSS 2.0 (~30 línies a app.py)

```python
from feed import _load_feed_items, _item_summary

@app.route("/api/feed.rss")
def feed_rss():
    items = _load_feed_items()
    xml_items = []
    for it in items:
        title = f"Novetats FP — {it['total']} ensenyaments ({it['ts'][:10]})"
        desc  = html.escape(_item_summary(it["changes"]))
        guid  = html.escape(it["guid"])
        pub   = it["ts"]  # ISO 8601, RFC 822 preferible però acceptat
        xml_items.append(f"""    <item>
      <title>{html.escape(title)}</title>
      <description>{desc}</description>
      <pubDate>{pub}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
    </item>""")

    body = "\n".join(xml_items) or "    <!-- Sense novetats recents -->"
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Cercador FP España — Novetats</title>
    <link>https://fp.lamosca.com</link>
    <description>Nous ensenyaments i canvis a l'oferta FP publicats pel Ministeri.</description>
    <language>ca</language>
{body}
  </channel>
</rss>"""
    return app.response_class(rss, mimetype="application/rss+xml",
                               headers={"Cache-Control": "public, max-age=3600"})
```

### Ruta JSON Feed (~20 línies a app.py)

```python
@app.route("/api/feed.json")
def feed_json():
    items = _load_feed_items()
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Cercador FP España — Novetats",
        "home_page_url": "https://fp.lamosca.com",
        "feed_url": "https://fp.lamosca.com/api/feed.json",
        "items": [
            {
                "id": it["guid"],
                "date_published": it["ts"],
                "title": f"Novetats FP — {it['total']} ensenyaments ({it['ts'][:10]})",
                "content_text": _item_summary(it["changes"]),
            }
            for it in items
        ],
    }
    return jsonify(feed), 200, {"Cache-Control": "public, max-age=3600"}
```

### Publicitat del feed

Afegir a `<head>` de `index.html` i `historial.html`:
```html
<link rel="alternate" type="application/rss+xml"
      title="Cercador FP España — Novetats"
      href="/api/feed.rss">
```

### Estimació de línies reals

| Fitxer | Línies noves |
|--------|-------------|
| `backend/feed.py` (nou) | ~35 |
| `backend/app.py` (2 rutes) | ~50 |
| `frontend/index.html` (`<link>`) | 2 |
| `frontend/historial.html` (`<link>`) | 2 |
| Tests (ruta RSS + JSON, feed buit, 0 canvis) | ~60 |
| **Total** | **~150** |

### Tests necessaris

- `test_feed_rss_empty`: historial buit → `<channel>` sense `<item>`.
- `test_feed_rss_no_changes`: entrades sense `has_changes` → feed buit.
- `test_feed_rss_with_changes`: entrada amb canvis → 1 `<item>` correcte.
- `test_feed_rss_xml_escape`: denominació amb `<>&` → escapat correctament (precedent pla 009).
- `test_feed_json_structure`: claus requerides per JSON Feed 1.1.
- `test_feed_guid_stable`: el GUID no canvia entre crides per la mateixa entrada.

---

## Step 4: Riscos i preguntes obertes

### R1 — Rotació HISTORY_MAX=20 i persistència del feed

**Problema**: amb HISTORY_MAX=20 i refreshos diaris, l'historial cobreix ~20 dies. Un subscriptor que no consulti el feed durant 3 setmanes pot perdre entrades.

**Valoració**: per a l'ús previst (lectors RSS, automatitzacions, newsletters setmanals), 20 dies és suficient. Si cal mes de cobertura, una opció és augmentar HISTORY_MAX a 60 sense impacte apreciable (les entrades slim pesen ~1–2 KB cadascuna → ~120 KB màxim).

**Decisió proposada**: mantenir HISTORY_MAX=20 ara, documentar el límit al feed (`<description>`). Si un subscriptor ho reporta com a problema, augmentar a 60.

### R2 — i18n: denominacions en castellà, UI en català

No és un problema per al feed: les denominacions venen del Ministeri (castellà) i el feed és per a consum automatitzat. El títol i descripció del canal poden ser bilingües o en castellà, que és la llengua del contingut.

### R3 — Arquitectura de missatgeria als usuaris registrats

**Decisió de producte capturada en aquest spike:**

El feed RSS/JSON és el canal *públic i sense auth*. Per als usuaris registrats, el projecte necessitarà enviar dos tipus de missatges:
1. **Avisos automàtics de novetats** (quan el feed detecta canvis).
2. **Newsletters manuals** (contingut editorial del propietari).

**Recomanació: delegar l'enviament a un servei extern** (Brevo, Mailchimp o similar) en comptes de construir un hub de missatgeria propi. Raons:
- Evita construir gestió de llistes, baixes (mandatory GDPR), bounces, templates HTML, queues de reintents, etc.
- Brevo i Mailchimp admeten **RSS-to-email natiu**: consumeixen `/api/feed.rss` i envien l'email automàticament quan hi ha items nous. Això resol el pla 017 sense codi addicional a l'app.
- El plan 016 (login d'usuaris) pot gestionar la subscripció (email + opt-in) i passar l'adreça al servei extern via API. La gestió de preferències viu a la app; l'enviament viu al servei extern.
- Cost: Brevo free tier (300 emails/dia) és suficient per a la fase inicial.

**Impacte sobre el pla 017** (alertes personalitzades): en lloc de construir un motor d'enviament propi, el pla 017 hauria de dissenyar la integració amb el servei extern triat (webhook o API call post-refresh quan `has_changes == True`).

### R4 — Seguretat: el feed no requereix auth

Consistent amb `/api/refresh-history` (ja públic). El feed no exposa dades sensibles: només denominacions d'ensenyaments oficials publicades pel Ministeri.

---

## Exemple complet del feed generat

### RSS 2.0

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Cercador FP España — Novetats</title>
    <link>https://fp.lamosca.com</link>
    <description>Nous ensenyaments i canvis a l'oferta FP publicats pel Ministeri.</description>
    <language>ca</language>
    <item>
      <title>Novetats FP — 1.842 ensenyaments (2026-06-14)</title>
      <description>Nous ensenyaments per grado: B: 3, C: 1
Noves famílies: Ciberseguretat</description>
      <pubDate>2026-06-14T08:00:00+00:00</pubDate>
      <guid isPermaLink="false">fp-cercador-refresh-2026-06-14T08:00:00+00:00</guid>
    </item>
    <item>
      <title>Novetats FP — 1.838 ensenyaments (2026-06-07)</title>
      <description>Nous ensenyaments per grado: A: 1, D: 3
Baixa per grado: B: 1</description>
      <pubDate>2026-06-07T08:00:00+00:00</pubDate>
      <guid isPermaLink="false">fp-cercador-refresh-2026-06-07T08:00:00+00:00</guid>
    </item>
  </channel>
</rss>
```

### JSON Feed 1.1

```json
{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "Cercador FP España — Novetats",
  "home_page_url": "https://fp.lamosca.com",
  "feed_url": "https://fp.lamosca.com/api/feed.json",
  "items": [
    {
      "id": "fp-cercador-refresh-2026-06-14T08:00:00+00:00",
      "date_published": "2026-06-14T08:00:00+00:00",
      "title": "Novetats FP — 1.842 ensenyaments (2026-06-14)",
      "content_text": "Nous ensenyaments per grado: B: 3, C: 1\nNoves famílies: Ciberseguretat"
    },
    {
      "id": "fp-cercador-refresh-2026-06-07T08:00:00+00:00",
      "date_published": "2026-06-07T08:00:00+00:00",
      "title": "Novetats FP — 1.838 ensenyaments (2026-06-07)",
      "content_text": "Nous ensenyaments per grado: A: 1, D: 3\nBaixa per grado: B: 1"
    }
  ]
}
```

---

## Estimació d'esforç del pla de construcció

| | |
|-|-|
| **Esforç total** | S (petit) — ~150 línies de codi + ~60 de tests |
| **Temps estimat** | 2–3 hores d'implementació + 1h de tests |
| **Risc** | BAIX — cap canvi a lògica existent; dues rutes noves llegint dades ja calculades |
| **Dependències noves** | Cap |
| **Prerequisits** | Plans 005 i 006 DONE (verificat: sí) |
| **Prioritat recomanada** | P3 — útil però no crític; implementar quan s'abordi el pla 016/017 |

**Recomanació d'ordre**: implementar el feed (pla de construcció) *abans* del pla 017, ja que el feed pot ser el mecanisme que triggeregi les alertes via RSS-to-email del servei extern, eliminant codi personalitzat al backend.
