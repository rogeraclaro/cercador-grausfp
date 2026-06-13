# Plan 020: Enriquiment Grado C (LOE) amb dades del Buscador de Certificats

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Context previ**: Llegeix `plans/outputs/spike-grado-c.md` ABANS de
> començar. Conté el contracte exacte de l'API (endpoints, paràmetres, patrons
> URL) i els resultats de les peticions de mostra. No répeteixis la
> investigació: tots els fets ja estan verificats.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> ```
> grep -n "ficha_id" backend/scrapers/buscador_scraper.py
> grep -n "parse_buscador_all\|pipeline" backend/pipeline.py | head -20
> grep -n "def run\|ofertes\|grado" backend/pipeline.py | head -20
> ```
> Si el codi viu difereix significativament dels extractes de "Current state",
> tracta-ho com a STOP condition i informa.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (tot és addició; cap canvi destructiu al pipeline existent)
- **Depends on**: 001, 002 (suite de tests verda), 006 (gzip ofertes)
- **Category**: feature
- **Planned at**: 2026-06-13, basat en spike `plans/outputs/spike-grado-c.md`

## Why this matters

Els 584 Grado C LOE (plan_antiguo=True) mostren avui només denominació, codi,
família i nivell. El Buscador de Certificados de Profesionalidad del ministeri
exposa durada en hores, URL del Real Decreto al BOE, fitxa PDF annexe i
suplementos Europass per a cadascun. El spike ha verificat que:

- 1 sol POST `paso=600` retorna els 588 certificats amb `certID` i `duracion_horas` en 2.4 s
- Les URLs de l'Annexe PDF i Europass són **derivables** de `codigo` + `nivel` (0 peticions extra)
- La URL del BOE s'obté via `fichaCP` on-demand quan l'usuari la demana (~1.5 s)
- El matching per `codigo` és del **100%** per als 584 antics

## Current state (fets verificats al codi)

- `backend/scrapers/buscador_scraper.py` — patró de referència: `_bootstrap_session` +
  `_fetch` + `_map_record`. El nou scraper seguirà exactament aquest patró.
- `backend/pipeline.py` — crida `parse_buscador_all()` i genera `ofertes.json`.
  Cal afegir-hi una crida opcional al nou scraper.
- `backend/app.py` — exposa `/api/ofertes` i endpoints admin. Cal afegir
  `GET /api/certificado/<codigo>`.
- `frontend/index.html` — línies 834–845 ja tenen tractament especial per a
  `row.grado === 'C' && row.plan_antiguo`. El panel expandible s'inserirà aquí.

## Scope

**In scope**:
- `backend/scrapers/certificados_scraper.py` (nou)
- `backend/pipeline.py` (modificació: crida al nou scraper + enriquiment)
- `backend/app.py` (nou endpoint `/api/certificado/<codigo>`)
- `frontend/index.html` (fila expandible per a Grado C antics)

**Out of scope**:
- Centres ("Dónde estudiar") — reservat per al Spike 015
- Tests dels nous components — fora d'abast per ara (la suite existent no ha de trencar)
- Grado C nous (plan_antiguo=False) — no existeixen al buscador de certificats

## Steps

### Step 1: Crear `backend/scrapers/certificados_scraper.py`

Crea el fitxer nou. Ha de seguir exactament el patró de `buscador_scraper.py`:

```python
"""
certificados_scraper.py — Enriquiment dels Grado C (LOE) amb dades del
Buscador de Certificados de Profesionalidad (todofp.es).

Flow:
  1. GET https://www.todofp.es/buscadorcertificados/buscador
     → obté cookie __Host-todofp.es (sense JSESSIONID)
  2. POST /busquedaCP (paso=600) → HTML amb tots els certificats
     → extreu certID i duracion_horas per a cadascun

La font retorna HTML, no JSON. BeautifulSoup per al parsing.
"""
```

**Funcions a implementar**:

