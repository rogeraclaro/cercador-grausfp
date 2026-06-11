# Plan 009: Escapar les dades scrapejades abans d'injectar-les a innerHTML (historial.html)

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- frontend/historial.html`
> Si les línies citades a "Current state" no coincideixen, localitza les
> interpolacions `${d}` amb `grep -n 'map(d=>' frontend/historial.html` i
> adapta els números de línia; si l'estructura ha canviat de fons, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: cap
- **Category**: security
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

`historial.html` construeix la taula amb template literals injectats via
`innerHTML`, interpolant **denominacions scrapejades de todofp.es sense
escapar**. Si la font (o un MITM/compromís de la font) inclogués mai
`<script>` o atributs HTML en una denominació, s'executaria al navegador de
tots els visitants de l'historial (XSS emmagatzemat). La probabilitat és
baixa (font governamental), però el cost de l'escapat és trivial i és la
pràctica correcta per a qualsevol dada de tercers. Per contrast,
`index.html` ja és segur (usa `x-text` d'Alpine, que escapa).

## Current state

- `frontend/historial.html` — funció `load()`. Les 4 interpolacions
  vulnerables, totes amb el patró `.map(d=>...)` on `d` és una denominació
  scrapejada:
  - Línia 295: `${added.map(d=>`<li class="new">+ ${d}</li>`).join('')}`
  - Línia 296: `${removed.map(d=>`<li class="gone">− ${d}</li>`).join('')}`
  - Línia 308: idèntica a la 295 (branca per-grado)
  - Línia 309: idèntica a la 296 (branca per-grado)
- La resta d'interpolacions del fitxer (`${rowId}`, `${g}`, `${d}` numèric
  de deltas, `${entry.total}`, dates...) són valors generats pel backend
  (números, lletres de grado A–E, timestamps) — no calen canvis.
- El fitxer no té cap funció d'escapat actualment.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/`) | Esperat |
|---|---|---|
| Localitzar interpolacions | `grep -n 'map(d=>' frontend/historial.html` | 4 línies |
| Verificar el fix | `grep -c 'esc(d)' frontend/historial.html` | 4 |

## Scope

**In scope**: `frontend/historial.html` (només la funció `esc` nova i les 4
interpolacions).

**Out of scope**:
- `frontend/index.html` (ja segur via `x-text`).
- `frontend/admin.html` — té `innerHTML` amb missatges interns
  (`setStatus`, línia 263), però el contingut prové de l'API pròpia, no de
  dades scrapejades; deliberadament fora d'abast (vegeu Maintenance notes).
- Qualsevol canvi visual o d'estructura de la taula.

## Git workflow

- Un commit a `master`: `fix(security): escapar denominacions scrapejades a historial.html`
- NO push sense instrucció.

## Steps

### Step 1: Afegir la funció d'escapat

A `frontend/historial.html`, dins el `<script>`, al costat de les altres
funcions helper (p. ex. just abans de `formatDate`, ~línia 230), afegeix:

```javascript
    function esc(s) {
      return String(s).replace(/[&<>"']/g, c =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }
```

### Step 2: Aplicar-la a les 4 interpolacions

A les línies 295, 296, 308 i 309, canvia `${d}` per `${esc(d)}` dins dels
`<li>`. Exemple (línia 295), abans:
```javascript
${added.map(d=>`<li class="new">+ ${d}</li>`).join('')}
```
després:
```javascript
${added.map(d=>`<li class="new">+ ${esc(d)}</li>`).join('')}
```

**Verify**: `grep -c 'esc(d)' frontend/historial.html` → `4`, i
`grep -n 'map(d=>`<li' frontend/historial.html | grep -v 'esc(d)'` → buit.

### Step 3: Test manual amb dada maliciosa

Amb el backend local engegat, comprova el renderitzat amb una entrada
adversarial sense tocar dades reals: obre la consola del navegador a
`historial.html` i executa el snippet de la funció `renderAccRows`...
Alternativa més simple i suficient: test estàtic amb Node si està
disponible, o validació visual:

1. `cd backend && python app.py`
2. Obre `http://localhost:5001`... (el frontend s'obre directament com a
   fitxer: obre `frontend/historial.html` al navegador)
3. Confirma que la taula es renderitza igual que abans (cap regressió
   visual: chips, accordions desplegables).

Si tens Node disponible, verificació mecànica de l'escapat:
```bash
node -e "
const esc = s => String(s).replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));
const out = \`<li class=\"new\">+ \${esc('<img src=x onerror=alert(1)>')}</li>\`;
if (out.includes('<img')) { console.error('FAIL'); process.exit(1); }
console.log('escapat OK:', out);
"
```
→ `escapat OK: <li class="new">+ &lt;img src=x onerror=alert(1)&gt;</li>`

## Test plan

El projecte no té infraestructura de tests frontend; la verificació és el
grep del Step 2 + la comprovació del Step 3. No s'introdueix cap framework
de test nou (fora d'abast i contra les constraints del projecte).

## Done criteria

- [ ] La funció `esc` existeix a `historial.html`
- [ ] `grep -c 'esc(d)' frontend/historial.html` → 4
- [ ] Cap `<li>` interpola `${d}` sense `esc`
- [ ] La pàgina es renderitza correctament al navegador (chips i accordions funcionen)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- Trobes més (o menys) de 4 interpolacions de denominacions — l'estructura
  ha canviat; recompta i adapta, però si apareixen interpolacions de camps
  scrapejats NOUS (p. ex. famílies renderitzades), informa perquè cal
  decidir si escapar-los també.
- El renderitzat es trenca visualment després del canvi.

## Maintenance notes

- Regla per a futur codi frontend d'aquest projecte: **tota dada que
  provingui del scraping (denominacions, famílies, observaciones) passa per
  `esc()` abans d'anar a `innerHTML`** — o es renderitza amb `textContent`/
  `x-text`.
- Deute menor conegut i deliberadament fora d'abast: `admin.html:263`
  injecta missatges d'estat via `innerHTML`; el contingut és de l'API
  pròpia (risc baix), però si mai s'hi mostren errors que continguin dades
  scrapejades, aplicar-hi el mateix patró.
