# Plan 006: Aprimar l'historial públic (d'11,5 MB a KB), activar gzip i cachejar /api/ofertes

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- backend/history.py backend/app.py frontend/historial.html`
> Aquest pla pressuposa que el pla 005 ja ha creat `backend/history.py`.
> Si no existeix, STOP (executa primer el pla 005).

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (canvia el format de persistència d'un endpoint públic — el frontend s'ha verificat compatible, però revisa-ho)
- **Depends on**: plans/005-historial-del-refresh-programat.md
- **Category**: perf
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

`backend/data/refresh_history.json` fa **11,5 MB** i `/api/refresh-history`
el serveix sencer, sense autenticació ni compressió, a cada visita de
`historial.html`. La causa: cada entrada persisteix les llistes completes de
~12.200 denominacions (`denominacions`, `denominacions_by_grado`, `families`),
que només es necessiten per calcular el diff amb el refresh SEGÜENT — el
frontend no les pinta mai (només usa `ts`, `total`, `by_grado`,
`duration_seconds`, `unknown_families` i `changes`). A més: (a) hi ha
entrades amb `changes` d'1,6 MB produïdes per arrencades de format antic,
(b) `/api/ofertes` rellegeix i reparseja 3,7 MB de disc a cada petició, i
(c) el vhost nginx no comprimeix les respostes JSON del proxy.

Resultat esperat: historial de KB en lloc de MB, i `/api/ofertes` servit
des de memòria i comprimit.

## Current state

Fitxers rellevants (rutes relatives a `fp-cercador/`, excepte nginx):

- `backend/history.py` (creat pel pla 005) — `append(result)` construeix
  l'entrada amb els camps: `ts, total, by_grado, families, denominacions,
  denominacions_by_grado, unknown_families, duration_seconds, changes`.
  `compute_changes(curr, prev)` diffeja l'entrada nova contra `history[0]`
  usant les llistes completes de l'entrada anterior.
- `backend/app.py`:
  - `/api/ofertes` (post-pla-005, originàriament línies 176–187): obre i fa
    `json.load` de `DATA_PATH` (3,7 MB, 12.894 registres) a CADA petició i
    `jsonify(data)` el torna a serialitzar.
  - `/api/refresh-history`: retorna el fitxer sencer.
- `frontend/historial.html` — funció `load()` (línies ~239 endavant):
  només llegeix `entry.ts`, `entry.total`, `entry.by_grado`,
  `entry.duration_seconds`, `entry.unknown_families` (només `.length`) i
  `entry.changes` (tots els subcamps). Gestiona `changes === null`
  ("Primer registre") i `has_changes === false` ("Sense canvis").
  **No llegeix mai** `entry.families`, `entry.denominacions` ni
  `entry.denominacions_by_grado`.
- `deploy/nginx-cloudpanel.conf` (a l'ARREL DEL REPO GIT, directori pare de
  `fp-cercador/`) — bloc `location /api/` amb `proxy_pass` a
  `127.0.0.1:8033`; sense directives gzip.
- Mida actual de cada entrada (mesurat): camps resum ~200 bytes; llistes
  completes ~1 MB; `changes` d'artefactes de bootstrap ~1,6 MB.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/backend/`) | Esperat |
|---|---|---|
| Suite | `python -m pytest tests/ -q` | 0 failed |
| Mida historial | `ls -la data/refresh_history.json` | < 100 KB en acabar |
| Servidor local | `python app.py` + `curl -s http://localhost:5001/api/refresh-history \| head -c 300` | JSON vàlid |

## Scope

**In scope**:
- `backend/history.py`
- `backend/app.py` (només la ruta `/api/ofertes` — cache)
- `backend/data/refresh_history.json` i `backend/data/last_snapshot.json`
  (via script de migració)
- `backend/tests/test_history.py` (crear)
- `deploy/nginx-cloudpanel.conf`
- `deploy/DEPLOY.md` (nota de redesplegament)