```python
BASE_CERT_URL = 'https://www.todofp.es/buscadorcertificados'
BASE_DAM = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

def _bootstrap_session(timeout=30) -> requests.Session:
    """GET /buscador → cookie __Host-todofp.es."""

def fetch_all() -> dict[str, dict]:
    """
    POST /busquedaCP (paso=600) → dict keyed by codigo.
    Cada valor: {'cert_id': int, 'duracion_horas': int | None}
    """

def enrich_record(record: dict, cert_data: dict) -> dict:
    """
    Afegeix camps derivats a un registre Grado C plan_antiguo=True.
    rep 'record' (el registre d'ofertes.json) i 'cert_data' (de fetch_all).
    Retorna el registre enriquit (no modifica l'original in-place).
    """
```

**Camps que ha de generar `enrich_record`**:

```python
codigo_lc = record['codigo'].lower()  # 'adgg0408'
nivel_n   = str(record['nivel'])      # '1', '2' o '3'

return {
    **record,
    'duracion_horas':   cert_data['duracion_horas'],       # INT o None
    'cert_id_buscador': cert_data['cert_id'],              # INT
    'url_anexo_pdf':    f"{BASE_DAM}/anexos/{codigo_lc}.pdf",
    'url_europass_es':  f"{BASE_DAM}/europass/n{nivel_n}-{codigo_lc}-es-pub.pdf",
    'url_europass_en':  f"{BASE_DAM}/europass/n{nivel_n}-{codigo_lc}-in-pub.pdf",
}
```

**Parsing HTML** (patró verificat al spike):
- Bootstrap: `session.get(BASE_CERT_URL + '/buscador', timeout=timeout)`
- POST: `session.post(BASE_CERT_URL + '/busquedaCP', data={...}, timeout=60)`
- Paràmetres POST: `{'limite': '0', 'paso': '600', 'total': '0', 'codigo': '', 'denominacion': '', 'familia': '0', 'nivel': '0'}`
- Files: `soup.select('table.tabla-resultados tbody tr')`
- certID: `row.find('input', {'name': 'certificadoID'})['value']`
- codigo: `row.find('td', class_='colCodigo').get_text(strip=True)`
- durada: `row.find('td', {'headers': 'columna-cuatro'}).find('p').get_text(strip=True)` → regex `(\d+)\s*horas`

**Verificació del Step 1**:
```bash
cd fp-cercador
python3 -c "
from backend.scrapers.certificados_scraper import fetch_all
data = fetch_all()
print(f'Total: {len(data)}')
import random; sample = random.choice(list(data.items()))
print('Mostra:', sample)
"
```
Esperat: `Total: 588`, mostra amb `cert_id` INT i `duracion_horas` INT.

---

### Step 2: Integrar al `backend/pipeline.py`

Localitza la funció `run()` (o equivalent) que genera `ofertes.json`. Afegeix, **després** de la crida a `parse_buscador_all()` i **abans** de desar el fitxer:

```python
# Enriquiment Grado C LOE (plan_antiguo=True) amb dades del buscador de certificats
try:
    from .scrapers.certificados_scraper import fetch_all as fetch_certificados, enrich_record
    cert_data = fetch_certificados()
    for record in all_records:
        if record.get('grado') == 'C' and record.get('plan_antiguo'):
            enrichment = cert_data.get(record['codigo'])
            if enrichment:
                record.update(enrich_record(record, enrichment))
    logger.info(f"Enriquiment Grado C: {len(cert_data)} certificats processats")
except Exception as exc:
    logger.warning(f"Enriquiment Grado C fallat (continua sense dades extra): {exc}")
```

> El `try/except` és **obligatori**: si el buscador de certificats no respon,
> el pipeline ha de continuar generant `ofertes.json` sense les dades extra,
> sense avortar el refresh.

Adapta la importació i el nom de la llista `all_records` al codi real de `pipeline.py`.

**Verificació del Step 2**:
```bash
python3 -c "
import json
# Força un refresh local (si hi ha una funció run() accessible)
# O comprova el JSON existent si ja s'ha regenerat
with open('backend/data/ofertes.json') as f: data = json.load(f)
c_antics = [r for r in data if r.get('grado')=='C' and r.get('plan_antiguo')]
sample = next((r for r in c_antics if r.get('duracion_horas')), None)
print('Registre enriquit:', sample)
print('Total enriquits:', sum(1 for r in c_antics if r.get('duracion_horas')))
"
```
Esperat: registre amb `duracion_horas`, `url_anexo_pdf`, `url_europass_es`, `url_europass_en`.

