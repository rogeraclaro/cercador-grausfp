# Spike: Enriquiment Grado C amb el Buscador de Certificados de Profesionalidad

> **Data**: 2026-06-13  
> **Pla origen**: 013-spike-dades-extra-grado-c.md  
> **Peticions reals al servidor del ministeri**: 9 (ben per sota del límit de 10)

---

## Step 1: Cartografia de la font

**Buscador de Certificados de Profesionalidad**  
URL base: `https://www.todofp.es/buscadorcertificados/`

### Endpoints descoberts

| Endpoint | Mètode | Descripció |
|----------|--------|------------|
| `/buscador` | GET | Bootstrap — retorna cookie `__Host-todofp.es` (sense JSESSIONID) |
| `/busquedaCP` | POST | Cerca i llista paginada de certificats → HTML |
| `/fichaCP` | POST | Fitxa individual amb BOE, Annexe PDF, Europass → HTML |
| `/pdfCP` | POST | PDF de la fitxa (accés via `certificadoID`) |
| `/busquedaCentros` | GET | Centres on s'imparteix (`?codCertificado=ADGG0408`) |

### Paràmetres de `/busquedaCP` (POST)

```
limite      = 0          # offset de paginació
paso        = 10         # mida de pàgina (pot ser 600 per obtenir tot de cop)
total       = 0          # total de resultats (omple el servidor)
codigo      = ""         # codi exacte (ex: "ADGG0408")
denominacion= ""         # cerca per text lliure
familia     = "0"        # "0" = totes
nivel       = "0"        # "0" = tots (el filtre per nivel NO funciona: ignora el valor)
```

### Sessió/cookies

El patró és idèntic al de `buscador_scraper._bootstrap_session`, però **sense JSESSIONID**:
- `GET /buscador` → emmet cookie `__Host-todofp.es`
- Sessions POST reutilitzen aquesta cookie sense captcha

### Format de resposta

**HTML** (no JSON). Parsing amb BeautifulSoup. Exemple de fila:

```html
<tr>
  <form action="fichaCP" id="form-ficha-CP_112" method="post">
    <input name="certificadoID" value="112"/>   ← ID numèric intern
    ...
  </form>
  <td class="colCodigo"><a>ADGG0408</a></td>
  <td headers="columna-cuatro"><p>430 horas</p></td>
  <!-- icones: ficha, Ciclos FP, Dónde estudiar (sense URL directa) -->
</tr>
```

### Peticions necessàries per a cada escenari

| Camp | Peticions | Temps estimat |
|------|-----------|---------------|
| certID + duracion_horas (tots 584) | **1 POST** `paso=600` | ~2.5 s |
| url_anexo_pdf | **0** (URL derivable) | 0 s |
| url_europass_es / en | **0** (URL derivable) | 0 s |
| url_boe (per registre) | **584 POST** fichaCP | ~876 s (≈15 min) |
| centres (per registre) | **584 GET** busquedaCentros | ~876 s |

---

## Step 2: Mapeig de camps

### Camps disponibles per certificat

| Camp | Origen | Tipus | Exemple (ADGG0408) |
|------|--------|-------|--------------------|
| `duracion_horas` | busquedaCP (bulk) | INT | `430` |
| `cert_id_buscador` | busquedaCP (bulk) | INT | `112` |
| `url_boe` | fichaCP (individual) | STRING | `https://www.boe.es/eli/es/rd/2011/5/9/645` |
| `url_anexo_pdf` | **derivable** | STRING | `https://www.todofp.es/dam/todofp/certificados-profesionales/anexos/adgg0408.pdf` |
| `url_europass_es` | **derivable** | STRING | `https://www.todofp.es/dam/todofp/certificados-profesionales/europass/n1-adgg0408-es-pub.pdf` |
| `url_europass_en` | **derivable** | STRING | `https://www.todofp.es/dam/todofp/certificados-profesionales/europass/n1-adgg0408-in-pub.pdf` |
| Centres | busquedaCentros (individual) | HTML/nombre | (no extret en mostra) |

### Patrons d'URL derivables (verificats en 2 mostres: ADGG0408, COML0110)

