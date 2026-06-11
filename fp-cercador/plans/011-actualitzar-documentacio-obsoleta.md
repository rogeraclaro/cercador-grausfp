# Plan 011: Actualitzar la documentació obsoleta (cookies, UUID, endpoint inexistent)

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de l'arrel del repo git)**:
> `git diff --stat 5dc92a1..HEAD -- deploy/DEPLOY.md fp-cercador/backend/scrapers/pipeline.py fp-cercador/README.md`
> Els plans 003/004/006/007/010 poden haver tocat aquests fitxers — és
> esperat; el que importa és que els fragments obsolets citats a "Current
> state" encara existeixin (verifica amb els greps de cada step).

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/007-debug-mode-fora-per-defecte.md (edita README.md abans), idealment després de 003 i 004 (toquen pipeline.py i DEPLOY.md)
- **Category**: docs
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

Des del refactor "auto-cookies" (commit `3eb9413`), el scraper del buscador
obté les cookies automàticament amb un GET de bootstrap: ja no calen ni
`BUSCADOR_COOKIES` ni `BUSCADOR_UUID` ni captcha. Però la documentació
encara descriu el món antic: `DEPLOY.md` mana configurar `BUSCADOR_COOKIES`
al `.env` i té una secció sencera de "Renovar les cookies", i el docstring
de `pipeline.py` cita `BUSCADOR_UUID` i un endpoint
`/api/admin/update-cookies` que **no existeix** a `app.py`. Documentació
activa incorrecta és pitjor que documentació absent: el proper desplegament
seguirà passos inútils o fallarà buscant com obtenir cookies.

## Current state

- `deploy/DEPLOY.md` (arrel del repo git):
  - Secció 3 ("Configurar variables d'entorn") mostra un `.env` amb la
    línia `BUSCADOR_COOKIES=JSESSIONID=<valor>; __Host-todofp.es=<valor>`
    i remet a la secció "Renovar les cookies del buscador" del final.
  - Existeix aquesta secció final sencera sobre renovar cookies
    (localitza-la amb `grep -n -i "cookie" deploy/DEPLOY.md`).
- `fp-cercador/backend/scrapers/pipeline.py`:
  - Docstring, línies 13–14:
    ```
    Grados A, B, C: API REST del Buscador de Graus FP (buscador_scraper.py).
      Requereix BUSCADOR_UUID a .env (obtingut resolent el reCAPTCHA del buscador).
    ```
    La segona línia és falsa (ja no cal cap UUID).
  - Comentari a les línies 100–101 (dins `run()`):
    ```python
    # D-01 (Phase 6): Recarrega .env perquè un BUSCADOR_COOKIES actualitzat
    # via /api/admin/update-cookies prengui efecte sense reiniciar el servei.
    load_dotenv(override=True)
    ```
    L'endpoint `/api/admin/update-cookies` no existeix a `app.py` i
    `BUSCADOR_COOKIES` ja no es llegeix enlloc.
- `fp-cercador/backend/.env.example` — correcte (no menciona cookies); no
  cal tocar-lo.
- Realitat del codi vigent: `buscador_scraper.py` docstring (línies 1–24)
  descriu el flow auto-cookies correcte — fes-lo servir com a font de
  veritat per redactar.
- `fp-cercador/README.md` — després del pla 007 documenta l'arrencada; li
  falta una referència al desplegament.

## Commands you will need

