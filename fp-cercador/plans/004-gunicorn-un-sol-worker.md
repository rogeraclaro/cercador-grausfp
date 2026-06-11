# Plan 004: Passar gunicorn a 1 worker amb threads (scheduler i estat són per-procés)

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de l'ARREL DEL REPO GIT, que és el
> directori PARE de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- deploy/fp-cercador.service deploy/DEPLOY.md`
> Si el `.service` ja no té `--workers 2`, STOP (potser ja s'ha arreglat).

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: cap
- **Category**: bug (arquitectura de desplegament)
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

El servei systemd arrenca gunicorn amb `--workers 2`. El backend, però,
manté TOT l'estat en memòria del procés:

1. `app.py:62` crida `scheduler_service.init_scheduler()` en temps d'import →
   **cada worker arrenca el seu propi APScheduler** i el refresh programat
   s'executa 2 vegades simultàniament (doble scraping a todofp.es i carrera
   en l'escriptura de l'historial, que és read-modify-write no atòmic entre
   processos).
2. `refresh_state._lock` (`backend/refresh_state.py:16`) és un
   `threading.Lock` per-procés → el guard 409 "Refresh already running" NO
   protegeix si dues peticions cauen en workers diferents.
3. `/api/refresh-status` retorna l'estat del worker que atengui la petició →
   el polling del panell admin pot veure "idle" mentre l'altre worker està
   "running" (comportament erràtic visible a l'usuari).

Amb el trànsit esperat d'aquesta app, 1 worker amb threads és suficient i
fa que el model d'estat en memòria torni a ser correcte.

## Current state

Fitxers rellevants. ATENCIÓ A LES RUTES: l'arrel del repo git és el directori
PARE de `fp-cercador/` (conté `deploy/`, `fp-cercador/`, `CLAUDE.md`...).

- `deploy/fp-cercador.service` (línies 11–17):
  ```ini
  ExecStart=/home/masellas-grausfp/htdocs/grausfp.masellas.info/venv/bin/gunicorn \
      --workers 2 \
      --bind 127.0.0.1:8033 \
      --timeout 120 \
      --access-logfile /var/log/fp-cercador/access.log \
      --error-logfile /var/log/fp-cercador/error.log \
      app:app
  ```
- `deploy/DEPLOY.md` — guia de desplegament; secció 5 instal·la el servei.
- `fp-cercador/backend/app.py:62` — `scheduler_service.init_scheduler()`
  s'executa en importar el mòdul (per tant, un cop per worker).
- `fp-cercador/backend/refresh_state.py:16` — `_lock = threading.Lock()`.

## Commands you will need

| Propòsit | Comanda | Esperat |
|---|---|---|
| Validar sintaxi servei | inspecció visual (no hi ha systemd a macOS) | — |
| Provar gunicorn localment (opcional) | `cd fp-cercador/backend && gunicorn --workers 1 --threads 4 --bind 127.0.0.1:8044 app:app` + `curl -s http://127.0.0.1:8044/health` | `{"status":"ok"}` |

## Scope

**In scope**:
- `deploy/fp-cercador.service`
- `deploy/DEPLOY.md` (afegir una nota breu)

**Out of scope**:
- Qualsevol canvi de codi a `backend/` — NO converteixis el scheduler en
  servei extern ni canviïs `refresh_state`; això seria una alternativa més
  cara explícitament descartada (vegeu Maintenance notes).
- `deploy/nginx-cloudpanel.conf` (el toca el pla 006).

## Git workflow

- Un commit a `master`: `fix(deploy): gunicorn amb 1 worker + threads — scheduler i estat són per-procés`
- NO push sense instrucció.

## Steps

### Step 1: Canviar la línia de workers del servei

A `deploy/fp-cercador.service`, substitueix `--workers 2 \` per:

```ini
    --workers 1 \
    --threads 4 \
```

Deixa la resta de flags intactes. Resultat esperat del bloc ExecStart:
gunicorn amb `--workers 1 --threads 4 --bind 127.0.0.1:8033 --timeout 120`.

**Verify**: `grep -n "workers\|threads" deploy/fp-cercador.service` →
mostra `--workers 1` i `--threads 4`, i cap `--workers 2`.

### Step 2: Documentar el perquè a DEPLOY.md

A `deploy/DEPLOY.md`, just després del bloc d'instal·lació del servei
(secció 5), afegeix:

```markdown
> **Important — no apugis `--workers`**: el backend manté l'scheduler
> (APScheduler), el lock de refresh i l'estat de `/api/refresh-status` en
> memòria del procés. Amb més d'un worker, el refresh programat s'executaria
> duplicat i l'estat seria inconsistent entre workers. Per absorbir més
> trànsit, apuja `--threads`, no `--workers`.
```

**Verify**: `grep -n "no apugis" deploy/DEPLOY.md` → 1 resultat.

### Step 3 (opcional, si gunicorn està instal·lat localment): smoke test

```bash
cd fp-cercador/backend
gunicorn --workers 1 --threads 4 --bind 127.0.0.1:8044 app:app &
sleep 2
curl -s http://127.0.0.1:8044/health
kill %1
```
→ `{"status":"ok"}`. Si gunicorn no està instal·lat localment, omet aquest
pas (la verificació real és al desplegament; vegeu `plans/instructions.md`).

## Test plan

Sense tests automatitzats: és un canvi de configuració de desplegament. La
verificació de producció (manual, per l'operador) és:
`systemctl restart fp-cercador && ps aux | grep gunicorn` → 1 master + 1
worker (2 processos gunicorn en total, no 3).

## Done criteria

- [ ] `deploy/fp-cercador.service` conté `--workers 1` i `--threads 4`, i no conté `--workers 2`
- [ ] `deploy/DEPLOY.md` conté la nota sobre workers
- [ ] `git status` net fora dels 2 fitxers in-scope
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- El `.service` ja no conté `--workers 2` (algú ho ha canviat — verifica si
  el problema ja està resolt d'una altra manera abans de tocar res).
- Trobes un segon mecanisme d'arrencada (un altre `.service`, supervisor,
  Procfile...) que també llanci gunicorn amb una config diferent.

## Maintenance notes

- **Alternativa descartada conscientment**: externalitzar el scheduler
  (systemd timer / cron que faci POST a `/api/admin/refresh`) i moure
  l'estat a disc faria el backend multi-worker-safe, però és més peces per
  a un guany que aquesta app no necessita. Si algun dia el trànsit exigeix
  més d'un worker, AQUEST és el refactor a fer — no apujar workers sense ell.
- L'aplicació del canvi al VPS requereix: copiar el `.service` actualitzat,
  `systemctl daemon-reload && systemctl restart fp-cercador` (detallat a
  `plans/instructions.md`).
- Revisor: confirmeu que ningú depèn del paral·lelisme de 2 workers per al
  rendiment — el refresh triga ~4s i va en thread de fons, no bloqueja.