```python
BASE = "https://www.todofp.es/dam/todofp/certificados-profesionales"
codigo_lc = codigo.lower()   # "adgg0408"
nivel_n   = str(nivel)       # "1", "2" o "3"

url_anexo_pdf    = f"{BASE}/anexos/{codigo_lc}.pdf"
url_europass_es  = f"{BASE}/europass/n{nivel_n}-{codigo_lc}-es-pub.pdf"
url_europass_en  = f"{BASE}/europass/n{nivel_n}-{codigo_lc}-in-pub.pdf"
```

> **Risc**: si todofp.es reorganitza els arxius DAM (JCR), els URLs trenquen sense avís.
> Mitigació: validar HEAD periòdicament contra 2-3 URLs de mostra.

### Clau de matching

**`codigo`** (string) és la clau única de creuament.

- El camp `ficha_id` que ja tenim a `buscador_scraper.py` prové del *Buscador de Graus FP* i és un ID diferent del `certificadoID` del *Buscador de Certificats*. No es pot usar per creuar.
- El `codigo` (LOE, p. ex. `ADGG0408`) és idèntic a ambdós sistemes.

### Taxa de matching (verificada)

| Conjunt | Total |
|---------|-------|
| Grado C al nostre pipeline | **981** |
| → plan_antiguo=True (LOE) | **584** |
| → plan_antiguo=False (nova llei 3/2022) | **397** |
| Buscador de Certificats (todofp.es) | **588** |
| **Matches exactes (codigo)** | **584 (100%)** |
| Al buscador però no en nosaltres | 4 (`FMEC0210`, `FMEC0110`, `SEAG0110`, `SEAG0212` — probablement derogats) |

**Conclusió crítica**: els 397 Grado C nous (codis `ADG_C_001_3B`, etc.) **no existeixen** al buscador de certificats. L'enriquiment cobreix únicament els 584 antics.

---

## Step 3: Estratègia d'integració recomanada

### Opcions analitzades

**(a) Enriquiment al pipeline (+1 petició bulk)**

- 1 POST `paso=600` → tots els `certID` + `duracion_horas` en ~2.5 s
- URLs `url_anexo_pdf` + `url_europass_es/en` derivades en memòria (0 peticions)
- BOE URL i Centres **no s'inclouen** (massa costós: 584 × ~1.5 s = ~876 s)
- Temps afegit al pipeline: **+2.5 s** (de ~4 s a ~6.5 s)
- Peticions afegides: **1**

**(b) Enriquiment on-demand** (`/api/certificado/<codigo>`)

- Backend fa POST a `fichaCP` quan l'usuari obre el detall del certificat
- Retorna en una sola resposta: BOE URL, Annexe PDF, Europass, Centres
- Latència per usuari: ~1-2 s per primera consulta
- Peticions al pipeline: **0**

**(c) Pipeline separat mensual**

- Cron job nocturn: 584 POST a `fichaCP` → emmagatzema a `certificados_enriched.json`
- Temps execució: ~876 s (~15 min) — acceptable per a un job mensual
- Cost al pipeline habitual: **0**
- Complexitat afegida: un nou component (cron + fitxer addicional)

### Recomanació: **Híbrid A + B**

```
Al pipeline (Estratègia A):
  1 POST bulk → certID + duracion_horas (584 registres, 2.5 s)
  + calcul en memòria → url_anexo_pdf, url_europass_es, url_europass_en
  Cost addicional: +1 petició, +2.5 s

On-demand (Estratègia B):
  GET /api/certificado/<codigo>
  → fa POST a fichaCP del ministeri (~1.5 s)
  → retorna url_boe + centres (a demanda, quan l'usuari clica)
```

**Justificació**: la `duracion_horas` i els PDFs Europass/Annexe són dades d'alta utilitat per mostrar a la llista (no cal clic extra). El BOE URL i els Centres no es mostren a la llista general i justifiquen la latència on-demand. El cost de +2.5 s al pipeline és negligible en un refresh setmanal en background.

---

## Step 4: Impacte al model de dades i la UI

### Camps nous a `ofertes.json` (només per `grado='C'` i `plan_antiguo=True`)

