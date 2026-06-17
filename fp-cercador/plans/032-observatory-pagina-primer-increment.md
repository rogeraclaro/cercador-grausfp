# Pla 032: [F7] Pàgina `observatori.html` — primer increment (V1 + V3 + V6)

## Status

- **Priority**: P2
- **Effort**: M (4-6h)
- **Risk**: LOW — pàgina nova independent, no toca codi existent
- **Depends on**: Pla 031 DONE (endpoint `/api/observatory` funcionant)
- **Category**: frontend
- **Planned at**: commit `b84ffb4`, 2026-06-17

## Why this matters

El primer increment demostrable de l'Observatori: una pàgina pública que mostra l'evolució del total de titulacions FP (línia), la distribució per grado (barres SVG manuals), i les darreres novetats amb links al cercador. Completament funcional amb les dades actuals. És el lliurable visible de F7.

## Decisions de disseny (del spike, tancades)

- **Gràfics de sèries temporals** (V1): uPlot ~15 KB, vendoritzat a `frontend/vendor/uplot.min.js`
- **Distribució per grado** (V3): SVG generat a mà en JS vanilla (~60 línies)
- **Últimes novetats** (V6): llista HTML renderitzada en JS, links al cercador amb `?grado=X&q=denominacio`
- **Idioma**: català (`<html lang="ca">`), `<title>` i `<meta description>` en castellà per SEO
- **Patró visual**: idèntic a `historial.html` — variables CSS, fonts, topbar, hero

## Variables CSS i fonts del projecte (de `historial.html`)

```css
:root {
  --dark: #1c1410;
  --warm: #8a7060;
  --warm2: #f5ece2;
  --border: #e8ddd4;
  --bg: #fdf8f2;
  --white: #ffffff;
}
/* Fonts: DM Sans (body), DM Serif Display (h1), Geist Mono (mono) */
```

## Scope

**In scope**:
- `frontend/observatori.html` (fitxer nou)
- `frontend/vendor/uplot.min.js` (fitxer nou — descarregar i vendoritzar)

**Out of scope**: cap fitxer existent. `index.html`, `historial.html`, `app.py`, `auth.js` — no tocar. Els links des d'`index.html` i `historial.html` cap a l'observatori es faran al pla 033 o com a tasca separada.

## Steps

### Step 1: Vendoritzar uPlot

Descarregar uPlot des de npm (no CDN):

```bash
# Opció A: via npm (si disponible)
npm pack uplot@1.6.30
# extreu el fitxer dist/uplot.min.js

# Opció B: descarregar directament del repositori GitHub de uPlot
# https://github.com/leeoniya/uPlot/raw/master/dist/uPlot.iife.min.js
# Desar a frontend/vendor/uplot.min.js
```

Verificar mida: `wc -c frontend/vendor/uplot.min.js` — ha de ser entre 35.000 i 50.000 bytes (~15 KB gzipped).

Verificar llicència: uPlot és MIT. No cal fitxer de llicència addicional, però afegir un comentari a la primera línia si el fitxer no el porta: `// uPlot v1.6.x — MIT License — https://github.com/leeoniya/uPlot`

### Step 2: Crear `frontend/observatori.html`

