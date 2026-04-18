# Fase 1: Project Setup - Mapa de Patrons

**Mapejat:** 2026-04-16
**Fitxers analitzats:** 10 (fitxers nous a crear)
**Analògics trobats:** 0 / 10 — projecte de zero, cap codi existent al repositori

> **Nota important:** El repositori `fp-cercador/` no existeix encara. No hi ha cap fitxer de codi existent
> que pugui servir d'analògic real. Tots els patrons provenen de les especificacions tancades al
> CONTEXT.md + RESEARCH.md i de les convencions estàndard de l'stack (Flask + python-dotenv + flask-cors).

---

## Classificació de Fitxers

| Fitxer nou | Rol | Flux de dades | Analògic més proper | Qualitat |
|------------|-----|---------------|---------------------|----------|
| `fp-cercador/backend/app.py` | config / entry-point | request-response (stub) | cap — patró extret de RESEARCH.md Pattern 1 | referència |
| `fp-cercador/backend/requirements.txt` | config | — | cap — llista plana estàndard pip | referència |
| `fp-cercador/backend/.env.example` | config | — | cap — fitxer de plantilla estàndard | referència |
| `fp-cercador/backend/data/ofertes.json` | model / dades | batch (lectura futura per API) | cap — schema definit a DATA-01 | referència |
| `fp-cercador/backend/scrapers/__init__.py` | config | — | cap — fitxer marcador Python buit | referència |
| `fp-cercador/frontend/index.html` | component (stub) | — | cap — HTML vàlid mínim | referència |
| `fp-cercador/frontend/admin.html` | component (stub) | — | cap — HTML vàlid mínim | referència |
| `fp-cercador/README.md` | docs | — | cap — README mínim estàndard | referència |
| `fp-cercador/.gitignore` | config | — | cap — .gitignore Python estàndard | referència |
| `fp-cercador/backend/data/` (directori) | — | — | cap | — |

---

## Assignació de Patrons

### `fp-cercador/backend/app.py` (config, entry-point)

**Analògic:** cap fitxer existent — patró extret de RESEARCH.md § Pattern 1 + decisions D-04/D-05

**Patró d'importació i inicialització** (RESEARCH.md línies 117-130):
```python
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

if __name__ == '__main__':
    app.run(debug=True)
```

**Restriccions crítiques:**
- `load_dotenv()` ha d'anar **abans** de qualsevol `os.getenv()` (RESEARCH.md Pitfall 2)
- **Cap ruta** en aquesta fase (decisió D-04) — les rutes van a la Fase 4
- `CORS(app)` sense arguments addicionals — wildcard per a dev (RESEARCH.md State of the Art)

**Anti-patrons a evitar:**
- No afegir `app.config['SECRET_KEY']` ni cap ruta `@app.route(...)` — fora d'abast
- No cridar `os.getenv('ADMIN_TOKEN')` al stub — no hi ha res que el requereixi en fase 1

---

### `fp-cercador/backend/requirements.txt` (config)

**Analògic:** cap fitxer existent — llista estàndard pip sense versions fixes (RESEARCH.md Pattern 2 + PROJ-03)

**Patró del fitxer** (RESEARCH.md línies 139-146):
```
flask
flask-cors
pdfplumber
requests
beautifulsoup4
python-dotenv
```

**Restriccions crítiques:**
- Exactament 6 línies, una dependència per línia (PROJ-03)
- Sense versions fixes (`flask==3.1.3`) — llista simple per a instal·lació neta (RESEARCH.md A1)
- Sense comentaris ni línies buides — facilita `grep -c ''` per a la verificació de smoke test

---

### `fp-cercador/backend/.env.example` (config)

**Analògic:** cap fitxer existent — plantilla estàndard python-dotenv (decisió D-07)

**Patró del fitxer** (CONTEXT.md D-07):
```
ADMIN_TOKEN=canvia-aquest-token-per-un-de-segur
```

**Restriccions crítiques:**
- Una sola línia — l'única variable de configuració de fase 1
- Valor placeholder llegible que indiqui clarament que cal canviar-lo
- Mai posar un token real (RESEARCH.md Security Domain)

---

### `fp-cercador/backend/data/ofertes.json` (model, batch)

