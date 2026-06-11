# Plan 001: Aïllar els tests de les dades de producció i netejar l'historial contaminat

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- backend/tests/test_api.py backend/app.py`
> Si algun fitxer in-scope ha canviat des que es va escriure el pla, compara
> els extractes de "Current state" amb el codi viu; si no coincideixen,
> tracta-ho com a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: cap
- **Category**: bug
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

Executar la suite de tests **escriu dades falses al fitxer de producció**
`backend/data/refresh_history.json`. El test `test_refresh_started` mockeja
`pipeline.run` però no l'escriptura d'historial: el thread de fons que llança
`/api/admin/refresh` crida `_append_history(result)` amb el resultat mock
(`total=100`), i això s'afegeix al fitxer real. Cada entrada falsa, a més,
genera un diff espuri d'~1,6 MB (12.208 denominacions "eliminades") que es
mostra públicament a `historial.html`. Està verificat empíricament: el fitxer
actual conté com a mínim entrades contaminades amb `total=100` (la 0 i la 4
en el moment de l'auditoria, i possiblement més si algú ha tornat a executar
pytest).

## Current state

Fitxers rellevants (rutes relatives a `fp-cercador/`):

- `backend/app.py` — l'endpoint `/api/admin/refresh` (línies 209–261) llança
  un thread que crida `_append_history(result)` (línia 242). `HISTORY_PATH`
  es defineix a les línies 52–54:
  ```python
  HISTORY_PATH = os.path.normpath(
      os.path.join(os.path.dirname(__file__), "data", "refresh_history.json")
  )
  ```
- `backend/tests/test_api.py` — el test culpable (línies 153–163):
  ```python
  def test_refresh_started(client):
      """API-03: POST /api/admin/refresh llança el pipeline en background..."""
      import time
      with mock.patch(PATCH_PIPELINE_RUN, return_value=MOCK_PIPELINE_RESULT):
          r = client.post("/api/admin/refresh",
                          headers={"Authorization": "Bearer test-token"})
      assert r.status_code == 200
      assert r.get_json() == {"status": "started"}
      time.sleep(0.05)
  ```
  `MOCK_PIPELINE_RESULT` (línies 18–23) té `total: 100` i
  `by_grado: {"A": 20, "B": 20, "C": 20, "D": 20, "E": 20}` — aquesta és la
  signatura per identificar entrades contaminades.
- `backend/data/refresh_history.json` — fitxer de dades real, contaminat.

Convencions del repo: els tests usen fixtures pytest amb `mock.patch` i
constants de patch-path al principi del mòdul (vegeu `test_api.py:15-16`).
Hi ha una fixture `autouse` existent (`reset_refresh_state`,
`test_api.py:29-46`) que serveix de patró.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/backend/`) | Esperat |
|---|---|---|
| Tests API | `python -m pytest tests/test_api.py -q` | 9 passed |
| Suite completa | `python -m pytest tests/ -q` | (de moment 10 failed, 59 passed — els 10 trencats els arregla el pla 002; aquí només importa que test_api passi) |
| Hash del fitxer de dades | `md5 data/refresh_history.json` | per comparar abans/després |

## Scope