**Out of scope**:
- `frontend/historial.html` — NO el modifiquis; el format slim és un
  subconjunt del que ja consumeix. Si descobreixes que llegeix un camp que
  has eliminat, STOP.
- `scrapers/pipeline.py` — el dict que retorna `run()` no canvia.
- El nombre màxim d'entrades (`HISTORY_MAX = 20`) — no el toquis.

## Git workflow

- 3 commits a `master`:
  1. `perf(history): entrades slim + snapshot separat per al diff`
  2. `perf(api): cache en memòria de /api/ofertes per mtime`
  3. `perf(deploy): gzip per a respostes JSON al vhost nginx`
- NO push sense instrucció.

## Steps

### Step 1: Reestructurar history.append amb snapshot separat

A `backend/history.py`:

1. Afegeix la constant:
   ```python
   SNAPSHOT_PATH = os.path.normpath(
       os.path.join(os.path.dirname(__file__), "data", "last_snapshot.json")
   )
   ```
2. Reescriu `append(result)` amb aquest flux:
   ```python
   def append(result: dict) -> None:
       """Afegeix una entrada SLIM a l'historial i actualitza l'snapshot.

       L'snapshot (last_snapshot.json) guarda les llistes completes del
       darrer refresh — només serveixen per diffejar el refresh següent.
       Les entrades de l'historial només porten el resum + changes.
       """
       full = {
           "total": result.get("total"),
           "by_grado": result.get("by_grado"),
           "families": result.get("families", []),
           "denominacions": result.get("denominacions", []),
           "denominacions_by_grado": result.get("denominacions_by_grado", {}),
       }
       prev = _load_json(SNAPSHOT_PATH)          # dict o None
       entry = {
           "ts": datetime.now(timezone.utc).isoformat(),
           "total": result.get("total"),
           "by_grado": result.get("by_grado"),
           "unknown_families": result.get("unknown_families", []),
           "duration_seconds": result.get("duration_seconds"),
           "changes": compute_changes(full, prev) if prev else None,
       }
       history = _load_json(HISTORY_PATH) or []
       history.insert(0, entry)
       history = history[:HISTORY_MAX]
       _write_atomic(history, HISTORY_PATH)
       _write_atomic(full, SNAPSHOT_PATH)
   ```
   Implementa els helpers `_load_json(path)` (retorna None si no existeix o
   és invàlid) i `_write_atomic(data, path)` (tempfile + `os.replace`,
   mateix patró que ja hi ha al codi actual). `compute_changes` no canvia.
3. `compute_changes(full, prev)` rep ara el dict "full" (amb llistes) i
   l'snapshot anterior — les mateixes claus que abans; la signatura i el cos
   no canvien.

**Verify**: `python -c "import history; print('OK')"` → OK.

### Step 2: Migrar el fitxer existent

Executa un cop des de `backend/` (després d'haver fet el pla 001, que ja ha
netejat les entrades mock):

```bash
python - <<'EOF'
import json, os

HP = "data/refresh_history.json"
SP = "data/last_snapshot.json"
BOOTSTRAP_THRESHOLD = 1000  # diffs amb >1000 altes/baixes són artefactes de canvi de format

with open(HP, encoding="utf-8") as f:
    history = json.load(f)

# 1) Snapshot des de l'entrada més recent que tingui llistes completes
snap = next((e for e in history if e.get("denominacions")), None)
if snap:
    with open(SP, "w", encoding="utf-8") as f:
        json.dump({
            "total": snap.get("total"),
            "by_grado": snap.get("by_grado"),
            "families": snap.get("families", []),
            "denominacions": snap.get("denominacions", []),
            "denominacions_by_grado": snap.get("denominacions_by_grado", {}),
        }, f, ensure_ascii=False)
    print("Snapshot creat des de l'entrada", snap["ts"])
else:
    print("AVÍS: cap entrada amb llistes completes; snapshot no creat")

# 2) Aprimar entrades
EMPTY_CHANGES = {
    "new_families": [], "removed_families": [], "grado_deltas": {},
    "total_delta": 0, "new_denominacions": [], "removed_denominacions": [],
    "new_by_grado": {}, "removed_by_grado": {}, "has_changes": False,
}
for e in history:
    for k in ("families", "denominacions", "denominacions_by_grado"):
        e.pop(k, None)
    c = e.get("changes")
    if c and (len(c.get("new_denominacions") or []) > BOOTSTRAP_THRESHOLD
              or len(c.get("removed_denominacions") or []) > BOOTSTRAP_THRESHOLD):
        e["changes"] = dict(EMPTY_CHANGES)  # artefacte de bootstrap, no canvi real

with open(HP, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False)
print("Migrat:", os.path.getsize(HP), "bytes")
EOF
```

