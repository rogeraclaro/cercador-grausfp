# Pla 033: [F7] Gràfics addicionals (V2 + V4) + SEO i enllaços

## Status

- **Priority**: P3
- **Effort**: S (2-3h)
- **Risk**: LOW — només afegeix contingut al fitxer existent; no trenca el primer increment
- **Depends on**: Pla 032 DONE + **almenys 4 setmanes de dades reals** a `observatory_snapshots`
- **Category**: frontend
- **Planned at**: commit `b84ffb4`, 2026-06-17

## Why this matters

El primer increment (pla 032) funciona amb 2+ punts de dades. Quan l'observatori tingui ≥4 setmanes de dades reals, valen la pena dos gràfics addicionals: V2 (evolució per grado, línies múltiples A/B/C/D/E) i V4 (altes per setmana, barres verticals). A més, aquest pla afegeix els links des d'`index.html` i `historial.html`, i refina els meta tags amb els números reals. No executar fins que hi hagi dades suficients — les línies amb 2-3 punts no aporten valor.

## Codebase context

**`frontend/observatori.html`** (post-pla 032) — estructura de seccions amb `id="chart-total"`, `id="chart-grados"`, `id="novetats-list"`.

**`/api/observatory` response** (post-pla 031):
```json
{
  "series": [{"ts": "...", "total": 12894, "A": 8730, "B": 2952, "C": 981, "D": 195, "E": 36, "n_altes": 10, ...}],
  "current": {"total": 12894, "A": 8730, ...},
  "recent_changes": [...]
}
```

