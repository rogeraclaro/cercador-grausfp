# Pla 043 [SPIKE]: Investigació fonts C LOMLOE→D i B→C LOE

> **Executor instructions**: Ets l'investigador, no l'implementador. El teu
> únic output és un fitxer de resultats a `plans/outputs/spike_043_results.md`.
> NO modifiquis cap fitxer de producció (backend/, frontend/). Executa cada
> pas en ordre, documenta el que trobes i, al final, escriu el report de
> viabilitat. Si una STOP condition es dispara, atura't i reporta.
>
> **Drift check (executa primer)**:
> ```bash
> git diff --stat 500127b..HEAD -- backend/scrapers/certificados_scraper.py backend/scrapers/pipeline.py backend/itinerary.py
> ```
> Si cap dels fitxers ha canviat, continua. Si han canviat, compara els
> excerpts de "Current state" amb el codi viu.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (investigació pura, cap canvi de producció)
- **Depends on**: 042 DONE
- **Category**: direction
- **Planned at**: commit `500127b`, 2026-06-19

## Per què importa

El pla 042 implementa les relacions A→B (local) i C LOE→D (via ciclosFP). Falten
dues relacions per completar F5:
- **C LOMLOE→D**: 397 certificats de la nova llei (LOMLOE, `plan_antiguo=False`) que
  el buscadorcertificados clàssic no exposa. Sense font confirmada.
- **B→C LOE**: relació inversa —saber quin Certificat de Profesionalidad acredita un
  determinat mòdul B. El spike 041 va identificar l'Annexo PDF com a font possible
  (~579 PDFs) però no el va validar.

A més, el pla 042 mostra cicles D sense `ficha_url`: el teu botó "Cicles FP (D)"
llista noms però no linkeja a la fitxa del grau. Cal saber si `build_ciclos_index`
pot enriquir cada cicle amb la `ficha_url` en el moment de construir l'índex.

Aquest spike respon a tres preguntes concretes i escriu un veredicte per/contra
implementar cadascuna.

## Current state

### Registres rellevants a ofertes.json

```
C LOE  (plan_antiguo=True):   584 registres — códis ex: COML0110, ADGG0408
C LOMLOE (plan_antiguo=False): 397 registres — codis ex: ADG_C_001_2P (pat: FAM_C_NNN_NIVEL)
D:                             195 registres — sense `codigo`, té `ficha_url`
```

### URLs i endpoints coneguts

```python
BASE_CERT_URL = 'https://www.todofp.es/buscadorcertificados'
BASE_DAM = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

# C LOE Annexo PDF (confirmat al certificados_scraper.py:164):
url_anexo_pdf = f"{BASE_DAM}/anexos/{codigo_lc}.pdf"
# Exemple: https://www.todofp.es/dam/todofp/certificados-profesionales/anexos/coml0110.pdf

# POST /busquedaCP (confirmat al certificados_scraper.py:60):
# Retorna HTML amb tots els C LOE (plan_antiguo=True). NO inclou C LOMLOE.
payload_busquedaCP = {
    'limite': '0', 'paso': '600', 'total': '0',
    'codigo': '', 'denominacion': '', 'familia': '0', 'nivel': '0',
}

# POST /ciclosFP (confirmat al certificados_scraper.py:110):
# Retorna cicles D per a un cert_id. Cada fila: denominació | família | "NNNN - nom mòdul"
payload_ciclosFP = {
    'certificadoID': str(cert_id),
    'limite': '0', 'paso': '10', 'total': '588',
    'codigo': '', 'denominacion': '', 'familia': '0',
    'nivelFiltro': '0', 'origen': 'busquedaCP',
}
```

### Codi de referència — bootstrap session (certificados_scraper.py:36–42)

```python
def _bootstrap_session(timeout: int = 30) -> requests.Session:
    """GET /buscador → cookie __Host-todofp.es (sense JSESSIONID)."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.get(BASE_CERT_URL + '/buscador', timeout=timeout)
    resp.raise_for_status()
    return session
```

### Estructura d'un cicle D retornat per ciclosFP (confirmat al spike 041)

```
Ciclo             | Familia | Mòdul
Servicios Admin.  | ADG     | 3006 - Preparación de pedidos y venta de productos
Servicios Comerc. | COM     | 3006 - Preparación de pedidos y venta de productos
```