**Verify**: `ls -la data/refresh_history.json` → mida < 100 KB, i
`python -c "import json; json.load(open('data/refresh_history.json'))"` net.

### Step 3: Tests del nou format

Crea `backend/tests/test_history.py` (patró: `tests/test_api.py`), amb
fixture autouse que redirigeixi `history.HISTORY_PATH` i
`history.SNAPSHOT_PATH` a `tmp_path`. Tests mínims:

1. **test_append_slim_entry** — després d'`append(result)`, l'entrada NO té
   les claus `families`/`denominacions`/`denominacions_by_grado` i SÍ té
   `ts/total/by_grado/unknown_families/duration_seconds/changes`.
2. **test_first_append_changes_none** — sense snapshot previ,
   `changes is None`.
3. **test_second_append_diffs_against_snapshot** — dos `append` amb
   denominacions diferents → el segon té `changes.new_denominacions` /
   `removed_denominacions` correctes i `has_changes True`.
4. **test_history_max_truncation** — `HISTORY_MAX + 2` appends → queden
   `HISTORY_MAX` entrades.
5. **test_snapshot_updated** — després d'append, `SNAPSHOT_PATH` conté les
   llistes completes de l'últim result.

**Verify**: `python -m pytest tests/test_history.py -q` → 5 passed.

### Step 4: Cache en memòria de /api/ofertes

A `backend/app.py`, substitueix el cos de `get_ofertes` per una versió amb
cache per mtime (evita reparsejar 3,7 MB a cada petició i la doble
serialització de `jsonify`):

```python
_ofertes_cache = {"mtime": None, "body": None}

@app.route("/api/ofertes")
def get_ofertes():
    """API-01 / API-02: Retorna tots els registres (cache en memòria per mtime)."""
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "Data not available. Run /api/admin/refresh first."}), 503
    try:
        mtime = os.path.getmtime(DATA_PATH)
        if _ofertes_cache["mtime"] != mtime:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                body = f.read()
            json.loads(body)  # valida abans de cachejar
            _ofertes_cache.update(mtime=mtime, body=body)
        return app.response_class(_ofertes_cache["body"], mimetype="application/json")
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("ofertes.json unreadable: %s", exc)
        return jsonify({"error": "Data file is corrupt. Run /api/admin/refresh."}), 503
```

ATENCIÓ: els tests existents de `/api/ofertes` (`test_api.py:73-99`)
mockegen `app.os.path.exists`, `app.json.load` i `builtins.open`. Amb el
codi nou, `app.json.load` ja no es crida (ara és `json.loads`). Adapta
`test_ofertes_200` perquè mockegi el nou flux (p. ex. `app.os.path.exists`,
`app.os.path.getmtime` i `builtins.open` amb `mock_open(read_data='[{"id":1,"denominacion":"Test","grado":"A"}]')`)
i reseteja `_ofertes_cache` a la fixture (afegeix
`monkeypatch.setattr("app._ofertes_cache", {"mtime": None, "body": None})`
o reset directe dins el test).

