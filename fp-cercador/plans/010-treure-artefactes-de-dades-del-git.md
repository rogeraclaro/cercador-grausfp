# Plan 010: Deixar de versionar els artefactes de dades generats en runtime

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- .gitignore backend/data/`
> Si els fitxers de dades ja no estan trackejats, STOP (ja s'ha fet).

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/001-aillar-tests-de-dades-reals.md (recomanat: neteja les dades abans del darrer commit que les contingui)
- **Category**: tech-debt
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

Tres artefactes generats en runtime estan versionats al git:
`backend/data/refresh_history.json` (blob de **9,8 MB** al darrer commit,
amb dades contaminades per tests incloses), `backend/data/ofertes.json`
(3,7 MB, regenerat a cada refresh) i `backend/data/last_failure.html`
(bolcat de diagnòstic). Conseqüències: el repo s'infla a cada commit que
els toca, i al VPS un `git pull` pot entrar en conflicte amb els fitxers
que el servidor regenera contínuament. Els fitxers de runtime han de viure
fora del control de versions, com ja fa `scheduler.json` (que mai s'ha
trackejat).

## Current state

- Fitxers trackejats actualment (sortida de `git ls-files` dins
  `fp-cercador/`):
  - `backend/data/last_failure.html`
  - `backend/data/ofertes.json`
  - `backend/data/refresh_history.json`
- NO trackejats (ja són runtime-only): `backend/data/scheduler.json` (si
  existeix), `backend/data/last_snapshot.json` (creat pel pla 006).
- `fp-cercador/.gitignore` actual: cobreix `.env`, `__pycache__/`, venvs,
  `*.pdf`, IDE — però NO `backend/data/`.
- El codi crea `backend/data/` automàticament si no existeix:
  `app.py` (`os.makedirs(dir_path, exist_ok=True)` dins l'escriptura
  d'historial), `buscador_scraper._dump_failure`, i
  `scheduler_service._write_atomic`. ATENCIÓ: `pipeline._write_atomic`
  (`scrapers/pipeline.py:58-73`) NO fa makedirs — però el directori sempre
  existirà al working tree perquè `git rm --cached` no esborra res del disc.
- Flux de desplegament (`deploy/DEPLOY.md`): clonar repo → instal·lar →
  arrencar servei → llançar refresh des del panell admin. En un clone nou,
  `/api/ofertes` retorna 503 amb el missatge "Run /api/admin/refresh first"
  fins al primer refresh — comportament ja dissenyat (`app.py:179-180`).

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/`) | Esperat |
|---|---|---|
| Untrack sense esborrar | `git rm --cached backend/data/refresh_history.json backend/data/ofertes.json backend/data/last_failure.html` | 3 fitxers |
| Verificar | `git ls-files \| grep "backend/data"` | buit |

## Scope

**In scope**:
- Índex de git (untrack dels 3 fitxers — els fitxers al disc NO es toquen)
- `.gitignore` (de `fp-cercador/`)
- `deploy/DEPLOY.md` (a l'arrel del repo git — una nota)

**Out of scope**:
- Reescriure la història de git per treure el blob de 9,8 MB
  (`git filter-repo`) — descartat explícitament: el repo el comparteixen
  el portàtil i el VPS i una reescriptura forçaria re-clones; el cost
  supera el benefici. NO ho facis.
- El contingut dels fitxers de dades.
- El codi del backend.

## Git workflow

- Un commit a `master`: `chore: deixar de versionar backend/data (artefactes de runtime)`
- NO push sense instrucció.

## Steps

### Step 1: Untrack dels 3 fitxers

```bash
git rm --cached backend/data/refresh_history.json backend/data/ofertes.json backend/data/last_failure.html
```

(`--cached` és imprescindible: treu del control de versions però DEIXA els
fitxers al disc.)

**Verify**: `ls backend/data/` → els fitxers segueixen existint al disc;
`git ls-files | grep "backend/data"` → buit.

### Step 2: Ignorar el directori de dades

A `fp-cercador/.gitignore`, afegeix al final:

```gitignore
# Artefactes de runtime (ofertes.json, refresh_history.json, scheduler.json,
# last_snapshot.json, last_failure.html) — el servidor els regenera
backend/data/
```

**Verify**: `git status` → `backend/data/` no apareix com a untracked;
`git check-ignore backend/data/ofertes.json` → imprimeix la ruta (ignorat).

### Step 3: Nota a DEPLOY.md

A `deploy/DEPLOY.md` (arrel del repo git), a la secció de clonatge o just
abans del primer refresh, afegeix:

```markdown
> **Nota**: `backend/data/` no està versionat. En un desplegament nou,
> `/api/ofertes` retornarà 503 fins que llancis el primer refresh des del
> panell admin (o via `POST /api/admin/refresh`).
```

**Verify**: `grep -n "no està versionat" ../deploy/DEPLOY.md` → 1 resultat.

### Step 4: Commit i comprovació final

```bash
git add .gitignore ../deploy/DEPLOY.md
git commit -m "chore: deixar de versionar backend/data (artefactes de runtime)"
git ls-files | grep "backend/data"
```
→ buit.

## Test plan

Cap test de codi (no es toca codi). Verificació de regressió: la suite
sencera segueix verda (`cd backend && python -m pytest tests/ -q`), i el
servidor local arrenca i serveix `/api/ofertes` normalment (els fitxers
segueixen al disc).

## Done criteria

- [ ] `git ls-files | grep "backend/data"` → buit
- [ ] Els 3 fitxers segueixen físicament a `backend/data/`
- [ ] `git check-ignore backend/data/ofertes.json` els reporta ignorats
- [ ] `deploy/DEPLOY.md` conté la nota del primer refresh
- [ ] `cd backend && python -m pytest tests/ -q` → 0 failed
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- `git rm --cached` reporta que algun dels fitxers no està trackejat
  (l'estat ha derivat — verifica amb `git ls-files` què queda per fer).
- `git status` mostra altres canvis staged que no són d'aquest pla (no els
  arrosseguis al commit).

## Maintenance notes

- **Al VPS**: després del `git pull` d'aquest commit, git deixarà els
  fitxers de dades del servidor intactes (passen a untracked). No cal cap
  acció; els conflictes de pull per aquests fitxers desapareixen.
- El blob de 9,8 MB queda a la història del repo. Si algun dia el repo es
  publica o la mida molesta de debò, valorar `git filter-repo` amb
  coordinació de tots els clones — decisió conscientment ajornada.
- Si es vol "seed data" per a desenvolupament local sense fer scraping,
  l'opció neta és un fixture petit (100 registres) a `backend/tests/` o un
  `make seed`, mai re-trackejar els fitxers de producció.
