# Plan 008: Eliminar les 6 variants mortes del frontend

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- frontend/`
> Si `frontend/index.html` ha canviat substancialment, re-verifica que cap
> fitxer nou referenciï les variants abans de continuar.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: cap
- **Category**: tech-debt
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

El directori `frontend/` conté 6 variants històriques de la pàgina principal
(~3.500 línies duplicades): iteracions de disseny abandonades. El propietari
ha confirmat explícitament que **`index.html` és l'única variant viva**.
A més de soroll per al manteniment, el vhost nginx serveix `frontend/` com a
root estàtic, així que totes les variants velles són públicament accessibles
(p. ex. `https://domini/old_index.html`), amb codi i crides API antigues.

## Current state

Contingut de `frontend/` (rutes relatives a `fp-cercador/`):

| Fitxer | Estat |
|---|---|
| `frontend/index.html` | **VIU** (confirmat pel propietari) — cercador principal |
| `frontend/admin.html` | VIU — panell admin |
| `frontend/historial.html` | VIU — historial públic |
| `frontend/old_index.html` | mort — eliminar |
| `frontend/bo_index.html` | mort — eliminar |
| `frontend/index_blau.html` | mort — eliminar |
| `frontend/index_roger.html` | mort — eliminar |
| `frontend/index_redisseny.html` | mort — eliminar |
| `frontend/_index_redisseny.html` | mort — eliminar |

Verificat durant l'auditoria (commit `5dc92a1`): cap fitxer del repo
(frontend, deploy, backend) referencia cap de les 6 variants mortes.
`deploy/nginx-cloudpanel.conf` té `index index.html;`.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/`) | Esperat |
|---|---|---|
| Verificar zero referències | `grep -rn "old_index\|bo_index\|index_blau\|index_roger\|index_redisseny" frontend backend ../deploy 2>/dev/null` | buit |
| Eliminar | `git rm frontend/old_index.html frontend/bo_index.html frontend/index_blau.html frontend/index_roger.html frontend/index_redisseny.html frontend/_index_redisseny.html` | 6 fitxers eliminats |

## Scope

**In scope**: els 6 fitxers morts de la taula (eliminar).

**Out of scope**:
- `frontend/index.html`, `frontend/admin.html`, `frontend/historial.html` —
  NO els toquis ni una línia.
- Qualsevol "neteja" addicional del frontend.

## Git workflow

- Un commit a `master`: `chore(frontend): eliminar 6 variants de disseny mortes`
- NO push sense instrucció.

## Steps

### Step 1: Re-verificar que res no les referencia

```bash
grep -rn "old_index\|bo_index\|index_blau\|index_roger\|index_redisseny" frontend backend ../deploy 2>/dev/null
```
→ ha de ser buit. Si surt qualsevol resultat, STOP.

### Step 2: Eliminar les variants

```bash
git rm frontend/old_index.html frontend/bo_index.html frontend/index_blau.html \
       frontend/index_roger.html frontend/index_redisseny.html frontend/_index_redisseny.html
```

**Verify**: `ls frontend/` → exactament 3 fitxers: `admin.html`,
`historial.html`, `index.html`.

### Step 3: Smoke test de l'index viu

Obre `frontend/index.html` al navegador amb el backend local engegat
(`cd backend && python app.py`) i confirma que el cercador carrega
registres. Alternativa sense navegador:
```bash
python -c "
html = open('frontend/index.html').read()
assert 'cercador' in html and '/api/ofertes' in html
print('index.html intacte OK')
"
```

## Test plan

Cap test automatitzat (només esborrat de fitxers estàtics no referenciats).
La verificació és el grep del Step 1 i l'smoke test del Step 3.

## Done criteria

- [ ] `ls frontend/` → només `admin.html`, `historial.html`, `index.html`
- [ ] El grep del Step 1 és buit
- [ ] `git status` mostra només les 6 eliminacions
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- El grep del Step 1 retorna qualsevol referència a una variant.
- `frontend/` conté fitxers que no apareixen a la taula de "Current state"
  (n'han aparegut de nous des de l'auditoria — pregunta abans d'esborrar).

## Maintenance notes

- Si en el futur es vol experimentar amb redissenys, fer-ho en una branca
  git, no amb fitxers paral·lels al directori servit públicament.
- En desplegar, els fitxers vells desapareixeran del VPS amb el `git pull`
  (si hi queden còpies no trackejades, esborrar-les manualment).