> **Nota**: Si el refresh del pipeline triga molt en local (fa scraping real),
> pots saltar-te la verificació del JSON i fer-la al Step 4 amb un test manual.

---

### Step 3: Nou endpoint `GET /api/certificado/<codigo>` a `backend/app.py`

Afegeix l'endpoint just abans del bloc `if __name__ == '__main__':` o agrupat amb els altres endpoints de l'API.

```python
@app.route('/api/certificado/<string:codigo>')
def get_certificado_detail(codigo):
    """
    Retorna url_boe per a un Grado C LOE (plan_antiguo=True).
    Fa POST a fichaCP del ministeri on-demand.
    """
    import re
    from bs4 import BeautifulSoup

    CERT_BASE = 'https://www.todofp.es/buscadorcertificados'

    # Valida format del codi (protecció bàsica contra injeccions de path)
    if not re.match(r'^[A-Z0-9_]{4,20}$', codigo):
        return jsonify({'error': 'Codi invàlid'}), 400

    # Necessitem cert_id_buscador — el busquem a ofertes.json en memòria
    ofertes = _load_ofertes()  # usa la funció/cache que ja existeixi a app.py
    record = next(
        (r for r in ofertes if r.get('codigo') == codigo and r.get('plan_antiguo')),
        None
    )
    if not record:
        return jsonify({'error': 'Certificat no trobat o no és pla antic'}), 404

    cert_id = record.get('cert_id_buscador')
    if not cert_id:
        return jsonify({'error': 'cert_id_buscador no disponible'}), 404

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': CERT_BASE + '/buscador',
        })
        session.get(CERT_BASE + '/buscador', timeout=10)

        data = {
            'certificadoID': str(cert_id),
            'limite': '0', 'paso': '10', 'total': '1',
            'codigo': codigo, 'denominacion': '', 'familia': '0',
            'nivelFiltro': '0', 'origen': 'busquedaCP',
        }
        resp = session.post(CERT_BASE + '/fichaCP', data=data, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        boe_link = soup.find('a', class_='enlace-ficha-boe',
                             href=re.compile(r'boe\.es'))
        url_boe = boe_link['href'] if boe_link else None

        return jsonify({'codigo': codigo, 'url_boe': url_boe})

    except Exception as exc:
        return jsonify({'error': str(exc)}), 502
```

Adapta `_load_ofertes()` / `ofertes` a com `app.py` ja accedeix a les dades (variable global, funció de cache, etc.).

**Verificació del Step 3**:
```bash
# Inicia el servidor en local
python3 -m flask --app backend/app.py run --port 5001 &
sleep 2
curl -s http://localhost:5001/api/certificado/ADGG0408 | python3 -m json.tool
# Esperat: {"codigo": "ADGG0408", "url_boe": "https://www.boe.es/eli/es/rd/2011/5/9/645"}
curl -s http://localhost:5001/api/certificado/INVALID!! | python3 -m json.tool
# Esperat: 400 error
```

---

### Step 4: Fila expandible a `frontend/index.html`

Localitza el bloc de codi que renderitza cada fila de la taula (prop de les línies 834–845, on ja hi ha `row.grado === 'C' && row.plan_antiguo`).

**Comportament desitjat**:
- La fila principal és clicable per als Grado C antics
- En clicar, s'expandeix una subfiles amb:
  - `duracion_horas` en hores (si disponible)
  - Botó "Annexe PDF" → `url_anexo_pdf` (nova pestanya)
  - Botó "Europass ES" → `url_europass_es` (nova pestanya)
  - Botó "Europass EN" → `url_europass_en` (nova pestanya)
  - Botó "BOE / RD" → crida `/api/certificado/<codigo>`, obre `url_boe` en nova pestanya
- El panell es plega en tornar a clicar (toggle)
- Per als Grado C sense `duracion_horas` (no hauria de passar, però per si de cas), ometre el camp
- Per als Grado C nous (`plan_antiguo=False`) i la resta de graus, no hi ha cap canvi de comportament