**In scope** (únics fitxers a modificar):
- `backend/tests/test_api.py`
- `backend/data/refresh_history.json` (només via l'script de neteja del Step 3)

**Out of scope** (NO tocar encara que sembli relacionat):
- `backend/app.py` — no canviïs `_append_history` ni les rutes; el refactor
  d'historial és el pla 005.
- `backend/tests/test_pipeline.py` i `test_html_scraper.py` — els arregla el pla 002.
- `backend/scheduler_service.py`.

## Git workflow

- El repo treballa directament a `master`, amb missatges estil conventional
  commits en català (exemple del log: `fix(scraper): tracking manual de cookies...`).
- Fes 2 commits: un per l'aïllament dels tests, un per la neteja de dades.
- NO facis push si l'operador no ho ha demanat.

## Steps

### Step 1: Afegir fixture autouse que redirigeix HISTORY_PATH a un directori temporal

A `backend/tests/test_api.py`, després de la fixture `reset_refresh_state`
(línia 46) i abans de la fixture `client`, afegeix:

```python
@pytest.fixture(autouse=True)
def isolate_history(tmp_path, monkeypatch):
    """Evita que els tests escriguin a backend/data/refresh_history.json real."""
    import app
    monkeypatch.setattr(app, "HISTORY_PATH", str(tmp_path / "refresh_history.json"))
```

Nota: importar `app` dins la fixture (no al nivell de mòdul) perquè
`ADMIN_TOKEN` ja està garantit per `conftest.py` i no volem efectes
col·laterals en temps de col·lecció.

**Verify** (des de `backend/`):
```bash
md5 data/refresh_history.json && python -m pytest tests/test_api.py -q && md5 data/refresh_history.json
```
→ `9 passed` i els dos hashos md5 **idèntics** (el fitxer real no s'ha tocat).

### Step 2: Executar la suite dues vegades per confirmar l'aïllament

**Verify**:
```bash
md5 data/refresh_history.json && python -m pytest tests/test_api.py -q && python -m pytest tests/test_api.py -q && md5 data/refresh_history.json
```
→ hash idèntic abans i després de dues execucions.

Commit: `fix(tests): aïllar test_api de refresh_history.json real`

### Step 3: Netejar les entrades contaminades del fitxer real

Executa aquest script una sola vegada (des de `backend/`). No importa `app`
expressament (importar-lo arrencaria l'APScheduler); duplica la lògica mínima
de diff:

```bash
python - <<'EOF'
import json

PATH = "data/refresh_history.json"
MOCK_BY_GRADO = {"A": 20, "B": 20, "C": 20, "D": 20, "E": 20}

def compute_changes(curr, prev):
    """Rèplica mínima de app._compute_changes (mateixa semàntica)."""
    prev_families = set(prev.get("families") or [])
    curr_families = set(curr.get("families") or [])
    prev_bg = prev.get("by_grado") or {}
    curr_bg = curr.get("by_grado") or {}
    grado_deltas = {
        g: (curr_bg.get(g) or 0) - (prev_bg.get(g) or 0)
        for g in sorted(set(curr_bg) | set(prev_bg))
        if (curr_bg.get(g) or 0) != (prev_bg.get(g) or 0)
    }
    prev_d = set(prev.get("denominacions") or [])
    curr_d = set(curr.get("denominacions") or [])
    new_d, rm_d = sorted(curr_d - prev_d), sorted(prev_d - curr_d)
    new_bg, rm_bg = {}, {}
    cdbg = curr.get("denominacions_by_grado") or {}
    pdbg = prev.get("denominacions_by_grado") or {}
    for g in sorted(set(cdbg) | set(pdbg)):
        a = sorted(set(cdbg.get(g) or []) - set(pdbg.get(g) or []))
        gone = sorted(set(pdbg.get(g) or []) - set(cdbg.get(g) or []))
        if a: new_bg[g] = a
        if gone: rm_bg[g] = gone
    nf, rf = sorted(curr_families - prev_families), sorted(prev_families - curr_families)
    return {
        "new_families": nf, "removed_families": rf,
        "grado_deltas": grado_deltas,
        "total_delta": (curr.get("total") or 0) - (prev.get("total") or 0),
        "new_denominacions": new_d, "removed_denominacions": rm_d,
        "new_by_grado": new_bg, "removed_by_grado": rm_bg,
        "has_changes": bool(nf or rf or grado_deltas or new_d or rm_d),
    }

with open(PATH, encoding="utf-8") as f:
    history = json.load(f)

before = len(history)
clean = [e for e in history
         if not (e.get("total") == 100 and e.get("by_grado") == MOCK_BY_GRADO)]
print(f"Entrades: {before} -> {len(clean)} (eliminades {before - len(clean)})")

# Recalcular 'changes' de cada entrada contra la seva nova anterior
# (history[0] és la més recent; l'anterior és history[i+1]).
for i, e in enumerate(clean):
    if i + 1 < len(clean):
        e["changes"] = compute_changes(e, clean[i + 1])
    else:
        e["changes"] = None

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(clean, f, ensure_ascii=False)
print("Fet.")
EOF
```

**Verify**:
```bash
python -c "
import json
h = json.load(open('data/refresh_history.json'))
assert not any(e.get('total') == 100 for e in h), 'Encara hi ha entrades mock!'
print('OK —', len(h), 'entrades netes')
"
```
→ `OK — N entrades netes` (N ≥ 1, sense cap entrada amb total=100).

Commit: `fix(data): eliminar entrades d'historial contaminades per tests`

## Test plan

No s'escriuen tests nous més enllà de la fixture: la fixture mateixa és la
protecció, i la verificació és el hash md5 invariant del Step 2.

## Done criteria

Tots han de complir-se:

- [ ] `cd backend && python -m pytest tests/test_api.py -q` → 9 passed
- [ ] El md5 de `backend/data/refresh_history.json` és idèntic abans i després d'executar `pytest tests/test_api.py` dues vegades
- [ ] `python -c "import json; h=json.load(open('backend/data/refresh_history.json')); assert not any(e.get('total')==100 for e in h)"` surt net
- [ ] `git status` no mostra modificat cap fitxer fora de l'in-scope
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- `test_api.py` no conté la fixture `reset_refresh_state` a les línies 29–46
  ni el test `test_refresh_started` (el codi ha derivat).
- Després del Step 1 el md5 del fitxer real canvia en executar pytest
  (vol dir que hi ha una altra via d'escriptura no identificada).
- L'script del Step 3 elimina TOTES les entrades (l'historial real quedaria
  buit — revisa el criteri abans d'escriure).

## Maintenance notes

- **Efecte col·lateral conegut, deliberadament fora d'abast**: importar
  `app` als tests arrenca un `BackgroundScheduler` real
  (`app.py:62 → scheduler_service.init_scheduler()`). És innocu (config
  per defecte `enabled: false`) però seria més net protegir-ho amb una
  variable d'entorn de test. Considerar-ho quan s'executi el pla 005.
- Si al **servidor de producció** també s'han executat tests alguna vegada,
  el `refresh_history.json` del VPS pot estar contaminat igualment: cal
  executar-hi el mateix script del Step 3 (vegeu `plans/instructions.md`).
- Qualsevol test futur que toqui `/api/admin/refresh` queda cobert per la
  fixture autouse; si es crea un altre fitxer de tests que importi `app`,
  cal replicar-hi la fixture (o moure-la a `conftest.py` amb compte de no
  importar `app` per a tests que no el necessiten).