El camp "Mòdul" té format `NNNN - Denominació`. El número `NNNN` coincideix amb
el camp `numero` dels graus B LOMLOE (ex: `ADG_B_3006` té número `3006`).

### Codi de referència — build_ciclos_index (certificados_scraper.py:127–148)

```python
def build_ciclos_index(cert_data: dict[str, dict]) -> dict[str, list[dict]]:
    """
    {codigo_C: [{'denominacion': str, 'familia': str}]}
    """
    session = _bootstrap_session()
    result = {}
    for codigo, data in cert_data.items():
        cert_id = data.get('cert_id')
        if not cert_id:
            continue
        ciclos = fetch_ciclos_fp(session, cert_id)
        result[codigo] = ciclos
    return result
```

El dict de cada cicle ara és `{'denominacion': str, 'familia': str}`. **NO inclou
el número de mòdul ni la `ficha_url`**. Caldrà ampliar `fetch_ciclos_fp` per
extreure el número de mòdul de la cel·la "Mòdul" si volem fer el match amb D.

## Comandes que necessitaràs

| Propòsit | Comanda | Esperat en cas d'èxit |
|---|---|---|
| Verificar ofertes.json disponible | `python3 -c "import json; d=json.load(open('backend/data/ofertes.json')); print(len(d))"` | `12894` (o similar) |
| Instal·lar pdfplumber si cal | `pip3 install pdfplumber` o `pip install pdfplumber` | exit 0 |
| Verificar pdfplumber | `python3 -c "import pdfplumber; print('ok')"` | `ok` |
| Executar script d'investigació | `python3 plans/outputs/spike_043_investigate.py` | output text sense excepcions fatals |

## Àmbit

**In scope** (els ÚNICS fitxers que pots crear o modificar):
- `plans/outputs/spike_043_investigate.py` — script d'investigació (temporal, no és producció)
- `plans/outputs/spike_043_results.md` — report de viabilitat (el producte del spike)

**Out of scope** (NO tocar):
- `backend/scrapers/certificados_scraper.py` — no modificar; el spike llegeix però no edita
- `backend/itinerary.py`, `backend/app.py`, `frontend/index.html` — fora d'abast
- `backend/data/ofertes.json` — no modificar mai
- Qualsevol altre fitxer del repo

---

## Pas 1: Examina registres C LOMLOE i D locals

Crea `plans/outputs/spike_043_investigate.py` i afegeix la primera secció:

```python
#!/usr/bin/env python3
"""
spike_043_investigate.py — Investigació fonts C LOMLOE→D i B→C LOE.
NO és codi de producció. Escriu els resultats a stdout.
"""
import json, re, os, sys

DATA_PATH = 'backend/data/ofertes.json'
if not os.path.exists(DATA_PATH):
    print(f"ERROR: {DATA_PATH} no trobat. Executa des de l'arrel del repo.")
    sys.exit(1)

with open(DATA_PATH) as f:
    records = json.load(f)

by_grado = {}
for r in records:
    by_grado.setdefault(r['grado'], []).append(r)

# ============================================================
# SECCIÓ 1: Estructura registres C LOMLOE i D
# ============================================================
c_lomloe = [r for r in by_grado.get('C', []) if not r.get('plan_antiguo')]
c_loe    = [r for r in by_grado.get('C', []) if r.get('plan_antiguo')]
d_recs   = by_grado.get('D', [])

print(f"\n=== SEC 1: Registres C LOMLOE (n={len(c_lomloe)}) ===")
print(f"  Primers 5 codis: {[r.get('codigo') for r in c_lomloe[:5]]}")
print(f"  Camps d'un registre: {list(c_lomloe[0].keys()) if c_lomloe else 'cap'}")
if c_lomloe:
    r0 = c_lomloe[0]
    print(f"  ficha_url: {r0.get('ficha_url','(no existeix)')}")
    print(f"  url_anexo_pdf: {r0.get('url_anexo_pdf','(no existeix)')}")

print(f"\n=== SEC 1: Registres D (n={len(d_recs)}) ===")
print(f"  Primers 5 ficha_url: {[r.get('ficha_url') for r in d_recs[:5]]}")
print(f"  Camps d'un registre: {list(d_recs[0].keys()) if d_recs else 'cap'}")
if d_recs:
    print(f"  denominacion exemple: {d_recs[0].get('denominacion')}")
    print(f"  familia exemple: {d_recs[0].get('familia')}")

# Analitza el patró de ficha_url dels D: conté el número de mòdul?
print(f"\n=== SEC 1: Patró ficha_url D vs família/número ===")
for r in d_recs[:10]:
    url = r.get('ficha_url', '')
    den = r.get('denominacion', '')[:50]
    fam = r.get('familia', '')
    print(f"  fam={fam} | '{den}' | url={url}")
```