**Analògic:** cap fitxer existent — schema definit a DATA-01 (REQUIREMENTS.md línia 34) + RESEARCH.md Pattern 3

**Patró del schema** (RESEARCH.md línia 155-167):
```json
{
  "id": 1,
  "grado": "A",
  "nivel": 1,
  "familia": "Administració i Gestió",
  "codigo": "ADGG0108",
  "denominacion": "Operacions auxiliars de serveis administratius i generals",
  "plan_antiguo": false,
  "observaciones": ""
}
```

**Camps obligatoris (tots els registres):** `id`, `grado`, `nivel`, `familia`, `codigo`, `denominacion`, `plan_antiguo`, `observaciones`

**Valors especials per Grado:**
- Grado D: `"codigo": null`, `"plan_antiguo": false`
- Grado E: `"codigo": null`, `"nivel": null`, `"plan_antiguo": false`
- Grado C (plan antic): `"plan_antiguo": true`, `"observaciones": "(Plan antiguo)"`

**Cobertura mínima:** 1 registre per cada Grado (A, B, C, D, E) — mínim 5, recomanat ~10 (decisió D-09)

**Registres de mostra complets** (RESEARCH.md línies 248-319) — 7 registres que cobreixen els 5 Grados:
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

**Restriccions crítiques:**
- Array JSON vàlid (no buit — decisió D-09 i RESEARCH.md Pitfall 3)
- IDs correlatius i únics (DATA-02)
- NO excloure del .gitignore (decisió D-09)

---

### `fp-cercador/backend/scrapers/__init__.py` (config)

**Analògic:** cap fitxer existent — fitxer marcador de paquet Python estàndard (RESEARCH.md Pitfall 1)

**Patró del fitxer:** fitxer buit (0 bytes) o amb comentari mínim:
```python
# Paquet scrapers — contingut a la Fase 2
```

**Restriccions crítiques:**
- Ha d'existir per fer `scrapers/` importable com a paquet Python (RESEARCH.md Pitfall 1)
- Sense cap codi de lògica de negoci en fase 1

---

### `fp-cercador/frontend/index.html` (component stub)

**Analògic:** cap fitxer existent — HTML vàlid estructurat (decisió D-05)

**Patró de l'stub HTML** (CONTEXT.md D-05):
```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <title>Cercador FP España</title>
</head>
<body>
  <!-- TODO: Phase 5 -->
</body>
</html>
```

**Restriccions crítiques:**
- `lang="ca"` — idioma català (decisió D-05)
- `charset="UTF-8"` obligatori (caràcters catalans: `·`, `à`, `è`, `í`, etc.)
- No és un fitxer de 0 bytes (decisió D-05)
- Cap CSS ni JS en fase 1 — tot va a la Fase 5

---

### `fp-cercador/frontend/admin.html` (component stub)

**Analògic:** `fp-cercador/frontend/index.html` — mateix patró HTML, títol diferent (decisió D-05)

**Patró de l'stub HTML:**
```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <title>Cercador FP — Administració</title>
</head>
<body>
  <!-- TODO: Phase 6 -->
</body>
</html>
```

**Diferències respecte index.html:**
- Comentari `<!-- TODO: Phase 6 -->` (no Phase 5)
- Títol indica "Administració"

---

### `fp-cercador/README.md` (docs)

**Analògic:** cap fitxer existent — README mínim (decisió D-08)

**Patró de l'estructura** (CONTEXT.md D-08):
```markdown
# Cercador FP España

Cercador de l'oferta formativa del Sistema de Formació Professional espanyol (Grados A–E).

## Setup

1. Copia el fitxer d'exemple: `cp backend/.env.example backend/.env`
2. Edita `backend/.env` i assigna un valor segur a `ADMIN_TOKEN`
3. Instal·la les dependències: `pip install -r backend/requirements.txt`
4. Arrenca el servidor: `cd backend && python app.py`
```

**Restriccions crítiques:**
- Mínim — sense seccions de docs extenses (decisió D-08)
- Els 4 passos de setup han de ser en ordre lògic (cp → editar → pip install → python app.py)

---

### `fp-cercador/.gitignore` (config)

**Analògic:** cap fitxer existent — .gitignore Python estàndard (decisió D-10 + RESEARCH.md Code Examples)

