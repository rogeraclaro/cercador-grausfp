# Plan 022: API i frontend per a centres per oferta

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Context previ**: Llegeix `plans/outputs/spike-centres-per-grau.md` ABANS de
> començar. Conté el model de dades, les mides dels fitxers i l'esbós d'UI ja
> verificats. No répeteixis la investigació.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> ```
> python3 -c "import json; d=json.load(open('backend/data/centres.json')); print(len(d), 'centres')"
> python3 -c "import json; d=json.load(open('backend/data/oferta_centres.json')); print(len(d), 'claus')"
> grep -n "def get_ofertes\|/api/" backend/app.py | head -20
> grep -n "x-for\|expandible\|centres" frontend/index.html | head -20
> ```
> Si `centres.json` o `oferta_centres.json` no existeixen, executa primer
> `python3 -m backend.scrapers.centres_scraper` (~15 min). Atura't si el
> nombre de centres < 15.000 o de claus < 800.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (addició pura; cap canvi destructiu als endpoints ni al frontend existent)
- **Depends on**: 015 (spike de centres DONE), 016b (centres.json existent)
- **Category**: feature
- **Planned at**: 2026-06-14

## Why this matters

El spike 015 va generar `centres.json` (17.951 centres) i `oferta_centres.json`
(815 relacions oferta↔centres). Sense aquest pla, les dades existeixen però
l'usuari no les pot veure. Aquest pla tanca el cicle: afegeix l'endpoint Flask
i el component Alpine.js a la fila expandible, permetent veure quins centres
ofereixen cada títol i accedir directament al web del centre.

## Current state (fets verificats)

- `backend/data/centres.json` — 17.951 registres, camps: `id`, `nombre`,
  `localitat`, `cp`, `provincia`, `ccaa`, `direccio`, `telefon`, `email`,
  `tipo`, `url_web` (null si no disponible), `updated_at`
- `backend/data/oferta_centres.json` — 815 claus:
  - Grado C LOE: clau = codi SEPE (`"ADGG0408"`)
  - Grado D/E: clau = id intern de l'oferta (`"12664"`)
- `backend/app.py` — patró existent per endpoints JSON: `@app.route('/api/...')`
- `frontend/index.html` — fila expandible Alpine.js ja implementada per a
  Grado C (durada, BOE, Europass). El panel expandible nou de centres s'inserirà
  al mateix patró.

## Scope

**In scope**:
- `backend/app.py` — nou endpoint `GET /api/centres?codigo=<clau>`
- `frontend/index.html` — comptador "N centres" a la fila + panel expandible
  de centres (filtre CCAA, llista paginada, link al web del centre)