**Verifica**: `python3 plans/outputs/spike_043_investigate.py` → imprimeix SEC 1 sense error.

**Documenta al report final**:
- Els camps que té un registre C LOMLOE (especialment si té `ficha_url`)
- El patró de les `ficha_url` dels D (ex: conté `adg3006`? Conté família+num?)

---

## Pas 2: Analitza el match ciclosFP → D ficha_url

Afegeix al script (secció 2 — anàlisi local, sense xarxa):

```python
# ============================================================
# SECCIÓ 2: Match ciclosFP output → D ficha_url
# ============================================================
# ciclosFP retorna per a cada cicle: denominació, família, "NNNN - nom mòdul"
# Exemple COML0110: ADG | 3006 - Preparación de pedidos...
# Preguntes:
#   (a) Les ficha_url de D contenen la família + número? Ex: "adg3006" a l'URL?
#   (b) Podem indexar D per (família, num_mòdul)?

# Construeix índex D per família
d_by_familia = {}
for r in d_recs:
    fam = (r.get('familia') or '').upper()
    d_by_familia.setdefault(fam, []).append(r)

print(f"\n=== SEC 2: Famílies D ({len(d_by_familia)} famílies, {len(d_recs)} registres) ===")
for fam, recs in sorted(d_by_familia.items())[:8]:
    urls = [r.get('ficha_url','') for r in recs[:2]]
    print(f"  {fam}: {len(recs)} registres, URLs ex: {urls}")

# Comprova si les ficha_url contenen patrons numèrics que puguin ser el núm. mòdul
import re as _re
pat_num_url = _re.compile(r'(\d{4})')
print(f"\n=== SEC 2: Números 4 dígits a les ficha_url D ===")
for r in d_recs[:15]:
    url = r.get('ficha_url', '')
    nums = pat_num_url.findall(url)
    den  = r.get('denominacion', '')[:40]
    fam  = r.get('familia', '')
    print(f"  {fam} | '{den}' | url_nums={nums} | url={url[-60:]}")
```

**Verifica**: afegeix la secció i torna a executar. Busca si les URLs D contenen números 4 dígits.

**Documenta al report final**:
- Les URLs D contenen el número de mòdul? Ex: `gestion-administrativa.html` vs `adg3006.html`.
- Si sí: com construïm l'índex D_by_(família, num)?
- Si no: és viable algun altre camp per fer el match?

---

## Pas 3: Investiga C LOMLOE → D via buscadorcertificados (xarxa)

Afegeix al script (secció 3 — crides de xarxa):