**Patró recomanat amb Alpine.js** (ja vendoritzat a `frontend/vendor/`):

```html
<!-- A la fila de Grado C plan_antiguo -->
<tr @click="expanded = !expanded" class="cursor-pointer">
  <!-- cel·les existents -->
</tr>
<tr x-show="expanded" x-cloak>
  <td colspan="N" class="detall-certificat">
    <div class="detall-inner">
      <span x-show="row.duracion_horas" x-text="row.duracion_horas + ' h.'"></span>
      <a :href="row.url_anexo_pdf" target="_blank" class="btn-doc">Annexe PDF</a>
      <a :href="row.url_europass_es" target="_blank" class="btn-doc">Europass ES</a>
      <a :href="row.url_europass_en" target="_blank" class="btn-doc">Europass EN</a>
      <button @click.stop="fetchBoe(row.codigo)" class="btn-doc">BOE / RD</button>
    </div>
  </td>
</tr>
```

Adapta el patró al codi real d'`index.html` (pot usar `x-data`, `v-show`, o qualsevol mecanisme Alpine.js ja present). Mira com estan fetes les files actuals i segueix el mateix patró.

**Funció `fetchBoe`** (afegir al component Alpine.js corresponent):

```javascript
async fetchBoe(codigo) {
  try {
    const res = await fetch(`/api/certificado/${codigo}`);
    const data = await res.json();
    if (data.url_boe) {
      window.open(data.url_boe, '_blank');
    } else {
      alert('URL del BOE no disponible per a aquest certificat.');
    }
  } catch (e) {
    alert('Error en obtenir el BOE: ' + e.message);
  }
}
```

**Verificació del Step 4**:
- Obre `frontend/index.html` al navegador (o amb el servidor Flask que serveix el frontend)
- Filtra per Grado C
- Clica un registre amb `plan_antiguo=True` → s'ha d'expandir el panell
- Clica "Annexe PDF" → obre el PDF del ministeri
- Clica "BOE / RD" → fa la crida, obre la URL del BOE (pot trigar ~1.5 s)
- Clica un Grado C nou (`plan_antiguo=False`) → NO s'expandeix (sense panell)
- Clica un Grado A/B → comportament inalterats

---

## Done criteria

- [ ] `backend/scrapers/certificados_scraper.py` existeix i `fetch_all()` retorna 588 registres
- [ ] `backend/pipeline.py` enriqueix els 584 Grado C antics sense avortar si el scraper falla
- [ ] `backend/app.py` respon `GET /api/certificado/ADGG0408` amb `url_boe` vàlida
- [ ] `backend/app.py` retorna 400 per a codis amb format invàlid
- [ ] `frontend/index.html` mostra el panell expandible per a Grado C `plan_antiguo=True`
- [ ] Els botons Annexe PDF i Europass funcionen sense crida addicional al backend
- [ ] El botó BOE fa la crida on-demand i obre la URL correcta
- [ ] Els Grado C nous i la resta de graus no han canviat de comportament
- [ ] La suite de tests existent continua verda (`python3 -m pytest backend/tests/ -q`)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- El drift check mostra canvis substancials a `pipeline.py` o `app.py` respecte als extractes — atura't i informa
- `fetch_all()` rep 403 o 429 del servidor — atura't, no insisteixis
- El format HTML del buscador ha canviat i el parsing retorna 0 registres — atura't i documenta
- Apareix qualsevol dependència nova (un import que no sigui `requests`, `beautifulsoup4`, `flask`, `re`, `logging`) — consulta primer

## Maintenance notes

- Si todofp.es reorganitza el buscador de certificats (migra a SPA/JS), `certificados_scraper.py` trencarà silenciosament i el `try/except` del pipeline ho contindria. El símptoma visible seria que els Grado C deixen de tenir `duracion_horas` al JSON.
- Les URLs derivades (Annexe PDF, Europass) segueixen el patró DAM verificat el 2026-06-13. Si canvien, cal actualitzar les constants a `certificados_scraper.py`.