**Verify**: `python -m pytest tests/test_api.py -q` → tots passen.

### Step 5: gzip al vhost nginx

A `deploy/nginx-cloudpanel.conf` (arrel del repo git), dins el bloc
`server { listen 443 ... }`, abans dels `location`, afegeix:

```nginx
    # Compressió per a les respostes JSON del backend i estàtics
    gzip on;
    gzip_types application/json text/css application/javascript;
    gzip_min_length 1024;
    gzip_comp_level 5;
    gzip_proxied any;   # comprimir també respostes del proxy_pass
```

I a `deploy/DEPLOY.md` afegeix una línia a la secció de nginx indicant que
cal recarregar nginx en aplicar el fitxer (`nginx -t && systemctl reload nginx`).

**Verify**: `grep -n "gzip" deploy/nginx-cloudpanel.conf` → 5 línies noves.

### Step 6: Smoke test local

```bash
cd backend && python app.py &
sleep 2
curl -s http://localhost:5001/api/refresh-history | python -m json.tool > /dev/null && echo "history OK"
curl -s http://localhost:5001/api/ofertes | python -c "import sys,json; print(len(json.load(sys.stdin)), 'registres')"
kill %1
```
→ `history OK` i `12894 registres` (o el total vigent).

Després obre `frontend/historial.html` al navegador (amb el servidor encara
engegat o desplegat) i confirma visualment que la taula es renderitza i que
les entrades migrades mostren "Sense canvis" o els seus chips de canvis.

## Test plan

5 tests nous a `backend/tests/test_history.py` (Step 3) + adaptació de
`test_ofertes_200` (Step 4). Patró estructural: `tests/test_api.py`.
Verificació final: `python -m pytest tests/ -q` → 0 failed.

## Done criteria

- [ ] `backend/data/refresh_history.json` < 100 KB
- [ ] `backend/data/last_snapshot.json` existeix i conté `denominacions` no buides
- [ ] `python -c "import json; h=json.load(open('backend/data/refresh_history.json')); assert all('denominacions' not in e for e in h)"` net
- [ ] `cd backend && python -m pytest tests/ -q` → 0 failed
- [ ] `grep -c gzip deploy/nginx-cloudpanel.conf` ≥ 5
- [ ] Smoke test del Step 6 passat
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- `backend/history.py` no existeix (el pla 005 no s'ha executat).
- `frontend/historial.html` llegeix algun dels camps eliminats
  (`entry.families`, `entry.denominacions`, `entry.denominacions_by_grado`)
  — re-verifica amb `grep -n "entry\.families\|entry\.denominacions" frontend/historial.html`
  abans del Step 2; si surt res, STOP.
- Després de la migració l'historial té 0 entrades o el JSON no és vàlid
  (restaura del backup — fes `cp data/refresh_history.json data/refresh_history.json.bak`
  ABANS del Step 2).
- Els tests de `/api/ofertes` no es poden adaptar sense canviar el
  comportament observable de l'endpoint (status codes i cossos d'error han
  de quedar idèntics).

## Maintenance notes

- `last_snapshot.json` és un artefacte de runtime: ha d'estar cobert pel
  `.gitignore` (el pla 010 ignora tot `backend/data/`; si el 010 encara no
  s'ha fet, afegeix la línia manualment si cal).
- Al VPS caldrà executar la mateixa migració del Step 2 sobre el fitxer del
  servidor (vegeu `plans/instructions.md`).
- Si mai s'afegeix paginació o filtres a l'historial, el cache d'ofertes és
  el patró a replicar (cache per mtime, invalidació automàtica en refresh
  perquè `os.replace` canvia el mtime).
- Revisor: vigileu el llindar `BOOTSTRAP_THRESHOLD = 1000` de la migració —
  qualsevol refresh real amb >1000 altes seria tractat com a artefacte; al
  catàleg FP això no passa (els canvis reals són desenes), però és una
  decisió de judici.