```python
# ============================================================
# SECCIÓ 3: C LOMLOE → D via buscadorcertificados
# ============================================================
import requests
from bs4 import BeautifulSoup

BASE_CERT_URL = 'https://www.todofp.es/buscadorcertificados'
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': BASE_CERT_URL + '/buscador',
}

def _bootstrap():
    s = requests.Session()
    s.headers.update(_HEADERS)
    s.get(BASE_CERT_URL + '/buscador', timeout=20)
    return s

sess = _bootstrap()

print(f"\n=== SEC 3: POST /busquedaCP amb nivel=3 (C LOMLOE = nivell 3 LOMLOE?) ===")
# Hipòtesi 1: el paràmetre 'nivel' filtra per nivell. C LOE és nivell 1/2/3, C LOMLOE potser diferent.
# Provem diferent valor de nivel i familia per veure si apareixen codis LOMLOE.
for nivel_val in ['0', '3', '4', '5']:
    payload = {
        'limite': '0', 'paso': '20', 'total': '0',
        'codigo': '', 'denominacion': '', 'familia': '0', 'nivel': nivel_val,
    }
    try:
        r = sess.post(BASE_CERT_URL + '/busquedaCP', data=payload, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select('table.tabla-resultados tbody tr')
        codigos_sample = []
        for row in rows[:5]:
            cod_td = row.find('td', class_='colCodigo')
            if cod_td:
                codigos_sample.append(cod_td.get_text(strip=True))
        print(f"  nivel={nivel_val}: {len(rows)} files, mostra codis: {codigos_sample}")
    except Exception as e:
        print(f"  nivel={nivel_val}: ERROR: {e}")

# Hipòtesi 2: hi ha un endpoint diferent per a LOMLOE (/busquedaCPNuevo o similar)
print(f"\n=== SEC 3: Endpoints alternatius al buscadorcertificados ===")
for endpoint in ['/busquedaCPNuevo', '/busquedaGrado', '/buscadorNuevo', '/busquedaModulos']:
    try:
        r = sess.get(BASE_CERT_URL + endpoint, timeout=10)
        print(f"  GET {endpoint}: status={r.status_code}, len={len(r.text)}")
    except Exception as e:
        print(f"  GET {endpoint}: ERROR: {e}")

# Hipòtesi 3: la fitxa web d'un C LOMLOE (si té ficha_url) mostra cicles D
if c_lomloe and c_lomloe[0].get('ficha_url'):
    sample_url = c_lomloe[0]['ficha_url']
    print(f"\n=== SEC 3: Fitxa web C LOMLOE — {c_lomloe[0].get('codigo')} ===")
    print(f"  URL: {sample_url}")
    try:
        r2 = requests.get(sample_url, headers=_HEADERS, timeout=20)
        soup2 = BeautifulSoup(r2.text, 'html.parser')
        text2 = soup2.get_text(separator='\n')
        ciclo_refs = [l.strip() for l in text2.split('\n')
                      if l.strip() and any(kw in l.lower()
                      for kw in ['ciclo', 'grado', 'convalid', 'módulo', 'D '])]
        print(f"  Línies amb 'ciclo/grado/convalid': {len(ciclo_refs)}")
        for l in ciclo_refs[:10]:
            print(f"    {repr(l[:100])}")
        if not ciclo_refs:
            print(f"  (text complet 500 chars): {repr(text2[:500])}")
    except Exception as e:
        print(f"  ERROR llegint fitxa: {e}")
else:
    print(f"\n=== SEC 3: C LOMLOE NO té ficha_url — no es pot comprovar fitxa web directament ===")
    print(f"  Camps de c_lomloe[0]: {list(c_lomloe[0].keys()) if c_lomloe else []}")
```

**Verifica**: executa el script — ha de completar la SEC 3 sense crash (errors de xarxa puntuals estan permesos, però el script ha de continuar).

**Documenta al report final**:
- POST /busquedaCP amb diferentes valors de `nivel` — apareixen codis LOMLOE?
- Existeix algun endpoint alternatiu (400→no existeix, 200→possible font)?
- La fitxa web del C LOMLOE menciona cicles D?

---

## Pas 4: Investiga B→C LOE via Annexo PDF (descàrrega + pdfplumber)

Afegeix al script (secció 4):