```json
{
  "codigo": "ADGG0408",
  "grado": "C",
  "plan_antiguo": true,
  "nivel": 1,
  "duracion_horas": 430,
  "cert_id_buscador": 112,
  "url_anexo_pdf": "https://www.todofp.es/dam/todofp/certificados-profesionales/anexos/adgg0408.pdf",
  "url_europass_es": "https://www.todofp.es/dam/todofp/certificados-profesionales/europass/n1-adgg0408-es-pub.pdf",
  "url_europass_en": "https://www.todofp.es/dam/todofp/certificados-profesionales/europass/n1-adgg0408-in-pub.pdf"
}
```

Per als 397 Grado C nous i tots els Grado A/B/D/E, tots els camps nous = `null`.

### Impacte en mida

| Mètrica | Valor |
|---------|-------|
| Mida actual `ofertes.json` | **3.647 KB** |
| Delta per registre enriquit | +376 B |
| Delta total (584 registres) | **+214 KB** |
| Mida estimada post-enriquiment | **~3.861 KB (+5.9%)** |

Amb la compressió gzip actual, l'impacte real a la xarxa és ~60-70 KB addicionals.

### UI a `index.html`

El codi ja té un tractament especial per a `row.grado === 'C' && row.plan_antiguo` (línies 834–845). Les opcions per mostrar les dades noves:

1. **Fila expandible** (acordió): clic a la fila obre un panell amb durada + botons PDF/Europass. Millor UX, no afecta densitat de la llista.
2. **Columna nova "Durada"**: visible a la llista per als Grado C antics. Senzill, però afegeix complexitat a la taula (columna quasi buida per als nous).
3. **Tooltip/popover** sobre les icones existents: reutilitza el patró visual actual dels Grado A/B.

**Recomanació UI**: fila expandible (acordió), consistent amb l'accordion que ja usa todofp.es per als Centres.

---

## Step 5: Riscos i preguntes obertes

### Riscos tècnics

| Risc | Probabilitat | Impacte | Mitigació |
|------|-------------|---------|-----------|
| todofp.es migra el buscador de certificats a JS-render (SPA) | Baixa | Alt (scraping trenca) | Monitorar el buscador periòdicament; el patró HTML és estable des de ~2015 |
| Reorganització de paths DAM (`/dam/todofp/...`) | Baixa-Mitjana | Mig (URLs derivades trenquen silenciosament) | HEAD check mensual a 5 URLs de mostra |
| Canvi en el formulari POST (nous camps obligatoris) | Molt baixa | Alt | Idèntic a risc del scraper actual de graus |
| El servidor retorna 429 si es fan moltes peticions | Desconeguda | Alt per estratègies B/C bulk | Limitar a 1 req/s amb `time.sleep(1)` per als on-demand |
| Inconsistència de dades: els 4 codis extra (FMEC*, SEAG*) | Ara baixa | Baix | Ignorar-los; probablement derogats o retallats |

### Qüestions obertes per al propietari

1. **Valor del BOE URL** per a l'usuari final: és prou important per justificar l'endpoint on-demand? O n'hi ha prou amb l'Annexe PDF?
2. **Centres**: mostrar el nombre de centres on s'imparteix cada certificat és un valor diferencial fort, però requereix 584 peticions individuals (estratègia C). Es vol fer?
3. **Grado C nous (397)**: mai tindran fitxa al buscador de certificats. Es vol comunicar d'alguna manera que les dades extra no estan disponibles per als nous?
4. **Freqüència de refresh**: si s'afegeix l'enriquiment al pipeline, el refresh setmanal segueix essent adequat?

---

## Conclusió

**Viabilitat**: ✅ Alta. El buscador de certificats és accessible amb el mateix patró de cookies que el buscador de graus, retorna HTML parsejable, i el matching per `codigo` és del 100% per als 584 Grado C LOE.

**Recomanació**: Implementar l'estratègia **A+B híbrid**:
- Pipeline: +1 petició (+2.5 s) → `duracion_horas` + `cert_id_buscador` + 3 URLs derivades
- On-demand: nou endpoint `/api/certificado/<codigo>` per a BOE URL + Centres quan l'usuari vol el detall

**Pas següent si es decideix implementar**: crear un pla de construcció nou que cobreixi:
1. Scraper nou `certificados_scraper.py` (mòdul independent, segueix patró de `buscador_scraper`)
2. Integració al pipeline (`pipeline.py`)
3. Endpoint `/api/certificado/<codigo>` al backend Flask
4. UI: component d'expansió a `index.html` per a Grado C antics