**Patró complet** (RESEARCH.md línies 212-241):
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

**Restriccions crítiques:**
- `.env` exclòs (PROJ-02, RESEARCH.md Security Domain)
- `ofertes.json` NO exclòs (decisió D-09 explícita)
- `*.pdf` exclòs per anticipar artefactes de la Fase 2 (RESEARCH.md Pitfall 4)
- Les entrades obligatòries de D-10 han d'estar totes: `.env`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `.Python`, `venv/`, `.venv/`, `*.egg-info/`

---

## Patrons Compartits

### Estructura de directoris arrel

**Aplica a:** tots els fitxers de la fase
**Arrel:** `fp-cercador/` dins de `Cercador Graus/` (decisió D-01)

```
Cercador Graus/
└── fp-cercador/
    ├── README.md
    ├── .gitignore
    ├── backend/
    │   ├── app.py
    │   ├── requirements.txt
    │   ├── .env.example
    │   ├── scrapers/
    │   │   └── __init__.py
    │   └── data/
    │       └── ofertes.json
    └── frontend/
        ├── index.html
        └── admin.html
```

### Idioma i encoding

**Aplica a:** tots els fitxers HTML, README i JSON
- Fitxers HTML: `lang="ca"` + `charset="UTF-8"`
- JSON: UTF-8 sense BOM (caràcters `·`, `l·l`, accents catalans)
- README.md: redactat en català o castellà (CLAUDE.md del projecte no restringeix; CONTEXT.md usa català)

### Seguretat de secrets

**Font:** RESEARCH.md § Security Domain
**Aplica a:** `.gitignore`, `.env.example`

Regla única: el fitxer `.env` real mai al repositori. Només `.env.example` amb valors placeholder.

---

## Sense Analògic Trobat

Tots els fitxers d'aquesta fase no tenen analògic al codebase (projecte de zero):

| Fitxer | Rol | Flux de dades | Motiu |
|--------|-----|---------------|-------|
| `backend/app.py` | config / entry-point | request-response (stub) | Primer fitxer Flask del projecte |
| `backend/requirements.txt` | config | — | Primer projecte Python del repositori |
| `backend/.env.example` | config | — | Primer fitxer de secrets del projecte |
| `backend/data/ofertes.json` | model | batch | Primera dada del projecte |
| `backend/scrapers/__init__.py` | config | — | Primer paquet Python del projecte |
| `frontend/index.html` | component | — | Primer fitxer HTML del projecte |
| `frontend/admin.html` | component | — | Primer fitxer HTML del projecte |
| `README.md` | docs | — | Primera documentació del projecte |
| `.gitignore` | config | — | Primer .gitignore del projecte |

**El planificador ha d'usar els patrons de RESEARCH.md i els excerpts d'aquest document** en lloc d'analògics del codebase.

---

## Verificacions de Smoke Test

Per a cada fitxer creat, el planificador pot incloure aquestes verificacions (RESEARCH.md § Validation Architecture):

| Requisit | Comandament de verificació |
|----------|---------------------------|
| PROJ-01 estructura | `ls fp-cercador/backend/ fp-cercador/frontend/` |
| PROJ-02 .gitignore | `grep '\.env' fp-cercador/.gitignore` |
| PROJ-03 requirements (6 deps) | `grep -c '' fp-cercador/backend/requirements.txt` (ha de retornar 6) |
| app.py importable | `cd fp-cercador/backend && python -c "from app import app; print('OK')"` |
| ofertes.json vàlid i cobertura 5 Grados | `python -c "import json; d=json.load(open('fp-cercador/backend/data/ofertes.json')); grads=set(r['grado'] for r in d); assert grads=={'A','B','C','D','E'}, grads; print('OK')"` |

---

## Metadades

**Àmbit de cerca d'analògics:** `/Users/rogermasellas/AI/Cercador Graus/` (tot el repositori)
**Fitxers escanejats:** 3 (CLAUDE.md, prompt-fp-cercador.md, fitxers de .planning/) — cap fitxer de codi font existent
**Data d'extracció de patrons:** 2026-04-16
**Fonts primàries dels patrons:** CONTEXT.md decisions D-01 a D-10, RESEARCH.md Pattern 1-3, REQUIREMENTS.md DATA-01