```python
# ============================================================
# SECCIÓ 4: B→C LOE via Annexo PDF (pdfplumber)
# ============================================================
import io, time

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("\n=== SEC 4: pdfplumber NO disponible — instal·la'l amb 'pip install pdfplumber' ===")

BASE_DAM = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

# Mostra de C LOE de 3 famílies professionals DIFERENTS per avaluar consistència de format
# (codec, familia_professional)
samples_c_loe = []
famcoverage = set()
for r in c_loe:
    fam = r.get('familia', '')
    if fam not in famcoverage and r.get('codigo'):
        samples_c_loe.append(r)
        famcoverage.add(fam)
    if len(samples_c_loe) >= 3:
        break

print(f"\n=== SEC 4: Mostra de C LOE per Annexo PDF ({len(samples_c_loe)} famílies) ===")
for r in samples_c_loe:
    url_pdf = f"{BASE_DAM}/anexos/{r['codigo'].lower()}.pdf"
    print(f"  {r['codigo']} (fam={r['familia']}): {url_pdf}")

if PDFPLUMBER_AVAILABLE:
    pdf_headers = {
        'User-Agent': _HEADERS['User-Agent'],
        'Referer': 'https://www.todofp.es/',
    }
    
    for r in samples_c_loe:
        codigo = r['codigo']
        url_pdf = f"{BASE_DAM}/anexos/{codigo.lower()}.pdf"
        print(f"\n--- PDF: {codigo} ---")
        try:
            t0 = time.time()
            resp_pdf = requests.get(url_pdf, headers=pdf_headers, timeout=60, stream=True)
            content = resp_pdf.content
            elapsed = time.time() - t0
            size_kb = len(content) // 1024
            print(f"  Status: {resp_pdf.status_code}, Mida: {size_kb} KB, Temps: {elapsed:.1f}s")
            
            if resp_pdf.status_code != 200:
                print(f"  ERROR: HTTP {resp_pdf.status_code}")
                continue
            
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                n_pages = len(pdf.pages)
                print(f"  Pàgines: {n_pages}")
                
                # Busca UC codes a totes les pàgines
                uc_codes = []
                mf_codes = []
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ''
                    uc_found = re.findall(r'\bUC\d{4}_\d\b', text)
                    mf_found = re.findall(r'\bMF\d{4}_\d\b', text)
                    uc_codes.extend(uc_found)
                    mf_codes.extend(mf_found)
                    
                    # Prova d'extraure taula
                    tables = page.extract_tables()
                    if tables:
                        print(f"  Pàg.{i+1}: {len(tables)} taula(es) trobada(es)")
                        for t_idx, table in enumerate(tables[:1]):  # Mostra primera taula
                            print(f"    Taula {t_idx+1}: {len(table)} files x {len(table[0]) if table else 0} cols")
                            for row_t in table[:4]:  # Primers 4 files
                                print(f"      {row_t}")
                
                uc_codes_uniq = list(dict.fromkeys(uc_codes))
                mf_codes_uniq = list(dict.fromkeys(mf_codes))
                print(f"  UC codes trobats: {uc_codes_uniq[:10]}")
                print(f"  MF codes trobats: {mf_codes_uniq[:10]}")
                
                if not uc_codes_uniq and not mf_codes_uniq:
                    # Text complet de la primera pàgina per diagnosi
                    first_text = pdf.pages[0].extract_text() or '(buit)'
                    print(f"  AVÍS: cap UC/MF trobat. Text pàg 1 (300 chars): {repr(first_text[:300])}")
        
        except Exception as e:
            print(f"  ERROR: {e}")
        
        time.sleep(1)  # Rate limiting cortesia
```

**Verifica**: executa el script — per a cada PDF mostrar mida, num pàgines, i si s'han trobat UC/MF codes.

**Documenta al report final**:
- Els PDFs carreguen correctament? Quin és el temps i mida aproximats?
- pdfplumber troba taules estructurades amb UC/MF codes?
- Hi ha consistència entre famílies professionals?
- Estimació del cost total: mida_pdf × 579 ÷ MB (bandwidth), temps total estimat.

---

## Pas 5: Analitza el match entre mòdul ciclosFP i ficha_url D

Afegeix al script (secció 5 — anàlisi local, sense xarxa):

