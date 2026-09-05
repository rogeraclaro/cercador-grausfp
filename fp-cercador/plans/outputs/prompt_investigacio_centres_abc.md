# Prompt per a nova sessió — Investigar centres per a graus A, B i C (pla nou)

Copia tot aquest text com a primer missatge d'una sessió nova de Claude Code,
obrint-la al directori `/Users/rogermasellas/AI/Cercador Graus/fp-cercador`
(o al directori pare `/Users/rogermasellas/AI/Cercador Graus`, que és on és
el repositori git real).

---

## Context

Aquest projecte (`fp-cercador` / Cercador Graus FP) cataloga l'oferta
formativa de FP espanyola en 5 "graus": A, B, C, D, E. Per a cada oferta
concreta, l'app mostra opcionalment els **centres** que la imparteixen
(funcionalitat de favorits + seguiment de centres, backend a
`backend/app.py`, dades a `backend/data/centres.json` i
`backend/data/oferta_centres.json`).

**Problema:** el scraper de centres (`backend/scrapers/centres_scraper.py`)
només cobreix:
- **Grau C amb `plan_antiguo=True`** (584 ofertes, codis tipus `COML0110`,
  `ADGG0408`) — consultant `GET https://registrosfp.educacion.gob.es/registroestatalentidadesformacion/datosTablaPublico?ofertaCodigo={codi}`
- **Grau D** (195 ofertes) i **Grau E** (36 ofertes) — mateix endpoint,
  amb `ofertaDenominacion={denominació sense prefix}&gradoProfesional=4` (D)
  o `=5` (E)

**Falta completament:**
- **Grau A** i **Grau B** (Certificats de Professionalitat SEPE, nivells
  bàsics/mòduls — vénen del "Buscador de Graus FP" de todofp.es,
  `backend/scrapers/buscador_scraper.py`)
- **Grau C amb `plan_antiguo=False`** (pla LOMLOE, 397 ofertes, codis tipus
  `ADG_C_001_2P`, format `FAM_C_NNN_NIVELL`)

## El que ja se sap (per no repetir feina)

- Hi ha un spike previ relacionat però NO equivalent:
  `plans/043-spike-c-lomloe-d-i-b-c-loe.md` — investiga *relacions entre
  graus* (C LOMLOE→D, B→C LOE), NO investiga centres. Mai es va executar
  (no hi ha `plans/outputs/spike_043_results.md`).
- El resum del scraper original és a
  `.planning/quick/20260614-centres-scraper/SUMMARY.md` — confirma que
  només es van fer 584+195+36 = 815 relacions, cap per A/B/C nou.
- Estructura d'un registre a `backend/data/ofertes.json`: cada oferta té
  `{codigo, denominacion, familia, nivel, grado, plan_antiguo, ...}`.
  Filtra per `grado` i, per C, per `plan_antiguo`.

## Què cal investigar (per ordre de cost, del més barat al més car)

### 1. Provar el mateix endpoint ja usat, amb altres paràmetres

Abans de buscar cap font nova, comprova si
`registrosfp.educacion.gob.es/registroestatalentidadesformacion/datosTablaPublico`
ja respon per a A, B i C LOMLOE simplement canviant el paràmetre:

```bash
# Prova amb un codi C LOMLOE real (agafa'n un de backend/data/ofertes.json,
# grau=C i plan_antiguo=false)
curl "https://registrosfp.educacion.gob.es/registroestatalentidadesformacion/datosTablaPublico?ofertaCodigo=ADG_C_001_2P&iDisplayLength=10&iDisplayStart=0&draw=1"

# Prova amb ofertaDenominacion + gradoProfesional per a A i B (com ja es fa
# per D=4 i E=5) — cal esbrinar quin valor de gradoProfesional correspondria
# a A i B, si n'hi ha
curl "https://registrosfp.educacion.gob.es/registroestatalentidadesformacion/datosTablaPublico?ofertaDenominacion=<denominacio_sense_prefix>&gradoProfesional=1&iDisplayLength=10&iDisplayStart=0&draw=1"
```

Si algun d'aquests respon amb centres reals (no buit/error), aquesta és de
lluny la solució més barata — només cal ampliar `centres_scraper.py` amb
un bloc més, seguint exactament el mateix patró que ja existeix per a C
LOE/D/E.

### 2. Si l'endpoint actual no cobreix res més: investigar el SEPE

Els graus A/B/C són Certificats de Professionalitat, gestionats
primàriament pel **SEPE** (Servicio Público de Empleo Estatal), no pel
Ministeri d'Educació. El SEPE té el seu propi **Buscador de centros y
entidades de formación** — normalment a sepe.es, dins l'àrea de Formación
Profesional para el Empleo. Cal:
- Localitzar la URL exacta del buscador (pot haver canviat de domini/ruta).
- Esbrinar si és una API JSON consultable (com el registre d'Educació) o
  només un formulari HTML amb resultats renderitzats al servidor.
- Comprovar si permet cercar per codi de certificat, i si retorna llista
  de centres amb dades similars (nom, adreça, contacte) a les que ja
  guardem a `centres.json`.
- Avaluar si té cobertura tant per certificats "antics" com "LOMLOE" (és
  probable que el SEPE unifiqui ambdós, ja que gestiona l'acreditació dels
  centres independentment del pla educatiu).

### 3. Últim recurs (probablement no vàlid per aquest propòsit)

Cada certificat té un Real Decret regulador al BOE amb annexos — però
això dona el contingut formatiu (mòduls, hores), no la llista de centres
que l'imparteixen. Descarta aquesta via tret que les altres fallin per
complet.

## Com procedir

Això és **investigació pura, no toquis codi de producció**. Segueix el
mateix format que altres spikes del projecte (`plans/0XX-spike-*.md`):
escriu els resultats a un fitxer nou `plans/outputs/spike_centres_abc_results.md`
amb aquesta estructura:

```markdown
# Spike — Centres per a graus A, B i C (pla nou)

## Taula de viabilitat
| Font | Cobertura (A/B/C-nou) | Format resposta | Esforç d'integració | Veredicte |
|---|---|---|---|---|

## Detall de proves fetes
[cada crida feta, resultat cru o resumit]

## Recomanació
[si viable: quin fitxer/funció caldria tocar i com; si no viable per cap
font: digues-ho clarament i per què]
```

No cal escriure codi d'implementació — només confirmar viabilitat i, si
n'hi ha, els paràmetres/endpoints exactes que calen per implementar-ho
després en un pla separat.
