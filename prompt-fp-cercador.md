# Prompt per a Claude Code: Cercador FP España

## Projecte

App web amb backend Flask (Python) + frontend estàtic (HTML/CSS/JS vanilla) per cercar l'oferta formativa del Sistema de Formació Professional espanyol (Llei Orgànica 3/2022), cobrint tots els Grados A, B, C, D i E.

Es desplegarà en un VPS amb CloudPanel (Ubuntu 24.04).

---

## Estructura de fitxers

```
fp-cercador/
├── backend/
│   ├── app.py                  # Flask app principal
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── parse_pdfs.py       # Extracció Grados A, B, C des de PDFs
│   │   └── scrape_html.py      # Scraping Grados D, E des de HTML
│   ├── data/
│   │   └── ofertes.json        # Generat pel scraper, servit al frontend
│   ├── requirements.txt
│   └── .env                    # ADMIN_TOKEN secret
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

---

## Fonts de dades

### Grados A, B, C → 3 PDFs oficials del Ministeri

Descarrega'ls amb `requests` durant el scraping (no estan inclosos al repositori).

URLs:
- Grado A: `https://todofp.es/dam/jcr:a8580dd0-8106-4387-ae2a-8c6c1f23fa91/catalogo-grados-a.pdf`
- Grado B: `https://todofp.es/dam/jcr:fbe95da3-7507-458a-ab0d-4202beea8d28/catalogo-grados-b.pdf`
- Grado C: `https://todofp.es/dam/jcr:8b85fd78-c6d5-406f-ade8-891abd96613f/catalogo-grados-c.pdf`

Headers obligatoris per descarregar:
```python
headers = {
    "Referer": "https://todofp.es/catalogos-registros-sistema-fp/catalogo-nacional-ofertas-sistema.html",
    "User-Agent": "Mozilla/5.0"
}
```

**Estructura interna dels PDFs** (text natiu, no escanejat, llegible amb `pdfplumber`):
- Pàgines 1–5: portada i introducció → ignorar
- Resta de pàgines: taules amb 3 columnes: `Código`, `Denominación`, `Observaciones`
- Les taules estan agrupades per **Família Professional** (capçaleres de secció entre taules)
- Dins de cada família, les taules estan separades per **Nivell**
- El nivell és deduïble del sufix del codi: `_3B` → Nivell 1, `_4B` → Nivell 2, `_5B` → Nivell 3
- Codis de pla antic: format `XXXN0000NN` seguits de ` (Plan antiguo)` en la columna Observaciones o al codi mateix → marcar `plan_antiguo: true`

Famílies professionals presents als PDFs A/B/C:
Actividades Físicas y Deportivas, Administración y Gestión, Agraria, Artes Gráficas, Artes y Artesanías, Comercio y Marketing, Competencias Transversales, Edificación y Obra Civil, Electricidad y Electrónica, Energía y Agua, Fabricación Mecánica, Hostelería y Turismo, Imagen Personal, Imagen y Sonido, Industrias Alimentarias, Industrias Extractivas, Informática y Comunicaciones, Instalación y Mantenimiento, Inteligencia Artificial y Data, Madera Mueble y Corcho, Mantenimiento y Servicios a la Producción, Marítimo-Pesquera, Química, Sanidad, Seguridad y Medio Ambiente, Servicios Socioculturales y a la Comunidad, Textil Confección y Piel, Transporte y Mantenimiento de Vehículos, Vidrio y Cerámica.

---

### Grados D → 3 pàgines HTML (scraping directe, sense captcha)

| Subtipus | Títols aprox. | URL |
|---|---|---|
| Grado Básico | 34 | `https://todofp.es/que-estudiar/grados-d/fp-grado-basico.html` |
| Grado Medio | 67 | `https://todofp.es/que-estudiar/grados-d/grado-medio.html` |
| Grado Superior | 94 | `https://todofp.es/que-estudiar/grados-d/grado-superior.html` |

**Estructura HTML confirmada:** els títols estan en elements amb atribut `id="tit-*"`. Exemple real:
```html
<span id="tit-actividades-ecuestres">Técnico en Actividades Ecuestres</span>
```
La família professional s'infereix de la secció on apareix cada títol (hi ha capçaleres de secció entre grups de títols). El nivell s'assigna per subtipus: Básico → 1, Medio → 2, Superior → 3.

---

### Grado E → 1 pàgina HTML

| Subtipus | Títols aprox. | URL |
|---|---|---|
| Cursos d'Especialització | 36 | `https://todofp.es/que-estudiar/grados-e/curso-especializacion.html` |

Mateixa estructura HTML que Grado D. El camp `nivel` serà `null` per a Grado E.

---

## Schema del JSON generat (`data/ofertes.json`)

Array d'objectes JSON amb aquest format:

```json
[
  {
    "id": 1,
    "grado": "C",
    "nivel": 2,
    "familia": "Informática y Comunicaciones",
    "codigo": "IFC_C_001_4B",
    "denominacion": "Operaciones auxiliares de montaje y mantenimiento de sistemas microinformáticos",
    "plan_antiguo": false,
    "observaciones": ""
  },
  {
    "id": 2,
    "grado": "D",
    "nivel": 2,
    "familia": "Actividades Físicas y Deportivas",
    "codigo": null,
    "denominacion": "Técnico en Actividades Ecuestres",
    "plan_antiguo": false,
    "observaciones": ""
  }
]
```