```python
# ============================================================
# SECCIÓ 5: Match ciclosFP num_modul → D ficha_url
# ============================================================
# ciclosFP retorna camps "Mòdul" com: "3006 - Preparación de pedidos..."
# El número 3006 coincideix amb codis B LOMLOE (ADG_B_3006, COM_B_3006).
# Cal saber si D ficha_url conté un patró indexable per (família, num).

# Exemple confirmat del spike 041: cert COML0110 → ADG | 3006 i COM | 3006
# Preguntes:
#   (a) Les D ficha_url contenen la família i el número? Ex: ".../adg3006..."?
#   (b) Podem construir un índex D_by_(familia.lower(), num_modul)?

print(f"\n=== SEC 5: Anàlisi match ciclosFP num_modul → D ficha_url ===")

# Analitza patró de totes les D ficha_url
pat_fam_num = re.compile(r'/([a-z]{2,4})(\d{4})[^/]*\.html')
pat_num_only = re.compile(r'(\d{4})')
fam_num_matches = []
for r in d_recs:
    url = (r.get('ficha_url') or '').lower()
    m = pat_fam_num.search(url)
    if m:
        fam_num_matches.append((m.group(1), m.group(2), r.get('familia',''), r.get('denominacion','')[:40]))

print(f"  D amb patró FAM+NNN a la URL: {len(fam_num_matches)} de {len(d_recs)}")
if fam_num_matches:
    for fam_url, num, fam_rec, den in fam_num_matches[:8]:
        print(f"  url_fam={fam_url}, url_num={num} | rec_fam={fam_rec} | '{den}'")

# Construeix índex D per (familia_lower, num_modul) si el patró existeix
d_by_fam_num = {}
for r in d_recs:
    url = (r.get('ficha_url') or '').lower()
    m = pat_fam_num.search(url)
    if m:
        key = (m.group(1), m.group(2))
        d_by_fam_num[key] = r

print(f"\n  Índex D per (fam, num): {len(d_by_fam_num)} entrades")

# Valida amb el cas confirmat: COML0110 → ADG | 3006
test_key_adg = ('adg', '3006')
test_key_com = ('com', '3006')
print(f"  Lookup ('adg','3006'): {d_by_fam_num.get(test_key_adg, {}).get('denominacion', 'NO TROBAT')}")
print(f"  Lookup ('com','3006'): {d_by_fam_num.get(test_key_com, {}).get('denominacion', 'NO TROBAT')}")

# Comprova cobertura: quants cicles D de l'índex ciclos_fp.json (si existeix)
# es podrien enrichir amb ficha_url?
ciclos_path = 'backend/data/ciclos_fp.json'
if os.path.exists(ciclos_path):
    with open(ciclos_path) as f:
        ciclos_index = json.load(f)
    pat_modul = re.compile(r'(\d{4})\s*-')
    enrichables = 0
    total_ciclos = 0
    for codigo_c, cicles in ciclos_index.items():
        for cicle in cicles:
            total_ciclos += 1
            den_cicle = cicle.get('denominacion', '')
            fam_cicle = (cicle.get('familia') or '').lower()
            m_num = pat_modul.search(den_cicle)
            if m_num:
                key = (fam_cicle, m_num.group(1))
                if key in d_by_fam_num:
                    enrichables += 1
    pct = enrichables / total_ciclos * 100 if total_ciclos else 0
    print(f"\n  ciclos_fp.json: {total_ciclos} cicles totals")
    print(f"  Enriquibles amb ficha_url: {enrichables} ({pct:.0f}%)")
else:
    print(f"\n  ciclos_fp.json no trobat — no es pot calcular cobertura d'enrichment")
    print(f"  (Cal executar el pipeline del pla 042 per generar-lo)")
```

**Verifica**: executa el script — ha de mostrar SEC 5 sense error. Si `ciclos_fp.json` no existeix, ha d'imprimir el missatge corresponent.

---

## Pas 6: Escriu el report de viabilitat

Crea `plans/outputs/spike_043_results.md` amb els resultats. Estructura obligatòria:

```markdown
# Spike 043 — Resultats: fonts C LOMLOE→D i B→C LOE

Executat: [DATA]
Commit base: 500127b
Executor: [nom/model]

## Taula de viabilitat

| Relació | Font investigada | Cobertura | Esforç | Risc | Veredicte |
|---------|-----------------|-----------|--------|------|-----------|
| C LOMLOE→D | [font o "cap font trobada"] | [N/A o NNN registres] | [S/M/L] | [LOW/MED/HIGH] | [VIABLE/NO VIABLE] |
| B→C LOE (Annexo PDF) | PDF pdfplumber | [% PDFs parsejables] | [S/M/L] | [LOW/MED/HIGH] | [VIABLE/NO VIABLE] |
| C→D ficha_url (enrich) | Índex D per (fam,num) | [% cicles enriquibles] | [S/M/L] | [LOW/MED/HIGH] | [VIABLE/NO VIABLE] |

## Resultats SEC 1: Estructura registres C LOMLOE i D

[Camps disponibles a C LOMLOE, si té ficha_url, patró ficha_url D]

## Resultats SEC 2: Match ciclosFP → D ficha_url

[Patró URLs D, funciona l'índex (fam,num)?, cobertura]

## Resultats SEC 3: C LOMLOE → D via buscadorcertificados

[POST /busquedaCP amb nivel diferent → retorna LOMLOE? Endpoints alternatius?
Fitxa web C LOMLOE menciona cicles D?]

## Resultats SEC 4: B→C LOE via Annexo PDF

[Per a cada PDF de mostra: mida, temps, UC/MF codes trobats, taules parseables?
Consistència entre famílies. Cost estimat total.]

## Resultats SEC 5: Match mòdul num → D ficha_url

[Patró URL, cobertura de l'índex, cas COML0110→ADG/3006 funciona?]

## Recomanació per a implementació

### C LOMLOE → D
[RECOMANACIÓ PER/CONTRA implementar. Si cal: proposa la font alternativa o
declara la relació com "no implementable amb fonts actuals".]

### B → C LOE (Annexo PDF)
[RECOMANACIÓ PER/CONTRA implementar. Si VIABLE: indica els punts d'integració
clau (no el codi complet).]

### C → D ficha_url enrichment
[RECOMANACIÓ PER/CONTRA implementar. Si VIABLE: indica si és una modificació
a build_ciclos_index o a fetch_ciclos_fp, i la cobertura esperada.]
```

