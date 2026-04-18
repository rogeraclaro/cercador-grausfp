# Phase 1: Project Setup - Research

**Researched:** 2026-04-16
**Domain:** Python project scaffolding — Flask + estructura de directoris + fitxers de configuració
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** La carpeta arrel `fp-cercador/` es crea dins del directori actual (`Cercador Graus/`). Estructura final: `Cercador Graus/fp-cercador/backend/` + `Cercador Graus/fp-cercador/frontend/`
- **D-02:** `backend/` té les subcarpetes `scrapers/` i `data/`, a més de `app.py`, `requirements.txt` i `.env.example` directament
- **D-03:** `frontend/` conté `index.html` i `admin.html`
- **D-04:** `app.py` és un stub mínim: importa Flask, flask_cors i dotenv; crea l'app amb `CORS(app)`; inclou `if __name__ == '__main__': app.run(debug=True)`. Sense cap ruta — les rutes es fan a la Fase 4
- **D-05:** `index.html` i `admin.html` a `frontend/` són HTML vàlids estructurats (DOCTYPE, `<html lang="ca">`, `<head>` amb charset i title, `<body>` buit amb comentari `<!-- TODO: Phase 5/6 -->`). No són fitxers buits de 0 bytes
- **D-06:** S'inclouen **ambdós**: `.env.example` (dins `backend/`) i `README.md` (a l'arrel de `fp-cercador/`)
- **D-07:** `.env.example` conté: `ADMIN_TOKEN=canvia-aquest-token-per-un-de-segur`
- **D-08:** `README.md` és mínim: nom del projecte, descripció breu, i passos de setup (cp .env.example .env → editar ADMIN_TOKEN → pip install → python app.py). Sense seccions de docs extenses
- **D-09:** `backend/data/ofertes.json` **s'inclou al repositori** (NO s'exclou del .gitignore). Conté ~5-10 registres de mostra representatius dels 5 Grados
- **D-10:** `.gitignore` exclou: `.env`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `.Python`, `venv/`, `.venv/`, `*.egg-info/`

### Claude's Discretion
- Estructura exacta del `.gitignore` (entrades concretes per Python/venv)
- Contingut exacte dels registres de mostra a `ofertes.json` (5-10 registres representatius dels 5 Grados)
- Títol exacte del README