Notes per als Grados D i E:
- `codigo`: `null` (no apareix al llistat HTML)
- `plan_antiguo`: sempre `false`
- `nivel`: Básico→1, Medio→2, Superior→3. Per a Grado E → `null`

---

## Backend Flask (`backend/app.py`)

### Endpoints

**`GET /api/ofertes`**
Retorna el contingut complet de `data/ofertes.json`.
Si el fitxer no existeix:
```json
{"error": "data not found", "hint": "run POST /api/admin/refresh first"}
```
Status 503.

---

**`POST /api/admin/refresh`**
Llança el pipeline complet d'extracció i scraping en un thread separat (no bloqueja).
Retorna immediatament:
```json
{"status": "started"}
```
Protegit per token: requereix header `Authorization: Bearer <ADMIN_TOKEN>`.
Si el token és incorrecte → status 401.
Si ja hi ha un procés en curs → status 409 amb `{"error": "already running"}`.

---

**`GET /api/refresh-status`**
Retorna l'estat del darrer procés d'actualització:
```json
{
  "status": "idle|running|done|error",
  "last_run": "2025-06-01T12:00:00Z",
  "last_result": {
    "total": 850,
    "by_grado": {"A": 120, "B": 200, "C": 380, "D": 115, "E": 35},
    "duration_seconds": 45,
    "errors": []
  }
}
```
Si el scraping falla parcialment, `errors` conté el detall per grado. Sense autenticació.

---

**`GET /health`**
```json
{"status": "ok"}
```
Sense autenticació.

---

### Configuració

- `ADMIN_TOKEN` llegit de variable d'entorn via fitxer `.env`
- CORS habilitat per a totes les origins
- El fitxer `.env` NO s'inclou al repositori (afegir a `.gitignore`)

---

## Frontend (`frontend/`)

Sense frameworks, sense dependències externes (ni Bootstrap ni jQuery). HTML + CSS + JS vanilla purs.

### Dues seccions: tabs o scroll

---

### Secció 1: Cercador (pública)

**Filtres en temps real** (sense botó de cerca, filtra mentre s'escriu):

| Filtre | Tipus | Comportament |
|---|---|---|
| Text lliure | Input text | Cerca simultàniament a `denominacion` i `codigo` |
| Grado | Dropdown | A, B, C, D, E o "Tots" |
| Família Professional | Dropdown | Llista dinàmica dels valors únics del JSON, o "Totes" |
| Nivell | Dropdown | 1, 2, 3 o "Tots" |
| Ocultar pla antic | Checkbox | Activat per defecte |

**Taula de resultats:**

Columnes: `Codi`, `Denominació`, `Família`, `Grado`, `Nivell`

Les files amb `plan_antiguo: true` mostren un badge "Pla antic" discret (no ocult, visible però no cridaner).

Comptador de resultats visibles ("X resultats") actualitzat en temps real.

Sense paginació. Tot en scroll vertical. La cerca ha de ser fluida fins a 1.500 registres.

**Estat inicial sense dades:** si `/api/ofertes` retorna 503, mostrar missatge:
> "No hi ha dades disponibles. Un administrador ha d'executar l'actualització primer."

---

### Secció 2: Panell Admin (protegit al client)

Un camp de text per introduir el token + botó "Actualitzar dades".

En fer clic:
1. Fa `POST /api/admin/refresh` amb header `Authorization: Bearer <token>`
2. Si la resposta és 401, mostra "Token incorrecte"
3. Si és 200 (`"started"`), comença polling a `GET /api/refresh-status` cada 3 segons
4. Mostra l'estat en curs: "Actualitzant... (en curs)"
5. Quan `status === "done"`, mostra el resum final:
   - Total de registres
   - Desglossat per grado
   - Durada en segons
6. Si `status === "error"`, mostra els errors detallats

El token **no es guarda** en `localStorage` ni a cap lloc persistent. S'esborra en tancar el panell.

---

## `requirements.txt`

```
flask
flask-cors
pdfplumber
requests
beautifulsoup4
python-dotenv
```

---

## Ordre d'execució

1. Crea l'estructura completa de fitxers i directoris
2. Implementa `scraper/parse_pdfs.py`:
   - Executa'l de forma aïllada i verifica manualment 10 registres de cada grado (A, B, C)
   - Comprova que la detecció de família, nivell i pla antic és correcta
3. Implementa `scraper/scrape_html.py`:
   - Executa'l de forma aïllada i verifica manualment 5 registres de cada subtipus (D Básico, D Medio, D Superior, E)
4. Implementa `backend/app.py` amb tots els endpoints
5. Implementa el frontend (index.html, style.css, app.js)
6. Executa un primer `POST /api/admin/refresh` i verifica que `ofertes.json` es genera correctament
7. Comprova el cercador amb les dades reals: filtra per grado, família i text lliure, verifica que els resultats són coherents