**Verifica**: `ls -la plans/outputs/spike_043_results.md` → existeix i té >1 KB.

---

## Test plan

Aquest spike no produeix codi de producció. No hi ha tests a escriure.
El "test" del spike és la verificació que el script ha corregut sense errors
fatals i que el report de viabilitat conté dades reals (no cel·les buides).

## Criteris de DONE

- [ ] `plans/outputs/spike_043_investigate.py` existeix i s'executa sense crash (`python3 plans/outputs/spike_043_investigate.py 2>&1 | tail -5` no mostra `Traceback`)
- [ ] `plans/outputs/spike_043_results.md` existeix i conté la taula de viabilitat completa (totes les cel·les emplenades)
- [ ] Per a cada relació investigada, el veredicte és VIABLE o NO VIABLE (no deixar "?")
- [ ] Si B→C LOE via PDF és VIABLE: el report especifica cobertura UC/MF, mida PDF sample, i estimació temps total
- [ ] Si C→D ficha_url és VIABLE: el report especifica % cobertura i si el match (fam,num) funciona per al cas COML0110
- [ ] Cap fitxer de producció modificat: `git diff --name-only` mostra únicament fitxers a `plans/outputs/`
- [ ] `plans/README.md` actualitzat amb estat DONE per al pla 043

## Condicions STOP

Atura't i reporta (no improvisis) si:

- `ofertes.json` no existeix al path `backend/data/ofertes.json` i tampoc ets capaç d'obtenir-lo via `certificados_scraper.fetch_all()` — sense dades, les seccions 1/2/5 no es poden completar.
- `pdfplumber` no és instal·lable (no tens pip o l'entorn no ho permet) — documenta-ho al report i salta la SEC 4, però no avortes el spike per complet.
- El buscadorcertificados retorna HTTP 5xx per a totes les crides de la SEC 3 durant >2 minuts — pot ser un bloqueig temporal; documenta-ho i marca SEC 3 com "no accessible al moment de l'execució".
- El report final quedaria amb >1 cel·la de veredicte buida — en aquest cas, documenta explícitament per a aquella relació quina informació addicional caldria per prendre la decisió.

## Notes de manteniment

- **No és codi de producció**: els fitxers a `plans/outputs/` no s'importen ni s'executen en cap flux de producció.
- **Pla 044 (si es crea)**: depèn de les conclusions d'aquest spike. Les relacions marcades VIABLE aquí es convertiran en plans d'implementació. Suggeriment d'estructura: un pla per B→C LOE (pdfplumber, esforç alt) i un pla per C→D ficha_url enrichment (modificació a `build_ciclos_index`, esforç baix).
- **Dades de C LOMLOE**: si el ministeri afegeix en el futur una font oficial (API o portal nou) per a C LOMLOE, revisar les conclusions de la SEC 3 d'aquest spike.
- **ciclos_fp.json i el num mòdul**: `fetch_ciclos_fp` actual NO extreu el número de mòdul de la cel·la "Mòdul". Si la SEC 5 confirma que el match és viable, `fetch_ciclos_fp` ha d'ampliar el dict de cada cicle per incloure `'modul_num': str` (ex: `'3006'`), parsejant la cel·la 2 amb `re.search(r'^(\d{4})\s*-', cel·la2)`.