| Propòsit | Comanda (des de l'arrel del repo git) | Esperat |
|---|---|---|
| Restes de cookies | `grep -rn -i "BUSCADOR_COOKIES\|BUSCADOR_UUID\|update-cookies" deploy fp-cercador --include="*.md" --include="*.py" \| grep -v __pycache__ \| grep -v plans/` | buit en acabar |
| Suite | `cd fp-cercador/backend && python -m pytest tests/ -q` | 0 failed |

## Scope

**In scope**:
- `deploy/DEPLOY.md`
- `fp-cercador/backend/scrapers/pipeline.py` (NOMÉS docstring i comentaris — cap línia de codi)
- `fp-cercador/README.md` (una línia de referència a DEPLOY.md)

**Out of scope**:
- El comportament de `load_dotenv(override=True)` a `pipeline.run()` — el
  comentari es corregeix, la crida ES MANTÉ (vegeu Maintenance notes).
- `buscador_scraper.py` (ja és correcte).
- `.env.example`.

## Git workflow

- Un commit a `master`: `docs: eliminar referències obsoletes a cookies/UUID del buscador`
- NO push sense instrucció.

## Steps

### Step 1: Netejar DEPLOY.md

1. A la secció 3, deixa el `.env` només amb `ADMIN_TOKEN=<token-segur-aleatori>`
   i elimina la línia de `BUSCADOR_COOKIES` i la frase que remet a la
   secció de renovació.
2. Elimina la secció sencera "Renovar les cookies del buscador" (final del
   document). Substitueix-la per una nota breu:
   ```markdown
   ## Sobre les cookies del buscador

   Des del refactor auto-cookies (maig 2026), el scraper obté les cookies
   automàticament amb un GET de bootstrap a
   `https://www.todofp.es/buscadorgradosfp/buscador` a cada refresh.
   No cal configurar res. Si el refresh falla amb "Bootstrap no ha retornat
   JSESSIONID", inspecciona `backend/data/last_failure.html` per veure la
   resposta del servidor.
   ```

**Verify**: `grep -n -i "BUSCADOR_COOKIES" deploy/DEPLOY.md` → buit.

### Step 2: Corregir el docstring i el comentari de pipeline.py

1. Docstring (línies 13–14), substitueix per:
   ```
   Grados A, B, C: API REST del Buscador de Graus FP (buscador_scraper.py).
     Cookies obtingudes automàticament via bootstrap GET (sense captcha ni config).
   ```
2. Comentari de `load_dotenv` (línies 100–101), substitueix per:
   ```python
    # Recarrega .env a cada run perquè canvis de configuració (p. ex. URLs
    # dels Grados D/E) prenguin efecte sense reiniciar el servei.
   ```

**Verify**:
`grep -n "BUSCADOR_UUID\|update-cookies" fp-cercador/backend/scrapers/pipeline.py` → buit, i
`cd fp-cercador/backend && python -m pytest tests/ -q` → 0 failed (no s'ha
tocat cap línia de codi).

### Step 3: Referència de producció al README

A `fp-cercador/README.md`, afegeix al final:

```markdown
## Desplegament

Per al desplegament en producció (VPS amb CloudPanel, gunicorn i nginx),
vegeu `../deploy/DEPLOY.md`.
```

**Verify**: `grep -n "DEPLOY.md" fp-cercador/README.md` → 1 resultat.

### Step 4: Escombrada final

**Verify**:
```bash
grep -rn -i "BUSCADOR_COOKIES\|BUSCADOR_UUID\|update-cookies" deploy fp-cercador --include="*.md" --include="*.py" | grep -v __pycache__ | grep -v plans/
```
→ buit.

## Test plan

Cap test (només docs i comentaris). La garantia que no s'ha tocat codi és
la suite verda del Step 2.

## Done criteria

- [ ] L'escombrada del Step 4 és buida
- [ ] `cd fp-cercador/backend && python -m pytest tests/ -q` → 0 failed
- [ ] `git diff` mostra NOMÉS canvis a línies de comentari/markdown (cap línia de codi Python efectiva)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- Trobes que `BUSCADOR_COOKIES` o `BUSCADOR_UUID` ES LLEGEIXEN en algun
  fitxer `.py` (`os.getenv`/`os.environ`) — la suposició "ja no s'usen" seria
  falsa; informa abans de tocar res.
- `DEPLOY.md` ha estat reescrit de dalt a baix i les seccions citades no
  existeixen.

## Maintenance notes

- `load_dotenv(override=True)` a `pipeline.run()` es conserva: encara és
  útil per recarregar URLs dels Grados D/E sense reiniciar. Si mai es
  decideix que no cal, treure-la és un canvi de comportament que mereix el
  seu propi commit i test, no un efecte col·lateral d'un canvi de docs.
- Quan canviï el mecanisme d'scraping una altra vegada, actualitzar DEPLOY.md
  i el docstring de pipeline.py EN EL MATEIX COMMIT que el codi — aquesta
  deriva és exactament el que aquest pla repara.