**`frontend/index.html`** — patró de link al footer (verificar l'estructura real del footer per copiar el patró).

**`frontend/historial.html`** — patró de link al footer: `<a href="index.html">← Tornar al cercador</a>`

## Scope

**In scope**:
- `frontend/observatori.html` — afegir seccions V2 + V4 + SEO refinament + `<noscript>` millorat
- `frontend/index.html` — afegir link a l'observatori al footer
- `frontend/historial.html` — afegir link a l'observatori al footer

**Out of scope**: `backend/`, `vendor/` (uPlot ja vendoritzat), cap altre fitxer.

## Steps

### Step 1: Verificar que hi ha dades suficients

Abans de res: `sqlite3 backend/data/fp_cercador.db "SELECT COUNT(*), MIN(ts), MAX(ts) FROM observatory_snapshots;"` — ha d'haver ≥4 files amb dates que cobreixen ≥4 setmanes naturals. Si no: STOP, és massa d'hora.

### Step 2: Afegir les seccions V2 i V4 a `observatori.html`

Afegir dues noves `<section class="chart-section">` just ABANS de la secció de novetats (`.chart-section` amb `id="novetats-list"`):

**Secció V2 — Evolució per grado:**
```html
<section class="chart-section">
  <h2>Evolució per grado</h2>
  <div class="chart-wrap" id="chart-grados-evol-wrap">
    <div class="loading-state" id="chart-grados-evol-loading">Carregant dades...</div>
    <div id="chart-grados-evol" style="display:none"></div>
  </div>
</section>
```

**Secció V4 — Altes per setmana:**
```html
<section class="chart-section">
  <h2>Titulacions noves per setmana</h2>
  <div class="chart-wrap">
    <div class="bar-chart-vertical" id="chart-altes">
      <div class="loading-state">Carregant...</div>
    </div>
  </div>
</section>
```

### Step 3: Afegir les funcions JS a `observatori.html`

Afegir les dues funcions dins el `<script>` existent, just ABANS de la crida `load()`:

**`renderGradosEvol(series)`** — línies múltiples amb uPlot:
```javascript
function renderGradosEvol(series) {
  const wrap = document.getElementById('chart-grados-evol-wrap');
  const loading = document.getElementById('chart-grados-evol-loading');
  const container = document.getElementById('chart-grados-evol');

  if (series.length < 4) {
    loading.textContent = 'Poques dades per mostrar tendències per grado (mínim 4 setmanes).';
    return;
  }

  const timestamps = series.map(s => new Date(s.ts).getTime() / 1000);
  const colors = { A: '#1c1410', B: '#8a7060', C: '#4a7c59', D: '#6b7fb8', E: '#c07a5a' };

  const opts = {
    width: wrap.clientWidth - 40,
    height: 240,
    series: [
      {},
      ...['A', 'B', 'C', 'D', 'E'].map(g => ({
        label: `Grau ${g}`,
        stroke: colors[g],
        width: 2,
      })),
    ],
    axes: [
      { stroke: '#8a7060', ticks: { stroke: '#e8ddd4' } },
      { stroke: '#8a7060', ticks: { stroke: '#e8ddd4' }, size: 60 },
    ],
    scales: { x: { time: true } },
    legend: { show: true },
  };

  loading.style.display = 'none';
  container.style.display = 'block';
  new uPlot(opts, [timestamps, ...['A', 'B', 'C', 'D', 'E'].map(g => series.map(s => s[g] || 0))], container);
}
```

**`renderAltesChart(series)`** — barres verticals SVG manual:
```javascript
function renderAltesChart(series) {
  const container = document.getElementById('chart-altes');
  const altes = series.filter(s => s.n_altes > 0);
  if (!altes.length) {
    container.innerHTML = '<p class="empty-state">Cap alta registrada fins ara</p>';
    return;
  }
  const maxAltes = Math.max(...altes.map(s => s.n_altes), 1);
  const barW = 28;
  const gap = 6;
  const chartH = 120;
  const svgW = altes.length * (barW + gap);

  const bars = altes.map((s, i) => {
    const h = Math.round((s.n_altes / maxAltes) * chartH);
    const x = i * (barW + gap);
    const y = chartH - h;
    const dateStr = new Date(s.ts).toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit' });
    return `<g>
      <rect x="${x}" y="${y}" width="${barW}" height="${h}" fill="var(--dark)" rx="2"/>
      <text x="${x + barW / 2}" y="${chartH + 14}" text-anchor="middle" font-size="10" fill="var(--warm)">${dateStr}</text>
      <text x="${x + barW / 2}" y="${y - 3}" text-anchor="middle" font-size="10" fill="var(--dark)">${s.n_altes}</text>
    </g>`;
  }).join('');

  container.innerHTML = `<svg width="${svgW}" height="${chartH + 30}" style="overflow:visible">
    ${bars}
    <line x1="0" y1="${chartH}" x2="${svgW}" y2="${chartH}" stroke="var(--border)" stroke-width="1"/>
  </svg>`;
}
```

Afegir les crides dins la funció `load()`, just DESPRÉS de `renderBarChart(data.current)`:
```javascript
renderGradosEvol(data.series || []);
renderAltesChart(data.series || []);
```

### Step 4: Millorar el `<noscript>` amb números reals

Substituir el `<noscript>` existent per un que inclogui instruccions de fallback clares:

```html
<noscript>
  <div style="padding:32px;font-family:sans-serif;">
    <h1>Observatori de l'oferta FP espanyola</h1>
    <p>Per veure les estadístiques interactives cal activar JavaScript.</p>
    <p>Dades actualitzades setmanalment des del Ministerio de Educación (todofp.es).</p>
  </div>
</noscript>
```

### Step 5: Afegir links a l'observatori des d'`index.html` i `historial.html`

**A `historial.html`** — afegir un segon link al footer (seguint el patró existent):
```html
<footer>
  <a href="index.html">← Tornar al cercador</a>
  &nbsp;·&nbsp;
  <a href="observatori.html">Observatori FP →</a>
</footer>
```

**A `index.html`** — localitzar el footer i afegir el link. El patró exacte dependrà de l'estructura del footer actual: llegir el footer d'`index.html` i afegir-hi el link de manera coherent amb el disseny existent. No alterar cap altra cosa d'`index.html`.

## Done criteria

- [ ] Hi ha ≥4 setmanes de dades a `observatory_snapshots` (Step 1 verificat)
- [ ] La secció V2 (evolució per grado) es mostra a `observatori.html`
- [ ] La secció V4 (altes per setmana) es mostra amb barres SVG
- [ ] `historial.html` té link a `observatori.html` al footer
- [ ] `index.html` té link a `observatori.html`
- [ ] `git status` — cap fitxer fora de l'scope modificat

## STOP conditions

- **Menys de 4 setmanes de dades**: ATURA — executar aquest pla no té sentit fins que els gràfics tinguin contingut real. Reportar quantes setmanes hi ha i tornar quan hi hagi prou.
- Si la secció V2 amb uPlot falla perquè la versió d'uPlot vendoritzada no suporta múltiples sèries de la manera esperada: ATURA i reporta l'error de consola.

## Git workflow

```
git add frontend/observatori.html frontend/index.html frontend/historial.html
git commit -m "feat(F7): gràfics V2+V4 + links observatori des d'index/historial (pla 033)"
```

## Maintenance notes

- El pla 033 és el tancament de F7. Un cop completat, afegir l'entrada de F7 al ROADMAP-FEATURES.md com a DONE.
- Si en el futur s'afegeixen dades de centres (post-pla 016b), afegir aquí la visualització V7 (centres per família) — només caldrà afegir una nova `<section>` i una nova funció render.