Estructura general (seguint el patró exacte d'`historial.html`):

```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Observatorio FP España — Estadísticas de la oferta formativa | GrausFP</title>
  <meta name="description" content="Evolución semanal de las titulaciones de Formación Profesional en España (Grados A–E). Estadísticas actualizadas automáticamente desde el Ministerio de Educación.">

  <!-- Mateixes fonts que historial.html -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=DM+Serif+Display:ital@0;1&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">

  <!-- uPlot vendoritzat -->
  <link rel="stylesheet" href="vendor/uplot.css"> <!-- si existeix, o inline els estils mínims -->
  <script src="vendor/uplot.min.js"></script>

  <style>
    /* Variables i reset idèntics a historial.html */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --dark: #1c1410; --warm: #8a7060; --warm2: #f5ece2;
      --border: #e8ddd4; --bg: #fdf8f2; --white: #ffffff;
    }
    body { font-family: 'DM Sans', -apple-system, sans-serif; font-size: 14px; color: var(--dark); background: var(--bg); }

    /* Topbar idèntic */
    .topbar { background: var(--dark); padding: 0 48px; }
    .topbar-inner { display: flex; align-items: center; height: 52px; }
    .topbar-logo { font-family: 'DM Serif Display', serif; color: var(--white); font-size: 20px; letter-spacing: -0.3px; text-decoration: none; }

    /* Hero */
    .hero { border-bottom: 2px solid var(--dark); padding: 40px 48px 32px; }
    .hero h1 { font-family: 'DM Serif Display', serif; font-size: 48px; font-weight: 400; line-height: 1.05; color: var(--dark); margin-bottom: 10px; }
    .hero-sub { font-size: 15px; color: var(--warm); }

    /* Stats strip al hero */
    .stats-strip { display: flex; gap: 32px; margin-top: 24px; flex-wrap: wrap; }
    .stat-card { display: flex; flex-direction: column; gap: 4px; }
    .stat-value { font-family: 'DM Serif Display', serif; font-size: 36px; line-height: 1; color: var(--dark); }
    .stat-label { font-size: 12px; color: var(--warm); text-transform: uppercase; letter-spacing: 0.06em; }

    /* Contingut */
    .content { padding: 28px 48px 64px; }
    .chart-section { margin-bottom: 48px; }
    .chart-section h2 { font-family: 'DM Serif Display', serif; font-size: 24px; font-weight: 400; margin-bottom: 16px; }
    .chart-wrap { background: var(--white); border: 1px solid var(--border); border-radius: 2px; padding: 20px; }

    /* Barres SVG distribució */
    .bar-chart { display: flex; flex-direction: column; gap: 10px; max-width: 480px; }
    .bar-row { display: flex; align-items: center; gap: 12px; }
    .bar-label { width: 56px; font-size: 13px; font-weight: 600; color: var(--dark); }
    .bar-track { flex: 1; height: 20px; background: var(--warm2); border-radius: 2px; overflow: hidden; }
    .bar-fill { height: 100%; background: var(--dark); border-radius: 2px; transition: width 0.4s ease; }
    .bar-value { width: 64px; font-size: 12px; color: var(--warm); text-align: right; font-family: 'Geist Mono', monospace; }

    /* Llista novetats */
    .novetats-list { list-style: none; padding: 0; }
    .noveta-item { padding: 12px 0; border-bottom: 1px solid var(--border); }
    .noveta-item:last-child { border-bottom: none; }
    .noveta-date { font-family: 'Geist Mono', monospace; font-size: 11px; color: var(--warm); margin-bottom: 6px; }
    .noveta-chips { display: flex; flex-wrap: wrap; gap: 4px; }
    .chip { border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
    .chip-new { background: #dcfce7; color: #166534; }
    .chip-link { text-decoration: none; cursor: pointer; }
    .chip-link:hover { filter: brightness(0.9); }

    /* Auth widget al topbar */
    #auth-widget { margin-left: auto; display: flex; align-items: center; gap: 8px; }
    .auth-greeting { color: rgba(255,255,255,0.75); font-size: 13px; }
    .auth-btn { font-size: 13px; padding: 5px 14px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.35); color: var(--white); background: transparent; cursor: pointer; text-decoration: none; font-family: inherit; }
    .auth-btn:hover { background: rgba(255,255,255,0.12); }
    .auth-btn--primary { background: var(--white); color: var(--dark); border-color: var(--white); }

    /* States */
    .loading-state { text-align: center; padding: 64px 48px; color: var(--warm); }
    .empty-state { text-align: center; color: var(--warm); padding: 32px; font-style: italic; }

    /* Footer */
    footer { border-top: 1px solid var(--border); padding: 20px 48px; }
    .footer-note { font-size: 12px; color: var(--warm); }
    footer a { font-size: 13px; color: var(--warm); text-decoration: none; }
    footer a:hover { color: var(--dark); }

    /* Responsive */
    @media (max-width: 768px) {
      .topbar { padding: 0 16px; }
      .hero { padding: 24px 16px 20px; }
      .hero h1 { font-size: 30px; }
      .content { padding: 16px 16px 32px; }
      footer { padding: 20px 16px; }
      .stats-strip { gap: 20px; }
      .stat-value { font-size: 28px; }
    }
  </style>
  <script src="auth.js"></script>
</head>
<body>

  <header class="topbar">
    <div class="topbar-inner">
      <a href="index.html" class="topbar-logo">GrausFP</a>
      <div id="auth-widget"></div>
    </div>
  </header>

  <div class="hero">
    <h1>Observatori<br><em>de l'oferta FP</em></h1>
    <p class="hero-sub">Evolució setmanal del catàleg de Formació Professional espanyol</p>
    <div class="stats-strip" id="stats-strip">
      <div class="stat-card"><span class="stat-value" id="stat-total">—</span><span class="stat-label">Titulacions actives</span></div>
      <div class="stat-card"><span class="stat-value">5</span><span class="stat-label">Grados (A–E)</span></div>
      <div class="stat-card"><span class="stat-value" id="stat-date">—</span><span class="stat-label">Darrera actualització</span></div>
    </div>
  </div>

  <main class="content">

    <section class="chart-section">
      <h2>Evolució del total de titulacions</h2>
      <div class="chart-wrap" id="chart-total-wrap">
        <div class="loading-state" id="chart-total-loading">Carregant dades...</div>
        <div id="chart-total" style="display:none"></div>
      </div>
    </section>

    <section class="chart-section">
      <h2>Distribució per grado</h2>
      <div class="chart-wrap">
        <div class="bar-chart" id="chart-grados">
          <div class="loading-state">Carregant...</div>
        </div>
      </div>
    </section>

    <section class="chart-section">
      <h2>Darreres novetats</h2>
      <ul class="novetats-list" id="novetats-list">
        <li class="loading-state">Carregant...</li>
      </ul>
    </section>

  </main>

  <footer>
    <p class="footer-note">Font: Ministerio de Educación, FP.es (todofp.es). Actualitzat automàticament cada setmana.</p>
    <a href="historial.html">← Veure l'historial complet</a>
  </footer>

  <noscript>
    <p>Observatori de l'oferta FP espanyola. Activa JavaScript per veure les estadístiques interactives.</p>
  </noscript>

  <script>
    const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:5001' : '';

    function formatDate(iso) {
      const d = new Date(iso);
      return d.toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }

    function renderBarChart(current) {
      const container = document.getElementById('chart-grados');
      const grados = ['A', 'B', 'C', 'D', 'E'];
      const total = current.total || 1;
      const html = grados.map(g => {
        const val = current[g] || 0;
        const pct = ((val / total) * 100).toFixed(1);
        return `<div class="bar-row">
          <span class="bar-label">Grau ${g}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
          <span class="bar-value">${val.toLocaleString('ca-ES')} (${pct}%)</span>
        </div>`;
      }).join('');
      container.innerHTML = html;
    }

    function renderNovetats(recentChanges) {
      const list = document.getElementById('novetats-list');
      if (!recentChanges.length) {
        list.innerHTML = '<li class="empty-state">Sense novetats recents</li>';
        return;
      }
      list.innerHTML = recentChanges.map(entry => {
        const chips = Object.entries(entry.new_by_grado).flatMap(([grado, denoms]) =>
          denoms.slice(0, 5).map(d => {
            const q = encodeURIComponent(d);
            return `<a class="chip chip-new chip-link" href="index.html?grado=${grado}&q=${q}" title="${d}">Grau ${grado}: ${d.length > 40 ? d.slice(0, 40) + '…' : d}</a>`;
          })
        ).join('');
        return `<li class="noveta-item">
          <div class="noveta-date">${formatDate(entry.ts)}</div>
          <div class="noveta-chips">${chips || '<span style="color:var(--warm);font-size:12px">Sense denominacions detallades</span>'}</div>
        </li>`;
      }).join('');
    }

    function renderLineChart(series) {
      const wrap = document.getElementById('chart-total-wrap');
      const loading = document.getElementById('chart-total-loading');
      const container = document.getElementById('chart-total');

      if (series.length < 2) {
        loading.textContent = 'Poques dades per mostrar una tendència (mínim 2 refreshos).';
        return;
      }

      const timestamps = series.map(s => new Date(s.ts).getTime() / 1000);
      const totals = series.map(s => s.total);

      loading.style.display = 'none';
      container.style.display = 'block';

      const opts = {
        width: wrap.clientWidth - 40,
        height: 220,
        cursor: { show: true },
        series: [
          {},
          {
            label: 'Total titulacions',
            stroke: '#1c1410',
            width: 2,
            fill: 'rgba(138,112,96,0.08)',
          },
        ],
        axes: [
          { stroke: '#8a7060', ticks: { stroke: '#e8ddd4' } },
          { stroke: '#8a7060', ticks: { stroke: '#e8ddd4' }, size: 60 },
        ],
        scales: { x: { time: true } },
      };

      new uPlot(opts, [timestamps, totals], container);
    }

    async function load() {
      try {
        const res = await fetch(API_BASE + '/api/observatory');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();

        // Stats strip
        if (data.current && data.current.total) {
          document.getElementById('stat-total').textContent = data.current.total.toLocaleString('ca-ES');
        }
        if (data.current && data.current.ts) {
          document.getElementById('stat-date').textContent = formatDate(data.current.ts);
        }

        // Gràfic de línies V1
        renderLineChart(data.series || []);

        // Barres distribució V3
        if (data.current && data.current.total) {
          renderBarChart(data.current);
        }

        // Novetats V6
        renderNovetats(data.recent_changes || []);

      } catch (e) {
        document.querySelector('.content').innerHTML =
          '<p class="empty-state" style="color:#991b1b;">Error carregant les dades de l\'Observatori.</p>';
      }
    }

    load();
  </script>
</body>
</html>
```

**Notes d'implementació per a l'executor:**
- Si `uPlot` necessita un fitxer CSS a part (`uplot.css`), vendoritzar-lo també a `frontend/vendor/uplot.css`. Si no n'hi ha, eliminar el `<link rel="stylesheet" href="vendor/uplot.css">`.
- El codi de `renderLineChart` és una guia — adaptar `opts` si l'API d'uPlot de la versió descargada difereix (consultar la documentació inline del fitxer `.min.js` o el README del repositori).
- El mockup HTML d'aquest pla és complet però l'executor ha de verificar que funciona realment al navegador amb les dades reals de l'endpoint.

## Done criteria

- [ ] `frontend/vendor/uplot.min.js` existeix i pesa entre 30–60 KB
- [ ] `frontend/observatori.html` existeix i carrega sense errors de consola
- [ ] Els 3 números del stats-strip es rendren (total, grados, data)
- [ ] El gràfic de línies V1 es mostra (o mostra el missatge "Poques dades" si hi ha <2 punts)
- [ ] Les barres de distribució V3 es rendren amb percentatges
- [ ] La llista de novetats V6 es mostra o mostra "Sense novetats recents"
- [ ] Els links de novetats apunten a `index.html?grado=X&q=denominacio`
- [ ] La pàgina és responsiva (mòbil: h1 30px, padding reduït)
- [ ] `git status` — cap fitxer fora de l'scope modificat

## STOP conditions

- Si `uPlot` no es pot descarregar sense CDN en l'entorn d'execució: ATURA i reporta — el revisor decidirà si usar SVG pur com a alternativa.
- Si l'endpoint `/api/observatory` retorna error o no existeix (pla 031 no executat): ATURA.
- Si l'API d'uPlot de la versió disponible és molt diferent del codi de `renderLineChart`: documenta la diferència i adapta mínimament — no canviis l'estructura de la pàgina.

## Git workflow

```
git add frontend/observatori.html frontend/vendor/uplot.min.js
git commit -m "feat(F7): pàgina observatori.html primer increment V1+V3+V6 (pla 032)"
```

## Maintenance notes

- El pla 033 afegirà V2 (evolució per grado) i V4 (altes per setmana) dins el mateix `observatori.html` quan hi hagi ≥4 setmanes de dades reals a `observatory_snapshots`.
- Quan el pla 033 estigui DONE, afegir l'enllaç des d'`index.html` (footer o nav) i des d'`historial.html`.
- Si en el futur es vendoritza una nova versió d'uPlot, actualitzar `frontend/vendor/uplot.min.js` i verificar que `renderLineChart` segueix funcionant.