### Deferred Ideas (OUT OF SCOPE)
Cap — la discussió es va mantenir dins de l'abast de la fase.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROJ-01 | Estructura de directoris `fp-cercador/backend/` i `fp-cercador/frontend/` amb tots els fitxers necessaris | Decisions D-01 a D-05 especifiquen exactament quins fitxers cal crear i amb quin contingut mínim |
| PROJ-02 | `.gitignore` exclou `.env`, cache Python (ofertes.json NO s'exclou per D-09) | Decisió D-10 lista les entrades exactes del `.gitignore` |
| PROJ-03 | `requirements.txt` conté: flask, flask-cors, pdfplumber, requests, beautifulsoup4, python-dotenv | Versions verificades al registre PyPI (Step 3 d'aquest document) |
</phase_requirements>

---

## Summary

Aquesta fase és de creació de fitxers purs: cap instal·lació de paquets nous, cap execució de codi, cap lògica de negoci. El resultat és un esquelet de repositori complet que un desenvolupador pot clonar, instal·lar les dependències amb un sol comandament, i arrencar el servidor Flask sense cap configuració addicional (llevat de definir `ADMIN_TOKEN`).

Totes les decisions estan tancades al CONTEXT.md. L'únic espai de discreció del planificador és el contingut exacte dels registres de mostra a `ofertes.json` i les entrades addicionals del `.gitignore` més enllà de les obligatòries.

La fase no té dependències externes ni riscos tècnics: Python 3.13 i pip 26.0 estan disponibles al sistema, i tots els paquets requerits existeixen al registre PyPI amb versions estables recents.

**Recomanació principal:** Crear tots els fitxers en una seqüència única i ordenada (estructura de directoris → fitxers de configuració → stubs de codi → dades de mostra), verificar amb un `pip install --dry-run` i un `python -c "import app"`.

## Architectural Responsibility Map

| Capacitat | Capa primària | Capa secundària | Racional |
|-----------|--------------|-----------------|----------|
| Estructura de directoris | Sistema de fitxers | — | Creació directa; no hi ha capa d'abstracció |
| Dependències Python | Backend (pip/requirements.txt) | — | Gestió estàndard de paquets Python |
| Configuració de secrets | Backend (.env / .env.example) | — | `ADMIN_TOKEN` és un secret de servidor; mai al frontend |
| Stubs HTML inicials | Frontend (static) | — | Fitxers HTML estàtics; sense servidor necessari en fase 1 |
| Dades de mostra | Backend (data/ofertes.json) | Frontend (lectura futura) | L'API (Fase 4) servirà aquest fitxer; el frontend (Fase 5) el consumirà |

## Standard Stack

### Core
| Biblioteca | Versió actual | Propòsit | Per què és estàndard |
|------------|--------------|----------|----------------------|
| flask | 3.1.3 | Framework web WSGI lleuger | Estàndard de facto per APIs Python petites-mitjanes |
| flask-cors | 6.0.2 | Capçaleres CORS per Flask | Extensió oficial; zero configuració per a `origins="*"` |
| pdfplumber | 0.11.9 | Extracció de text/taules de PDFs | Millor precisió que PyPDF2 per a PDFs amb taules; Fase 2 |
| requests | 2.32.5 | HTTP client | Biblioteca HTTP Python per excel·lència |
| beautifulsoup4 | 4.14.3 | Parsing HTML | Estàndard per a scraping; Fase 3 |
| python-dotenv | 1.2.2 | Carrega `.env` a variables d'entorn | Patró universal per a secrets en Flask |

**Verificació de versions:** [VERIFIED: pip3 index versions — 2026-04-16]

### Instal·lació
```bash
pip install flask flask-cors pdfplumber requests beautifulsoup4 python-dotenv
```

### Paquets ja instal·lats al sistema
- `flask` 3.1.3 — JA INSTAL·LAT [VERIFIED: pip3 show]
- `requests` 2.32.5 — JA INSTAL·LAT [VERIFIED: pip3 show]
- `flask-cors`, `pdfplumber`, `python-dotenv`, `beautifulsoup4` — no instal·lats [VERIFIED: pip3 show]

## Architecture Patterns

### Diagrama de flux de la fase

```
Directori de treball: Cercador Graus/
└── fp-cercador/                   ← arrel del projecte
    ├── README.md                   ← documentació setup
    ├── .gitignore                  ← exclou .env i cache Python
    ├── backend/
    │   ├── app.py                  ← stub Flask (sense rutes)
    │   ├── requirements.txt        ← 6 dependències declarades
    │   ├── .env.example            ← plantilla de secrets
    │   ├── scrapers/               ← buit ara; Fases 2-3 el popularan
    │   └── data/
    │       └── ofertes.json        ← ~10 registres de mostra (5 Grados)
    └── frontend/
        ├── index.html              ← stub HTML vàlid (Fase 5)
        └── admin.html              ← stub HTML vàlid (Fase 6)
```

### Pattern 1: Flask app stub mínim

**Què:** Aplicació Flask mínima que inicialitza CORS i carrega dotenv, sense cap ruta definida.
**Quan usar:** Primera fase d'un projecte Flask multi-fase; les rutes es reserven per a fases posteriors.

```python
# Source: Decisions D-04 i D-05 del CONTEXT.md + patró estàndard Flask/python-dotenv
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

if __name__ == '__main__':
    app.run(debug=True)
```

**Nota important:** `load_dotenv()` ha d'anar **abans** de qualsevol `os.getenv()` per tal que les fases posteriors puguin llegir `ADMIN_TOKEN`. [ASSUMED: ordre de càrrega — però és el comportament documentat de python-dotenv]

### Pattern 2: Estructura del requirements.txt

**Què:** Declaració de dependències sense fixar versions patch, per facilitar `pip install` net.
**Quan usar:** Projectes nous sense necessitats de reproducibilitat exacta.

```
flask
flask-cors
pdfplumber
requests
beautifulsoup4
python-dotenv
```

**Alternativa considerada:** Fixar versions exactes (`flask==3.1.3`). Per a un projecte de desplegament en VPS, fixar versions garanteix reproducibilitat. Si el propietari vol reproduïbilitat exacta, cal `pip freeze > requirements.txt` un cop instal·lat. [ASSUMED: la preferència del propietari és la llista simple sense versions — no s'ha confirmat explícitament]

### Pattern 3: Schema de ofertes.json

El schema derivat dels requisits DATA-01 (REQUIREMENTS.md) és:

```json
[
  {
    "id": 1,
    "grado": "A",
    "nivel": 2,
    "familia": "Electricitat i Electrònica",
    "codigo": "ELEE0209",
    "denominacion": "Muntatge i manteniment d'instal·lacions elèctriques de baixa tensió",
    "plan_antiguo": false,
    "observaciones": ""
  }
]
```

Els registres de mostra han de cobrir els 5 Grados. Per als Grados D i E, `codigo` és `null` i `plan_antiguo` és `false`. Per al Grado E, `nivel` és `null`. [ASSUMED: valors null per a Grado D/E — confirmat per HTML-06 dels requisits]

### Anti-patrons a evitar
- **`.env` al repositori:** Mai cometre el fitxer `.env` real. Només `.env.example` va al git.
- **`debug=True` en producció:** El stub inclou `debug=True` per a desenvolupament. En desplegament CloudPanel, cal usar Gunicorn/uWSGI, no `app.run()`.
- **Rutes a `app.py` en fase 1:** La decisió D-04 és explícita: cap ruta fins a la Fase 4.
- **`ofertes.json` buit:** Ha de contenir registres vàlids de mostra (D-09), no un array buit `[]`.

## Don't Hand-Roll

| Problema | No construeixis | Usa en comptes | Per què |
|----------|----------------|----------------|---------|
| CORS headers | Middleware manual | `flask-cors` | Gestiona preflight, wildcards, credencials correctament |
| Càrrega de `.env` | Parsing manual del fitxer | `python-dotenv` | Gestiona quotes, comentaris, variables d'entorn del sistema |
| Parsing HTML | Regex sobre strings HTML | `beautifulsoup4` | Regex trenca amb HTML mal format; BS4 és tolerant |
| Extracció de PDFs | `pdfminer` directa | `pdfplumber` | API de nivell superior; millor per a taules multi-columna |

## Common Pitfalls

### Pitfall 1: `scrapers/` no inicialitzat com a paquet Python
**Què passa malament:** La carpeta `scrapers/` existeix però no té `__init__.py`. Les fases posteriors no podran fer `from scrapers.pdf_scraper import ...`.
**Per què passa:** En crear directoris purs, es pot oblidar el fitxer marcador.
**Com evitar-ho:** Crear `scrapers/__init__.py` (pot estar buit) en fase 1.
**Senyal d'alerta:** `ModuleNotFoundError: No module named 'scrapers'` a la Fase 2.

### Pitfall 2: Ordre de `load_dotenv()` a `app.py`
**Què passa malament:** Si `load_dotenv()` es crida després d'accedir a `os.getenv('ADMIN_TOKEN')`, el token serà `None`.
**Per què passa:** python-dotenv no modifica variables ja definides per defecte.
**Com evitar-ho:** Cridar `load_dotenv()` al principi de `app.py`, abans de qualsevol `os.getenv()`.

### Pitfall 3: `ofertes.json` amb schema incorrecte
**Què passa malament:** Els registres de mostra tenen camps que no coincideixen amb el schema real (DATA-01). El frontend de la Fase 5 fallarà en renderitzar.
**Per què passa:** Es crea el JSON manualment sense referència al schema.
**Com evitar-ho:** Verificar que cada registre de mostra té exactament: `id`, `grado`, `nivel`, `familia`, `codigo`, `denominacion`, `plan_antiguo`, `observaciones`.

### Pitfall 4: `.gitignore` no ignora `data/` ni PDFs temporals
**Què passa malament:** Quan la Fase 2 descarregui els PDFs dins de `backend/data/`, es commitejaran accidentalment (mida ~10-30MB cadascun).
**Per què passa:** `.gitignore` de Fase 1 no anticipa els artefactes de les fases posteriors.
**Com evitar-ho:** Afegir `backend/data/*.pdf` o `*.pdf` al `.gitignore` en fase 1.

## Code Examples

### .gitignore complet recomanat
```gitignore
# Secrets — mai al repositori
.env

# Cache Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Entorns virtuals
venv/
.venv/
env/
.env.bak

# Paquets instal·lats
*.egg-info/
dist/
build/

# PDFs descarregats (artefactes de Fase 2-3, poden ser grans)
*.pdf

# IDE
.DS_Store
.idea/
.vscode/
```

**Nota:** `ofertes.json` NO s'exclou (D-09 — inclòs al repositori amb dades de mostra).

### Registres de mostra per a ofertes.json (cobertura dels 5 Grados)
```json
[
  {
    "id": 1,
    "grado": "A",
    "nivel": 1,
    "familia": "Administració i Gestió",
    "codigo": "ADGG0108",
    "denominacion": "Operacions auxiliars de serveis administratius i generals",
    "plan_antiguo": false,
    "observaciones": ""
  },
  {
    "id": 2,
    "grado": "B",
    "nivel": 2,
    "familia": "Informàtica i Comunicacions",
    "codigo": "IFCT0209",
    "denominacion": "Sistemes microinformàtics",
    "plan_antiguo": false,
    "observaciones": ""
  },
  {
    "id": 3,
    "grado": "C",
    "nivel": 3,
    "familia": "Sanitat",
    "codigo": "SANT0208",
    "denominacion": "Atenció sanitària",
    "plan_antiguo": true,
    "observaciones": "(Plan antiguo)"
  },
  {
    "id": 4,
    "grado": "D",
    "nivel": 1,
    "familia": "Agrària",
    "codigo": null,
    "denominacion": "Agrojardineria i composicions florals",
    "plan_antiguo": false,
    "observaciones": ""
  },
  {
    "id": 5,
    "grado": "D",
    "nivel": 2,
    "familia": "Electricitat i Electrònica",
    "codigo": null,
    "denominacion": "Instal·lacions elèctriques i automàtiques",
    "plan_antiguo": false,
    "observaciones": ""
  },
  {
    "id": 6,
    "grado": "D",
    "nivel": 3,
    "familia": "Informàtica i Comunicacions",
    "codigo": null,
    "denominacion": "Administració de sistemes informàtics en xarxa",
    "plan_antiguo": false,
    "observaciones": ""
  },
  {
    "id": 7,
    "grado": "E",
    "nivel": null,
    "familia": "Sanitat",
    "codigo": null,
    "denominacion": "Audiologia protèsica",
    "plan_antiguo": false,
    "observaciones": ""
  }
]
```

## State of the Art

| Pràctica antiga | Pràctica actual | Canvi | Impacte |
|----------------|-----------------|-------|---------|
| `python manage.py startproject` (Django) | Estructura manual per a Flask | Flask no imposa estructura | Cal crear les carpetes a mà |
| `from flask_cors import CORS; CORS(app, resources={...})` | `CORS(app)` per a origins wildcard | flask-cors 4+ simplifica l'API | Menys configuració per a dev |
| `app.config['SECRET_KEY'] = os.environ.get(...)` | `load_dotenv()` + `os.getenv()` | python-dotenv és l'estàndard | `.env` separat del codi |

## Assumptions Log

| # | Afirmació | Secció | Risc si és incorrecte |
|---|-----------|--------|----------------------|
| A1 | `requirements.txt` sense versions fixades és la preferència del propietari | Standard Stack | Si vol reproducibilitat exacta, cal `pip freeze`; fàcil de corregir |
| A2 | `load_dotenv()` abans de `os.getenv()` és el comportament documentat | Pattern 1 | Molt baix — és el comportament oficial de python-dotenv |
| A3 | `scrapers/__init__.py` buit és suficient per fer el paquet importable | Pitfall 1 | Molt baix — comportament estàndard de Python |

## Open Questions

1. **Versions fixes vs. llista simple al requirements.txt**
   - Què sabem: les decisions no especifiquen si cal fixar versions
   - Què no està clar: si el VPS de desplegament necessita reproducibilitat exacta
   - Recomanació: Usar llista simple ara; afegir versions exactes a la fase de desplegament si cal

2. **`scrapers/__init__.py` a fase 1 o fase 2**
   - Què sabem: la carpeta `scrapers/` es crea a fase 1, però el codi entra a fase 2
   - Recomanació: Crear `__init__.py` buit a fase 1 per evitar errors a fase 2

## Environment Availability

| Dependència | Requerida per | Disponible | Versió | Fallback |
|-------------|--------------|-----------|--------|---------|
| Python 3 | tot el backend | ✓ | 3.13.0 | — |
| pip | instal·lació de paquets | ✓ | 26.0.1 | — |
| flask | app.py stub | ✓ (ja instal·lat) | 3.1.3 | — |
| requests | requirements.txt | ✓ (ja instal·lat) | 2.32.5 | — |
| flask-cors | requirements.txt | ✗ (no instal·lat) | 6.0.2 al PyPI | `pip install flask-cors` |
| pdfplumber | requirements.txt | ✗ (no instal·lat) | 0.11.9 al PyPI | `pip install pdfplumber` |
| python-dotenv | requirements.txt | ✗ (no instal·lat) | 1.2.2 al PyPI | `pip install python-dotenv` |
| beautifulsoup4 | requirements.txt | ✗ (no instal·lat) | 4.14.3 al PyPI | `pip install beautifulsoup4` |

**Dependències absents sense fallback:** Cap — tots els paquets estan al PyPI i pip és funcional.

**Nota:** La fase 1 declara les dependències al `requirements.txt` però NO les instal·la. La instal·lació és responsabilitat del desenvolupador que clona el repositori. El planner no ha d'incloure `pip install` com a tasca d'aquesta fase.

## Validation Architecture

### Test Framework
| Propietat | Valor |
|-----------|-------|
| Framework | Cap — aquesta fase no té lògica de negoci que provar |
| Fitxer de config | — |
| Comandament ràpid | `python -c "from app import app; print('OK')"` (des de `backend/`) |
| Comandament complet | `python -c "import json; data=json.load(open('data/ofertes.json')); assert len(data) >= 5"` |

### Mapa de Requisits → Verificacions
| Req ID | Comportament | Tipus | Comandament | Fitxer existent? |
|--------|-------------|-------|-------------|-----------------|
| PROJ-01 | Estructura de directoris completa | smoke | `ls fp-cercador/backend/ fp-cercador/frontend/` | ❌ Wave 0 |
| PROJ-02 | `.gitignore` exclou `.env` | smoke | `grep '\.env' fp-cercador/.gitignore` | ❌ Wave 0 |
| PROJ-03 | `requirements.txt` conté 6 deps | smoke | `grep -c '' fp-cercador/backend/requirements.txt` (ha de retornar 6) | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] No hi ha infraestructura de tests — les verificacions d'aquesta fase són smoke tests de shell, no codi de test. El planner pot incloure-les com a passos de verificació manual o com a mini-script de validació.

*(Cap gap de framework — les verificacions de fase 1 no requereixen pytest ni cap framework)*

## Security Domain

### Categories ASVS aplicables

| Categoria ASVS | Aplica | Control estàndard |
|----------------|--------|------------------|
| V2 Autenticació | No (fase 1 no implementa auth) | — |
| V3 Gestió de sessions | No | — |
| V4 Control d'accés | No | — |
| V5 Validació d'entrada | No (cap endpoint en fase 1) | — |
| V6 Criptografia | No | — |

### Patrons de risc de seguretat per a aquesta fase

| Patró | STRIDE | Mitigació estàndard |
|-------|--------|---------------------|
| Secret en repositori | Divulgació d'informació | `.env` a `.gitignore`; `.env.example` sense valors reals |
| `debug=True` en producció | Divulgació d'informació | Només per a dev; CloudPanel usa Gunicorn (Fase de desplegament) |

**Nota clau:** El risc principal de seguretat en aquesta fase és cometre accidentalment el fitxer `.env` real. El `.gitignore` és la mitigació crítica (PROJ-02).

## Sources

### Primary (HIGH confidence)
- `pip3 index versions flask flask-cors pdfplumber requests beautifulsoup4 python-dotenv` — versions verificades al registre PyPI [VERIFIED: 2026-04-16]
- `pip3 show flask requests` — paquets ja instal·lats verificats [VERIFIED: 2026-04-16]
- `.planning/phases/01-project-setup/01-CONTEXT.md` — decisions D-01 a D-10 tancades [VERIFIED: llegit]
- `.planning/REQUIREMENTS.md` — schema DATA-01, requirements PROJ-01/02/03 [VERIFIED: llegit]

### Secondary (MEDIUM confidence)
- Patró `load_dotenv()` + `os.getenv()` — documentació oficial python-dotenv [ASSUMED basat en coneixement d'entrenament, comportament àmpliament documentat]

## Metadata

**Breakdown de confiança:**
- Stack estàndard: HIGH — versions verificades al PyPI en temps real
- Arquitectura: HIGH — decisions tancades al CONTEXT.md; cap ambigüitat
- Pitfalls: MEDIUM — basats en experiència comuna amb Flask + python-dotenv; A2/A3 marcats com ASSUMED

**Data de recerca:** 2026-04-16
**Vàlid fins:** 2026-05-16 (paquets PyPI estables; decisions del CONTEXT.md no expiren)
