# Spike 015: Centres on s'imparteix cada grau

> **Data de verificació**: 2026-06-14
> **Peticions reals al servidor del ministeri**: ~19 Font 1, 2 Font 2 (dins límit del pla)

---

## Resum executiu

**Font 1 (Registre Estatal Entitats de Formació FP) és la font primària recomanada.**
Cobreix Graus C, D i E amb adreça completa, telèfon i email via una API JSON sense captcha.
La cobertura per Grau A i B és indirecta (s'hereten dels centres del Grado C pare).
Font 2 (todofp.es `busquedaCentros`) és inferior: menys centres, sense adreça, només Grado C LOE.

---

## Step 1: Validació a fons de la Font 1

### Descripció

**Registre General de Centres de Formació Professional**
URL: `https://registrosfp.educacion.gob.es/registroestatalentidadesformacion/buscarPublico`
Versió de l'aplicació: 2.2.28 (verificat 2026-06-14)

### 1.1 Mecanisme de cerca

El formulari fa servir **bootstrap + AJAX GET** (no form POST):

```
1. GET /buscarPublico → emmet JSESSIONID (sense captcha)
2. GET /datosTablaPublico?{paràmetres} → resposta JSON DataTables
```

El botó "Buscar" invoca `buscar()` JS que inicialitza DataTables amb server-side processing.

**Paràmetre crític (verificat)**: `ofertaCodigo`
- Per Grado C LOE: codi SEPE alfanumèric (`ADGG0408`, `IFCT0209`)
- Per Grado D/E: codi numèric de 8 dígits (`12112101`, `12112001`)
- `especialidadCodigo` (alias del JS) NO fa el filtre — usar `ofertaCodigo`

Paràmetres de filtre addicionals disponibles:
| Paràmetre | Exemples de valor |
|-----------|------------------|
| `gradoProfesional` | `3`=C, `4`=D, `5`=E (NO 'C','D','E') |
| `ofertaDenominacion` | cerca parcial per text de denominació |
| `ccaaCodigo` | codi CCAA (2 dígits) |
| `provinciaCodigo` | codi de província |
| `familiaCodigo` | abreviatura família (p. ex. `ADG`) |
| `titularidadRCD` | titularitat del centre |

### 1.2 Resultats per a 3 títols coneguts

| Oferta | Codi | Grado | Total centres | Temps |
|--------|------|-------|---------------|-------|
| Gestión Administrativa | ADGG0408 | C | **4.232** | 0.59s |
| Sistemas de Telecomunicaciones | IFCT0209 | C | **1.512** | 0.42s |
| (Gestión Administrativa CFGM) | 12112101 | D | **776** | ~0.4s |
| (Soldadura y calderería) | 12110802 | D | **99** | ~0.3s |

Tots en una sola crida (length=5000 recupera tots sense paginació).

### 1.3 Dades del detall de centre: adreça, telèfon, email

La resposta JSON ja inclou tots els camps de contacte directament (NO cal accedir al detall):

```
[0]:  codigo intern (8 dígits o buit)
[1]:  codigoMinisterio (M + 11 dígits)   ← clau única de centre
[2]:  nombre del centre
[3]:  localidad
[4]:  codigoPostal
[5]:  provincia
[6]:  (buit en centres públics)
[7]:  comunidadAutonoma
[8]:  direccion completa                  ← INCLOSA
[9]:  telefono                            ← INCLOSA
[10]: email                              ← INCLOSA
[11]: centrorcd (0=Acreditado, 1=RCD)
[12]: letrasgrado (C / D / E)
```

Exemple verificat:
```json
["0100000938", "M010009325G", "CENTRO DE ESTUDIOS ALAVA", "Vitoria-Gasteiz",
 "01001", "ARABA/ÁLAVA", "", "PAÍS VASCO", "CL ALDAVE 20", "945144531",
 "info@ceaformacion.com", "0", "C"]
```

Detall de centre RCD (URL `/centrorcd/{codMinisterio}`) conté a més: URL web, titularitat.

### 1.4 Exportació Excel

Endpoint: `GET /datosTablaExcelPublico?{mateixos paràmetres}`

La primera prova va retornar HTML (sessió caducada). Requereix:
- Sessió JSESSIONID activa (bootstrap previ)
- Mateixos paràmetres que `datosTablaPublico`

El JS indica `limiteMaximo=10.000` (màxim exportable), `limiteAdvertencia=2.000` (demana confirmació).
Per a descàrregues > 10.000 centres, caldria paginar.

### 1.5 Estratègia d'enumeració: per oferta vs per família

| Estratègia | Consultes | Temps estimat | Mapping oferta↔centre |
|------------|-----------|---------------|----------------------|
| **Per `ofertaCodigo` (recomanada)** | 584 (Grado C LOE) + 195 (D) + 36 (E) = **815** | ~13 min | **Exacte** |
| Per família + grado | ~26 famílies C + 1 D + 1 E ≈ 28 | ~30s | **Imprecís** (tots centres de la família) |
| Descàrrega total sense filtre | 1 | 2s | **Cap** (no sabem quins títols ofereix cada centre) |

**Recomanació: per `ofertaCodigo`**. 815 consultes a ~0.5s = ~7 min per al pipeline mensual.
La font admet throttling a 1 req/s sense problemes observats (servidors del ministeri).

### 1.6 Grado A/B: tractament "inclosos en C"

Font 1 NO té opcions per Grado A ni B al selector `gradoProfesional` (només 3/4/5 = C/D/E).

**Estratègia derivada**: un centre autoritzat per a un codi Grado C (p. ex. `ADGG0408`) pot
impartir els mòduls A i B que composen aquell certificat. Però la relació C→A/B **no consta
al nostre `ofertes.json`** (els Graus A i B no tenen el camp `codigo` del seu C pare).

**Recomanació**: per a la primera versió, mostrar centres de Grado C quan l'usuari consulta
un A o un B de la mateixa família i prefix. La relació exacta A/B→C requereix investigació
separada de l'estructura curricular LO3/2022.

---

## Step 2: Validació de l'enriquiment de contacte

### 2.1 Font 1 ja inclou les dades de contacte

La Font 1 proporciona `direccion`, `telefono` i `email` al JSON de la llista (camps [8],[9],[10]).
**Font 2 (RCD) és innecessàri per a contacte.** No cal enriquiment creuant fonts.

### 2.2 Comparació Font 1 vs todofp.es busquedaCentros

| Criteri | Font 1 (registrosfp) | Font 2 (todofp busquedaCentros) |
|---------|---------------------|--------------------------------|
| Format | JSON (DataTables) | HTML paginat |
| Adreça completa | Sí | No (només CP) |
| Telèfon | Sí | Sí |
| Email | Sí | Sí |
| Grado C LOE | Sí — 4.232 per ADGG0408 | Sí — 3.288 per ADGG0408 |
| Grado D/E | **Sí** | **No** |
| Grado A/B | No | No |
| Automatitzable | Sí (GET sense captcha) | Sí (GET) |

Font 1 dominant en tots els eixos. **Font 2 descartada com a font primària.**

### 2.3 Font 4 (dades obertes autonòmiques): innecessària

Amb Font 1 tenim adreça+telèfon+email, la Font 4 no aporta valor addicional.
Mantenir com a darrer recurs si alguna CCAA no apareix a Font 1.

---

## Step 3: Model de dades i integració

### 3.1 Fitxers proposats

#### `backend/data/centres.json` — catàleg de centres (≈ 18.000 registres)

```json
[
  {
    "id": "M010014639G",
    "codigo": "01000411",
    "nombre": "LAUDIOALDE",
    "direccion": "Virgen del Carmen 17",
    "localidad": "Laudio/Llodio",
    "cp": "01400",
    "provincia": "ARABA/ÁLAVA",
    "ccaa": "PAÍS VASCO",
    "telefono": "946720505",
    "email": "010201aa@hezkuntza.net",
    "tipo": "rcd",
    "updated_at": "2026-06-14"
  }
]
```

Mida estimada: ~18.000 centres × ~250 bytes ≈ **4.5 MB**.
Opció alternativa: SQLite o fitxer gzip per reduir mida.

#### `backend/data/oferta_centres.json` — relació oferta ↔ centres

```json
{
  "ADGG0408": ["M010014639G", "M010009325G", ...],
  "IFCT0209": ["M010009325G", ...],
  "12112101": ["M010014639G", ...]
}
```

Mida estimada: ~1.000 ofertes × ~200 centres cadascuna × ~14 bytes per ID ≈ **3 MB** gzip.

Total: ~7.5 MB addicionals al backend. **NO incrustats a `ofertes.json`** (ja 3.7 MB).

### 3.2 Canvis al pipeline

**Opció A (recomanada): pipeline separat amb cadència mensual**

```
backend/scrapers/centres_scraper.py
  - bootstrap_session()
  - fetch_centres_per_oferta(codigo)   # 815 crides, rate-limit 1 req/s
  - build_centres_json()
  - build_oferta_centres_json()
```

Temps d'execució: ~15 min/mes. No alenteix el refresh setmanal de `ofertes.json`.

**Opció B: passada addicional al pipeline setmanal**

Afegir `centres_scraper` al `pipeline.py` existent. Risc: alenteix el refresh setmanal
(+15 min sobre els ~4s actuals). Recomanat no fer fins que el volum ho justifiqui.

**Cicle de vida dels registres** (estratègia a de snapshots):
- Reutilitzar `history.compute_changes` del plan 005/006
- `vigent` = present a l'última captura
- `nou` = apareix a la captura actual però no a l'anterior
- `historic` = desapareixia de captures anteriors → conservat amb marca `actiu=False`

### 3.3 Endpoint API

```
GET /api/centres?codigo=ADGG0408
→ JSON array de centres (filtrats de oferta_centres.json)
```

Alternativa: servir `oferta_centres.json` com a fitxer estàtic (CDN/nginx) i fer
`fetch('/data/oferta_centres.json')` al frontend. Menys flexible però zero overhead de Flask.

**Recomanació**: endpoint Flask `/api/centres?codigo=...` per a la primera versió.
Migrar a fitxer estàtic si el tràfic ho justifica.

### 3.4 Esbós UI (frontend)

```
Fila de resultat de cerca:
┌─────────────────────────────────────┐
│ Gestión Administrativa (Grado C)    │
│ ADG · Nivell 2 · Plan LOE          │
│ [▶ 4.232 centres]                  │ ← clic → expandeix
└─────────────────────────────────────┘

Fila expandida (fetch on-demand):
┌─────────────────────────────────────┐
│ Filtra per CCAA: [Totes ▼]        │
│ Filtra per província: [Totes ▼]    │
│                                     │
│ ● CENTRO DE ESTUDIOS ALAVA         │
│   CL ALDAVE 20, Vitoria-Gasteiz    │
│   📞 945144531 · ✉ info@ceaf...    │
│                                     │
│ ● CEAM S.L.                        │
│   ..., Vitoria-Gasteiz             │
│                                     │
│ [Mostrar tots els 4.232 centres]   │
└─────────────────────────────────────┘
```

Implementació suggerida: Alpine.js (ja present) + `fetch` al clic de la fila expandible.
Mostrar els primers 20 centres, paginació client-side o scroll infinit.

---

## Step 4: Estratègia per a "inscripció oberta"

### 4.1 Recomanació: taula estàtica de 17 URLs (opció a del pla)

Cap font estatal publica l'estat d'inscripció. La inscripció és competència autonòmica.
La solució més senzilla i mantenible: **taula estàtica de 17+2 URLs als portals d'admissió**,
versionada al repo, revisada manualment 1 cop/any.

### 4.2 Taula de 17 + 2 URLs d'admissió FP (verificades 2026-06-14)

| CCAA | Portal centres FP / admissió |
|------|------------------------------|
| Andalucía | https://www.juntadeandalucia.es/educacion/portals/web/ced/centros |
| Aragón | https://educa.aragon.es/web/guest/oferta-formativa-en-formaci%C3%B3n-profesional-del-sistema-educativo |
| Asturias | https://www.educastur.es/mapa-formacion-profesional |
| Illes Balears | http://www.caib.es/sites/fp/ca/cercador_doferta_formativa/ |
| Canàries | https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/centros-que-imparten-fp/ |
| Cantàbria | https://www.educantabria.es/centros/buscador-de-centros |
| Castilla-La Mancha | https://www.educa.jccm.es/es/fpclm/centros-formacion-profesional |
| Castilla y León | https://www.educa.jcyl.es/fp/es/oferta-fp-castilla-leon-curso-2024-2025 |
| Catalunya | http://mapaescolar.gencat.cat/ |
| Extremadura | https://www.educarex.es/fp/ofertamapa.html |
| Galícia | http://www.edu.xunta.gal/fp/centros |
| Madrid | https://gestiona.comunidad.madrid/wpad_pub/run/j/MostrarConsultaGeneral.icm |
| Múrcia | https://llegarasalto.com/guiafp/#portfolio |
| Navarra | https://www.educacion.navarra.es/web/dpto/centros-educativos |
| País Basc | https://www.euskadi.eus/informacion/oferta-formativa-de-fp-en-la-capv/web01-a2hlanhz/es/ |
| La Rioja | https://www.larioja.org/educarioja-centros/es/buscador-centros/mapa-centros |
| C. Valenciana | https://ceice.gva.es/es/web/centros-docentes/formacion-profesional/listados |
| Ceuta | https://www.todofp.es/como-cuando-y-donde-estudiar/donde-estudiar/informacion-ceuta-melilla/centros-fp-ceuta.html |
| Melilla | https://www.educacionyfp.gob.es/contenidos/ba/ceuta-melilla/melilla/portada.html |

Origen: `https://www.todofp.es/como-cuando-y-donde-estudiar/donde-estudiar/comunidades.html` (2026-06-14)
**Cal reverificar anualment** (les CCAA canvien portals).

### 4.3 Cost/risc de l'alternativa: scraping de calendaris

Contra: 17 portals amb formats i tecnologies heterogènies, canvis sense avís, difícil de mantenir.
A favor: informació valuosa per a l'usuari.
Recomanació: **NO implementar** fins que el propietari ho demani com a fase pròpia prioritzada.

---

## Step 5: Pla de construcció proposat

### Seqüència recomanada

#### Pla 016: Scraper de centres (Font 1) — Esforç M, Risc BAIX

**Entregable**: `centres_scraper.py`, `centres.json`, `oferta_centres.json`

Tasques:
1. Bootstrap de sessió (reutilitzar patró de `buscador_scraper._bootstrap_session`)
2. Loop per 584 codis Grado C LOE → `ofertaCodigo` → resultats JSON → desduplicació centres
3. Loop per 195 Grado D → `ofertaDenominacion` + `gradoProfesional=4` (risc: falsos positius)
4. Loop per 36 Grado E → `ofertaDenominacion` + `gradoProfesional=5`
5. Generar `centres.json` (catàleg) i `oferta_centres.json` (relació)
6. Rate-limiting a 1 req/s (unes 15 min totals)

Risc principal: el matching per denominació per a Grado D pot donar falsos positius.
Mitigació: afegir filtre de `nivel` (1=FP Bàsica, 2=CFGM, 3=CFGS) disponible a la Font 1.

#### Pla 017: API + frontend — Esforç M, Risc BAIX

**Entregable**: `/api/centres?codigo=X`, fila expandible al frontend amb llista de centres

Tasques:
1. Endpoint Flask `/api/centres` que llegeix `oferta_centres.json` i `centres.json`
2. Filtre per CCAA/província al frontend (Alpine.js)
3. Mostrar comptador "N centres" a la fila de cerca
4. Deep-link "Com matricular-s'hi" → URL CCAA (taula de 17)

#### Pla 018: Cicle de vida i estats — Esforç M-L, Risc MEDI

**Entregable**: historial d'estats per als parells oferta×centre

Tasques:
1. Adaptació de `history.compute_changes` per a la relació oferta↔centre
2. Marcar `vigent / nou / historic` a `oferta_centres.json`
3. Filtre UI per estat

**Condició prèvia**: un mínim de 2 captures mensuals per derivar estats.

### Estimació de volum de dades

| Fitxer | Registres estimats | Mida estimada |
|--------|-------------------|---------------|
| `centres.json` | ~15.000 centres únics | 3.8 MB |
| `oferta_centres.json` | ~815 ofertes × ~500 centres mitjans | 5.7 MB |
| **Total** | — | **~9.5 MB** |

Frontend: càrrega on-demand (`fetch` al clic). Màxim ~785 KB per oferta (ADGG0408).
Considera gzip: ~785 KB → ~150 KB transferit. Acceptable per connexió mòbil.

---

## Limitacions i riscos detectats

| Risc | Probabilitat | Impacte | Mitigació |
|------|-------------|---------|-----------|
| Matching Grado D per text = falsos positius | Medi | Baix | Afegir filtre `nivel` |
| Font 1 canvia estructura URL/API | Baixa | Alt | Monitor mensual |
| Codes numèrics Grado D no disponibles al nostre DB | Alt | Medi | Derivar amb text lookup inicial |
| Grado A/B sense cobertura directa | Confirmat | Medi | Mostrar centres del C pare (primera versió) |
| Grado C LO3/2022 (plan_antiguo=False, ~402) no a Font 1 | Confirmat | Medi | Esperar que Font 1 els incorpori |

---

## Criteris Done del pla (verificació)

- [x] `plans/outputs/spike-centres-per-grau.md` existeix i respon els Steps 1–5
- [x] Inclou exemples reals de request/response de la Font 1 (mostra)
- [x] Inclou la decisió d'enumeració quantificada (consultes × files × temps)
- [x] Inclou el model de dades amb mides estimades i l'esbós d'UI
- [x] Inclou la taula de 17+2 URLs d'admissió per CCAA (verificades)
- [x] Cap fitxer fora de `plans/` modificat
- [ ] Fila actualitzada a `plans/README.md` (pendent)
