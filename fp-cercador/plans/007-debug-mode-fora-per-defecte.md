# Plan 007: Desactivar el mode debug de Flask per defecte

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- backend/app.py README.md`
> Si `app.py` ja no acaba amb `app.run(debug=True, port=5001)`, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: cap
- **Category**: security
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

`backend/app.py` acaba amb `app.run(debug=True, port=5001)`, i el README
indica com a instrucció d'arrencada `cd backend && python app.py`. Si algú
segueix el README en un servidor accessible des de fora, exposa el debugger
de Werkzeug, que permet **execució remota de codi** des del navegador. En
producció es fa servir gunicorn (que no passa per aquest bloc), però la
configuració per defecte ha de ser segura: debug només si es demana
explícitament per variable d'entorn.

## Current state

- `backend/app.py:319-320`:
  ```python
  if __name__ == "__main__":
      app.run(debug=True, port=5001)
  ```
- `README.md:11` (instrucció 4 del setup):
  `Arrenca el servidor: cd backend && python app.py`
- El frontend espera el backend al port 5001 en local
  (`frontend/index.html:565-566`: `API_BASE = ... 'http://localhost:5001'`),
  per tant el port NO es pot canviar.
- Convenció existent de config per entorn: `os.environ.get(...)` amb
  `python-dotenv` (vegeu `app.py:42-46`).

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/backend/`) | Esperat |
|---|---|---|
| Suite | `python -m pytest tests/ -q` | 0 failed |
| Arrencada sense debug | `python app.py` | banner Flask SENSE "Debug mode: on" ni "Debugger PIN" |

## Scope

**In scope**:
- `backend/app.py` (només les línies finals)
- `README.md` (la instrucció d'arrencada)

**Out de scope**:
- `deploy/` (gunicorn no usa aquest bloc).
- Qualsevol altra part d'`app.py`.

## Git workflow

- Un commit a `master`: `fix(security): debug de Flask només amb FLASK_DEBUG=1`
- NO push sense instrucció.

## Steps

### Step 1: Condicionar el debug a una variable d'entorn

A `backend/app.py`, substitueix:

```python
if __name__ == "__main__":
    app.run(debug=True, port=5001)
```

per:

```python
if __name__ == "__main__":
    # Debug NOMÉS en desenvolupament explícit: FLASK_DEBUG=1 python app.py
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
```

**Verify**: `grep -n "debug=True" backend/app.py` → cap resultat.

### Step 2: Actualitzar el README

A `README.md`, canvia el pas 4 per:

```markdown
4. Arrenca el servidor: `cd backend && python app.py`
   (per a desenvolupament amb autoreload i debugger: `FLASK_DEBUG=1 python app.py` —
   no ho facis mai en un servidor exposat)
```

**Verify**: `grep -n "FLASK_DEBUG" README.md` → 1 resultat.

### Step 3: Comprovació funcional

```bash
cd backend
timeout 5 python app.py 2>&1 | head -10
```
→ la sortida NO conté "Debugger is active" ni "Debugger PIN". Després:
```bash
timeout 5 env FLASK_DEBUG=1 python app.py 2>&1 | head -10
```
→ la sortida SÍ conté "Debugger is active" (o "Debug mode: on").

Nota: si `timeout` no existeix a macOS, fes servir
`python app.py & sleep 3; kill %1` i llegeix la sortida.

**Verify**: comportament descrit + `python -m pytest tests/ -q` → 0 failed.

## Test plan

Sense tests automatitzats nous (el bloc `__main__` no és testejable amb
pytest de manera neta); la verificació és la comprovació funcional del
Step 3.

## Done criteria

- [ ] `grep -n "debug=True" backend/app.py` → buit
- [ ] Arrencada per defecte sense debugger; amb `FLASK_DEBUG=1` amb debugger
- [ ] `README.md` documenta les dues formes
- [ ] `cd backend && python -m pytest tests/ -q` → 0 failed
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- El bloc final d'`app.py` no coincideix amb l'extracte (ha derivat).
- En arrencar `python app.py` falla per `ADMIN_TOKEN not set` — necessites
  un `backend/.env` local amb `ADMIN_TOKEN` (no en creïs cap de nou amb
  valors inventats sense avisar; comprova si ja existeix).

## Maintenance notes

- El pla 011 també toca `README.md` (documentació de producció); si es fa
  després, ha de respectar aquesta redacció.
- Revisor: confirmeu que el port es manté a 5001 (el frontend local hi
  apunta hardcoded).