- `backend/data/` — servir `centres.json` i `oferta_centres.json` via Flask
  (fitxers ja existents, només cal l'endpoint de lectura)

**Out of scope**:
- Cicle de vida (vigent/nou/historic) dels parells oferta×centre → Pla 023
- Inscripció oberta / links autonòmics → Pla 024
- Estat en temps real dels centres (escoles obertes/tancades) → futur
- Modificar `centres.json` o `oferta_centres.json` (lectures úniques)

## Steps

### Step 1 — Endpoint Flask `/api/centres`

**Fitxer**: `backend/app.py`

Afegir just després dels imports de dades existents:

```python
_CENTRES_PATH = os.path.join(_DATA_DIR, 'centres.json')
_OFERTA_CENTRES_PATH = os.path.join(_DATA_DIR, 'oferta_centres.json')
_centres_index: dict | None = None      # {id: centre_dict}
_oferta_centres: dict | None = None     # {clau: [id, ...]}

def _load_centres_data():
    global _centres_index, _oferta_centres
    if _centres_index is None:
        with open(_CENTRES_PATH, encoding='utf-8') as f:
            centres_list = json.load(f)
        _centres_index = {c['id']: c for c in centres_list}
    if _oferta_centres is None:
        with open(_OFERTA_CENTRES_PATH, encoding='utf-8') as f:
            _oferta_centres = json.load(f)
```

Endpoint (lazy-load per no bloquejar l'arrencada si els fitxers no existeixen):

```python
@app.route('/api/centres')
def get_centres():
    """
    GET /api/centres?codigo=ADGG0408
    GET /api/centres?id=12664          (per a Grado D/E)
    Retorna JSON array de centres per a l'oferta indicada.
    """
    try:
        _load_centres_data()
    except FileNotFoundError:
        return jsonify({'error': 'centres.json no disponible'}), 503

    clau = request.args.get('codigo') or request.args.get('id')
    if not clau:
        return jsonify({'error': 'cal el paràmetre codigo o id'}), 400

    ids = _oferta_centres.get(clau, [])
    centres = [_centres_index[i] for i in ids if i in _centres_index]
    return jsonify(centres)
```

**Verificació**:
```bash
curl "http://localhost:5001/api/centres?codigo=ADGG0408" | python3 -m json.tool | head -30
# Ha de retornar array de centres amb nom, adreça, etc.
curl "http://localhost:5001/api/centres?id=12664" | python3 -m json.tool | head -10
# Ha de retornar 92 centres per al D de "Instalaciones Deportivas"
```

### Step 2 — Comptador de centres a la fila de cerca

**Fitxer**: `frontend/index.html`

Afegir el comptador de centres a la fila principal (a la zona on ja es mostren
família, nivell i pla). Buscar el bloc que renderitza les pills/badges de cada
fila i afegir-hi:

```html
<template x-if="centres_count(row) > 0">
  <span class="badge badge-centres"
        @click.stop="toggleCentres(row)"
        x-text="centres_count(row) + ' centres'">
  </span>
</template>
```

La funció `centres_count(row)` i `toggleCentres(row)` s'afegiran a l'objecte
Alpine.js al Step 3.

### Step 3 — Lògica Alpine.js per a la càrrega de centres

**Fitxer**: `frontend/index.html` — dins l'objecte `data()` de l'app Alpine.

Afegir:
```javascript
// Centres per oferta (on-demand)
centresVisible: {},   // {row_id: bool}
centresData: {},      // {row_id: [{...}, ...]}
centresCCAA: {},      // {row_id: 'Totes'}
centresLoading: {},   // {row_id: bool}

centres_count(row) {
    // Retorna el nombre de centres si ja s'han carregat, o 0
    const data = this.centresData[row.id];
    return data ? data.length : 0;
},

async toggleCentres(row) {
    if (this.centresVisible[row.id]) {
        this.centresVisible[row.id] = false;
        return;
    }
    this.centresVisible[row.id] = true;
    if (this.centresData[row.id]) return; // ja carregat
    this.centresLoading[row.id] = true;
    try {
        const clau = row.grado === 'C' && row.plan_antiguo
            ? row.codigo
            : row.id;
        const param = row.grado === 'C' && row.plan_antiguo
            ? `codigo=${clau}`
            : `id=${clau}`;
        const resp = await fetch(`/api/centres?${param}`);
        this.centresData[row.id] = await resp.json();
        this.centresCCAA[row.id] = 'Totes';
    } finally {
        this.centresLoading[row.id] = false;
    }
},

centresFiltrats(row) {
    const data = this.centresData[row.id] || [];
    const ccaa = this.centresCCAA[row.id];
    if (!ccaa || ccaa === 'Totes') return data;
    return data.filter(c => c.ccaa === ccaa);
},

ccaasDisponibles(row) {
    const data = this.centresData[row.id] || [];
    return ['Totes', ...new Set(data.map(c => c.ccaa).filter(Boolean)).values()].sort();
},
```

**Nota**: inicialitzar `centresVisible`, `centresData`, `centresCCAA`,
`centresLoading` amb `{}` dins `data()`.

### Step 4 — Panel expandible de centres al template HTML

**Fitxer**: `frontend/index.html`

Afegir una fila addicional al `<tbody>` just després de la fila expandible
existent (o integrar dins el mateix panel si l'estructura ho permet). El panel
ha de ser visible quan `centresVisible[row.id]`:

```html
<template x-if="centresVisible[row.id]">
  <tr class="centres-panel">
    <td colspan="99">
      <div class="centres-container">

        <!-- Capçalera amb comptador i filtre CCAA -->
        <div class="centres-header">
          <span x-text="(centresData[row.id] || []).length + ' centres'"></span>
          <select x-model="centresCCAA[row.id]">
            <template x-for="ccaa in ccaasDisponibles(row)" :key="ccaa">
              <option :value="ccaa" x-text="ccaa"></option>
            </template>
          </select>
          <button @click="centresVisible[row.id] = false">✕</button>
        </div>

        <!-- Loading spinner -->
        <div x-show="centresLoading[row.id]" class="centres-loading">
          Carregant centres…
        </div>

        <!-- Llista de centres (primers 50, amb "Mostrar tots") -->
        <div x-show="!centresLoading[row.id]">
          <template x-for="centre in centresFiltrats(row).slice(0, 50)" :key="centre.id">
            <div class="centre-item">
              <div class="centre-nom">
                <template x-if="centre.url_web">
                  <a :href="centre.url_web" target="_blank" rel="noopener"
                     x-text="centre.nombre"></a>
                </template>
                <template x-if="!centre.url_web">
                  <span x-text="centre.nombre"></span>
                </template>
              </div>
              <div class="centre-meta">
                <span x-text="centre.direccio || ''"></span>
                <span x-show="centre.direccio && centre.localitat">, </span>
                <span x-text="centre.localitat || ''"></span>
                <span x-show="centre.telefon"> · 📞 <span x-text="centre.telefon"></span></span>
              </div>
            </div>
          </template>

          <!-- Avís si n'hi ha més de 50 -->
          <template x-if="centresFiltrats(row).length > 50">
            <p class="centres-more"
               x-text="'... i ' + (centresFiltrats(row).length - 50) + ' centres més'">
            </p>
          </template>

          <!-- Missatge si 0 centres -->
          <template x-if="centresFiltrats(row).length === 0 && !centresLoading[row.id]">
            <p class="centres-buit">Cap centre trobat per a aquesta comunitat.</p>
          </template>
        </div>

      </div>
    </td>
  </tr>
</template>
```

### Step 5 — CSS per al panel de centres

**Fitxer**: `frontend/index.html` (bloc `<style>` existent)

Afegir al final del bloc de styles:

```css
/* ── Centres per oferta ─────────────────────────── */
.badge-centres {
  cursor: pointer;
  background: #e8f4fd;
  color: #1a73e8;
  border: 1px solid #1a73e8;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 6px;
  white-space: nowrap;
}
.badge-centres:hover { background: #1a73e8; color: #fff; }

.centres-panel td { padding: 0 !important; }
.centres-container {
  background: #f8f9fa;
  border-top: 2px solid #1a73e8;
  padding: 12px 16px;
  max-height: 400px;
  overflow-y: auto;
}
.centres-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  font-weight: 600;
  font-size: 0.9rem;
}
.centres-header select {
  font-size: 0.85rem;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #ccc;
}
.centres-header button {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: #666;
}
.centres-loading { color: #666; font-style: italic; padding: 8px 0; }

.centre-item {
  padding: 6px 0;
  border-bottom: 1px solid #e9ecef;
}
.centre-item:last-child { border-bottom: none; }
.centre-nom { font-weight: 500; font-size: 0.88rem; }
.centre-nom a { color: #1a73e8; text-decoration: none; }
.centre-nom a:hover { text-decoration: underline; }
.centre-meta { font-size: 0.78rem; color: #666; margin-top: 2px; }

.centres-more { color: #888; font-size: 0.82rem; margin-top: 8px; }
.centres-buit { color: #888; font-style: italic; font-size: 0.85rem; }
```

### Step 6 — Precarregar recompte de centres (opcional però recomanat)

Per mostrar el badge "N centres" sense una petició per fila, es pot servir un
índex lleuger de comptadors:

**Opció A (recomanada)**: endpoint `/api/centres/count` que retorna
`{clau: count}` per a totes les ofertes. El frontend el carrega un cop a
l'inici (3.3 MB → gzip ~400 KB).

```python
@app.route('/api/centres/count')
def get_centres_count():
    try:
        _load_centres_data()
    except FileNotFoundError:
        return jsonify({}), 200
    return jsonify({k: len(v) for k, v in _oferta_centres.items()})
```

Al frontend, afegir `centresCount: {}` a `data()` i carregar-lo a `init()`:
```javascript
fetch('/api/centres/count')
    .then(r => r.json())
    .then(d => { this.centresCount = d; });
```

Actualitzar `centres_count(row)`:
```javascript
centres_count(row) {
    if (this.centresData[row.id]) return this.centresData[row.id].length;
    const clau = row.grado === 'C' && row.plan_antiguo ? row.codigo : String(row.id);
    return this.centresCount[clau] || 0;
},
```

**Opció B**: no precarregar; el badge no apareix fins que l'usuari expandeix
la fila. Més simple, menys UX.

Implementar l'Opció A.

### Step 7 — Verificació manual

```bash
# Servidor local
cd fp-cercador && python3 -m flask --app backend.app run --port 5001

# Test API
curl "http://localhost:5001/api/centres?codigo=ADGG0408" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(f'{len(d)} centres')
print('Primer:', d[0]['nombre'], '|', d[0]['localitat'])
"

curl "http://localhost:5001/api/centres/count" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(f'{len(d)} claus')
print('ADGG0408:', d.get('ADGG0408'))
"

# Verificació UI (obre el navegador)
open http://localhost:5001
# Cerca "gestión administrativa" → hauria d'aparèixer el badge "4232 centres"
# Clic al badge → s'ha d'obrir el panel amb llista de centres
# Filtra per CCAA "PAÍS VASCO" → ha de filtrar la llista
# Comprova que els centres amb url_web mostren un link clicable
```

## Done criteria

- [ ] `GET /api/centres?codigo=ADGG0408` retorna 4.232 centres en JSON
- [ ] `GET /api/centres?id=12664` retorna 92 centres
- [ ] `GET /api/centres/count` retorna dict amb 815 claus
- [ ] Badge "N centres" visible a cada fila (excepte si N=0)
- [ ] Clic al badge obre el panel de centres (fetch on-demand)
- [ ] Filtre de CCAA funciona sense recàrrega
- [ ] Centres amb `url_web` mostren link clicable
- [ ] Centres sense `url_web` mostren nom sense link
- [ ] Panel tanca amb el botó ✕
- [ ] Cap error de consola JS a l'obrir el panel
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- `centres.json` no existeix → executar `centres_scraper.py` primer
- L'endpoint retorna `503` → els fitxers de dades no s'han generat
- El filtre de CCAA buida tots els resultats per defecte → revisar la lògica
  de `centresCCAA` (ha d'inicialitzar a `'Totes'`)
- El badge apareix a files Grado A/B → els Grado A/B no tenen clau a
  `oferta_centres.json`; `centres_count` ha de retornar 0 per a ells
