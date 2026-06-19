# Pla 041: [SPIKE — F5] Validar fonts de dades per a itineraris formatius A→B→C→D

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada
> comanda de verificació i confirma el resultat esperat abans de passar al
> pas següent. Si es produeix alguna condició STOP, atura't i reporta —
> no improvisis. En acabar, actualitza la fila d'estat d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer)**:
> `git diff --stat fa66f76..HEAD -- backend/scrapers/ backend/data/ofertes.json`
> Si algun fitxer in-scope ha canviat des que es va escriure el pla,
> compara els excerpts de "Current state" amb el codi viu abans de continuar.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (read-only investigation — sense modificar cap font de dades ni cap codi de producció)
- **Depends on**: cap (spike independent)
- **Category**: direction
- **Planned at**: commit `fa66f76`, 2026-06-19

## Per què importa

La Llei 3/2022 (LOMLOE) defineix els graus A–E com acumulables: els mòduls A
formen unitats B, les unitats B s'agrupen en certificats C (equivalents als
antics Certificados de Profesionalidad LOE), i els C conecten amb els cicles
D (Grado Medio/Superior). Mostrar aquests itineraris ("des d'on vinc, on puc
arribar") seria un diferenciador fort que cap cercador existent mostra bé.

Abans de construir res, cal saber quines relacions es poden derivar de les
fonts que ja tenim i quines necessiten nous endpoints o scraping addicional.
Aquest spike ha de produir evidència concreta (codi executable) per a cada
relació, o una decisió documentada de per què no és viable.

## Current state

### Estructura de codis en ofertes.json

El fitxer `backend/data/ofertes.json` (12.894 registres) té la següent
estructura per grado:

**Grado A** — codi format `FAM_A_NNNN_PP`:
```
ADG_A_3001_01 | Preparación de los equipos
ADG_A_3001_02 | Grabación de datos y textos
ADG_A_3001_03 | Tratamiento de textos
ADG_A_3001_04 | Archivo e impresión
```

**Grado B** — codi format `FAM_B_NNNN`:
```
ADG_B_3001 | Tratamiento informático de datos
```

**Grado C nou (LOMLOE)** — codi format `FAM_C_NNN_NX` (397 registres):
```
ADG_C_001_3B | Actividades de grabación, reproducción y tratamien...
ADG_C_001_4B | Actividades administrativas de recepción y relació...
```

**Grado C antic (LOE, plan_antiguo=True)** — codi estil `XXXXXNNNN` (579 registres):
```
ADGG0408 | Operaciones auxiliares de servicios administrativos
ADGG0508 | Operaciones de grabación y tratamiento de datos
```

**Grado D** — codi `None` per a tots els 195 registres; sí que té `ficha_url`:
```
None | Título Profesional Básico en Servicios Administrativos
```

**Grado E** — codi `None` per als 36 registres; sí que té `ficha_url`.

### Relació A→B ja confirmada per inspecció

Durant la preparació d'aquest spike s'ha verificat que **tots** els 1.003
números únics `(FAM, NNNN)` de Grado A tenen un Grado B corresponent
amb el mateix `(FAM, NNNN)`. La derivació és 100% local, sense API externa:

```python
# ADG_A_3001_01 → NNNN=3001 → cerca ADG_B_3001 a ofertes.json
fam, num = "ADG", "3001"
parent_b = next(r for r in records if r['grado'] == 'B' and r['codigo'] == f"{fam}_B_{num}")
```

### Endpoints del buscadorcertificados ja explorats

El buscadorcertificados (todofp.es/buscadorcertificados/) té:
- `POST /busquedaCP` — llistat de tots els C LOE (588 registres, no inclou C LOMLOE nous)
- `POST /fichaCP` — detall d'un certificat per `certificadoID`; la pàgina menciona "Ciclos FP Convalidación" però no hem extret les Unidades de Competencia (UC = Grado B)
- `POST /ciclosFP` — per a un `certificadoID` retorna taula: `Ciclo formativo | Familia | Módulo Profesional`; el camp "Módulo Profesional" conté el número NNNN que coincideix amb els codis B

Exemple confirmat:
```
cert_id=308, codi=COML0110 → ciclosFP retorna:
  "Servicios Administrativos | ADG | 3006 - Preparación de pedidos y venta de productos"
  "Servicios Comerciales     | COM | 3006 - Preparación de pedidos y venta de productos"
```
→ El "3006" coincideix amb `ADG_B_3006` i `COM_B_3006` als nostres registres.

### Fitxer de scraper de referència

El patró de sessió auto-cookies ja usat:
`backend/scrapers/certificados_scraper.py` (bootstrap GET + POST)

El scraper principal: `backend/scrapers/buscador_scraper.py` (bootstrap amb JSESSIONID)

## Comandes que necessitaràs

| Propòsit | Comanda | Esperat en cas d'èxit |
|---|---|---|
| Executar script spike | `python3 plans/outputs/spike_f5.py` | Impressió amb resultats per relació |
| Tests existents | `python3 -m pytest backend/tests/ -x -q` | tots passes |
| Verificar JSON ofertes | `python3 -c "import json; d=json.load(open('backend/data/ofertes.json')); print(len(d))"` | `12894` |

## Àmbit

**In scope** (els únics fitxers que pots crear o modificar):
- `plans/outputs/spike_f5.py` — script d'investigació (crea'l nou; no entra a producció)
- `plans/README.md` — actualitzar l'estat al final

**Out of scope** (NO tocar):
- `backend/scrapers/` — no modificar cap scraper existent
- `backend/data/ofertes.json` — no sobreescriure
- Cap fitxer de frontend ni de backend
- Cap migració de base de dades

## Git workflow

- No cal crear branca ni commit per a aquest spike (és un script d'investigació)
- Si vols desar el script per a referència futura, pots fer un commit a `master`
  amb missatge `spike(f5): script investigació itineraris A→B→C→D`

## Passos

### Pas 1: Verifica la relació A→B localment

Crea `plans/outputs/spike_f5.py` i afegeix la secció A→B:

```python
#!/usr/bin/env python3
"""
Spike F5 — Itineraris formatius A→B→C→D
Script d'investigació (NO és codi de producció).
"""
import json, re, sys

with open("backend/data/ofertes.json") as f:
    records = json.load(f)

by_grado = {}
for r in records:
    by_grado.setdefault(r["grado"], []).append(r)

# --- A→B ---
pat_a = re.compile(r"^([A-Z]+)_A_(\d+)_(\d+)$")
pat_b = re.compile(r"^([A-Z]+)_B_(\d+)$")

b_index = {}
for r in by_grado.get("B", []):
    m = pat_b.match(r.get("codigo") or "")
    if m:
        b_index[(m.group(1), m.group(2))] = r

matched, unmatched = 0, []
for r in by_grado.get("A", []):
    m = pat_a.match(r.get("codigo") or "")
    if m:
        key = (m.group(1), m.group(2))
        if key in b_index:
            matched += 1
        else:
            unmatched.append(r["codigo"])

print(f"[A→B] Mòduls A amb B corresponent: {matched}")
print(f"[A→B] Mòduls A SENSE B (no hauria d'haver-ne): {len(unmatched)}")
if unmatched:
    print("  Exemples sense B:", unmatched[:5])

# Exemple d'itinerari complet A→B
ex_key = list(b_index.keys())[0]
ex_b = b_index[ex_key]
ex_a_parts = [r for r in by_grado.get("A", [])
              if pat_a.match(r.get("codigo") or "")
              and (pat_a.match(r["codigo"]).group(1), pat_a.match(r["codigo"]).group(2)) == ex_key]
print(f"\n[A→B] Exemple: B={ex_b['codigo']} | '{ex_b['denominacion']}'")
for p in ex_a_parts:
    print(f"       A={p['codigo']} | '{p['denominacion']}'")
```

**Verifica**: `python3 plans/outputs/spike_f5.py` ha d'imprimir
`[A→B] Mòduls A amb B corresponent: 8730` i `SENSE B: 0`.

---

### Pas 2: Investiga B→C via fichaCP (Unidades de Competencia)

La hipòtesi és que la fitxa de cada Certificat de Profesionalidad (Grado C LOE)
inclou les seves Unidades de Competencia, que corresponen als codis B.

Afegeix al script:

```python
# --- B→C via fichaCP ---
import requests
from bs4 import BeautifulSoup

BASE_CERT = "https://www.todofp.es/buscadorcertificados"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Referer": BASE_CERT + "/buscador",
}

def bootstrap_cert_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(BASE_CERT + "/buscador", timeout=20)
    return s

sess = bootstrap_cert_session()

# Busquem cert_id per COML0110 (cert_id=308, confirmat a l'spike)
payload_ficha = {
    "certificadoID": "308",
    "limite": "0", "paso": "10", "total": "588",
    "codigo": "", "denominacion": "", "familia": "0", "nivelFiltro": "0",
    "origen": "busquedaCP",
}
resp_ficha = sess.post(BASE_CERT + "/fichaCP", data=payload_ficha, timeout=30)
soup_ficha = BeautifulSoup(resp_ficha.text, "html.parser")

print("\n[B→C] fichaCP per COML0110 (cert_id=308):")
print("  Status:", resp_ficha.status_code)

# Cerca camps: Unidades de Competencia, UC, módulo formatiu
text = soup_ficha.get_text(separator="\n")
uc_found = []
for line in text.split("\n"):
    line = line.strip()
    if line and any(kw in line.lower() for kw in ["unidad de competencia", " uc", "uf", "módulo formativo",
                                                    "unitat de competència", "_b_", "nivel"]):
        uc_found.append(line)
if uc_found:
    print("  Línies amb UC/mòduls:")
    for l in uc_found[:15]:
        print("   ", repr(l[:100]))
else:
    print("  AVÍS: No s'han trobat Unidades de Competencia al fichaCP HTML")
    print("  Text complet (primers 2000 chars):")
    print(text[:2000])
```

**Verifica**: el script imprimeix el contingut de fichaCP. El resultat determinant és:
- Si hi ha "Unidades de Competencia" → anota quins codis retorna i si coincideixen amb codis B
- Si NO hi ha UC → anota-ho com a "B→C no disponible via fichaCP"

---

### Pas 3: Investiga B→C via estructura de codis LOMLOE

Els C nous (LOMLOE) tenen codis com `ADG_C_001_3B`. El suffix `3B` podria
indicar el nivell (3) i alguna referència al contingut. Afegeix al script:

```python
# --- B→C via estructura de codis LOMLOE ---
pat_c_new = re.compile(r"^([A-Z]+)_C_(\d+)_(\d+)([A-Z]+)$")

c_new = [r for r in by_grado.get("C", []) if not r.get("plan_antiguo")]
print(f"\n[B→C LOMLOE] C nous (LOMLOE): {len(c_new)}")

# Analitza l'estructura del codi
examples = {}
for r in c_new[:10]:
    cod = r.get("codigo", "")
    m = pat_c_new.match(cod)
    if m:
        fam, seq, nivel_num, nivel_letra = m.groups()
        examples[cod] = {"fam": fam, "seq": seq, "nivel": nivel_num + nivel_letra,
                         "denominacion": r["denominacion"][:50]}
        # Busquem B de la mateixa família (per veure si el número seq coincideix amb algun B)
        b_same_fam = [br for br in by_grado.get("B", [])
                      if br.get("codigo", "").startswith(fam + "_B_")]
        examples[cod]["b_count_same_fam"] = len(b_same_fam)

for cod, info in examples.items():
    print(f"  {cod}: nivel={info['nivel']}, B de {info['fam']}: {info['b_count_same_fam']}, '{info['denominacion']}'")

# El número seq (001, 002...) dels C nous coincideix amb algun B?
# B usa NNNN (4 dígits, ex: 3001), C nou usa NNN (3 dígits, ex: 001) → probablement NO match directe
c_seq_nums = {pat_c_new.match(r["codigo"]).group(2)
              for r in c_new if pat_c_new.match(r.get("codigo",""))}
b_nums = {pat_b.match(r["codigo"]).group(2)
          for r in by_grado.get("B",[]) if pat_b.match(r.get("codigo",""))}
overlap = c_seq_nums & b_nums
print(f"\n[B→C LOMLOE] Números seq C nous ({len(c_seq_nums)}) ∩ nums B ({len(b_nums)}): {len(overlap)}")
print("  → Si overlap=0: no hi ha relació directa per codi entre C nous i B")
```

**Verifica**: el script imprimeix la superposició. S'espera `overlap=0`
(els numbers seq de C LOMLOE (001...) i els de B (3001...) no coincideixen).

---

### Pas 4: Investiga C→D via ciclosFP

L'endpoint `ciclosFP` del buscadorcertificados retorna, per a cada C LOE,
quins cicles D el convaliden. Afegeix al script:

```python
# --- C→D via ciclosFP ---

# Agafem una mostra de 5 certificats LOE i en veiem la relació amb D
c_loe = [r for r in by_grado.get("C", []) if r.get("plan_antiguo")][:5]
print(f"\n[C→D] Provant ciclosFP per a {len(c_loe)} C LOE (necessita cert_id_buscador):")

# El cert_id_buscador s'obté de la base de dades d'enriquiment (pla 020)
# Si no disponible, hem de fer POST /busquedaCP primer per obtenir-lo
# Aquí usem els cert_ids coneguts per a la demo (308=COML0110)
demo_certs = [
    {"cert_id": "308", "codigo": "COML0110"},
    # Afegir més si vols ampliar la mostra
]

for cert in demo_certs:
    payload_ciclos = {
        "certificadoID": cert["cert_id"],
        "limite": "0", "paso": "10", "total": "588",
        "codigo": "", "denominacion": "", "familia": "0", "nivelFiltro": "0",
        "origen": "busquedaCP",
    }
    resp_ciclos = sess.post(BASE_CERT + "/ciclosFP", data=payload_ciclos, timeout=30)
    soup_ciclos = BeautifulSoup(resp_ciclos.text, "html.parser")
    rows = soup_ciclos.select("table tr")
    print(f"\n  {cert['codigo']} (cert_id={cert['cert_id']}):")
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
        if cells:
            print("   ", " | ".join(cells[:3]))

    # Extreu els números de mòdul del Grado D i comprova si coincideixen amb B
    import re as _re
    mod_nums = _re.findall(r"(\d{4})\s*-", resp_ciclos.text)
    if mod_nums:
        print(f"  Números de mòdul trobats: {mod_nums}")
        for num in mod_nums:
            b_matches = [r for r in by_grado.get("B",[])
                         if pat_b.match(r.get("codigo",""))
                         and pat_b.match(r["codigo"]).group(2) == num]
            if b_matches:
                print(f"    → B codis per num {num}: {[r['codigo'] for r in b_matches]}")
```

**Verifica**: el script imprimeix la taula ciclosFP i confirma que els
números de mòdul (ex: 3006) coincideixen amb codis B (`ADG_B_3006`, `COM_B_3006`).

---

### Pas 5: Investiga els D via ficha_url

Els Grado D no tenen `codigo` però sí `ficha_url`. Revisa si la pàgina de
la fitxa d'un D inclou referències a certificats C que s'hi convaliden.

```python
# --- D: ficha_url conté relació amb C? ---
import urllib.request

d_recs = by_grado.get("D", [])[:3]
print(f"\n[C→D via D.ficha_url] Mostrem ficha_url de primers 3 D:")
for r in d_recs:
    url = r.get("ficha_url","")
    den = r.get("denominacion","")[:60]
    print(f"  '{den}' → {url}")

# Fes una petició a una ficha D i busca si menciona certificats C
if d_recs and d_recs[0].get("ficha_url"):
    url = d_recs[0]["ficha_url"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=20) as resp_d:
            html_d = resp_d.read().decode("utf-8", errors="replace")
        soup_d = BeautifulSoup(html_d, "html.parser")
        text_d = soup_d.get_text(separator="\n")
        cert_refs = [l.strip() for l in text_d.split("\n")
                     if l.strip() and any(kw in l.lower()
                     for kw in ["certificado", "convalid", "cp ", " cp\t"])]
        print(f"\n  Línies amb 'certificado/convalid' a la fitxa del D:")
        for l in cert_refs[:10]:
            print("   ", repr(l[:100]))
        if not cert_refs:
            print("  AVÍS: cap referència a certificats C a la fitxa del D")
    except Exception as e:
        print(f"  Error llegint ficha_url: {e}")
```

**Verifica**: el script imprimeix si la pàgina D menciona o no els C.

---

### Pas 6: Documenta les conclusions

Al final del script, afegeix un bloc de conclusions que el script imprimeixi
automàticament:

```python
print("""
=== CONCLUSIONS SPIKE F5 ===

RELACIÓ   | FONT             | VIABLE? | ESFORÇ AFEGIT | COBERTURA
A → B     | codis locals     | SÍ      | 0 (ja parsejable) | 100% (8730 A → 1003 B)
B → C LOE | fichaCP UC       | ?       | M (scraping fichaCP per cada C LOE) | ~579 C LOE
B → C LOMLOE | no source    | ?       | desconegut    | 397 C LOMLOE (falta font)
C → D     | ciclosFP         | SÍ (parcialment) | M (1 crida/C LOE) | ~579 C LOE
D → E     | no font identificada | ?  | desconegut    | 195 D, 36 E

Omple la columna VIABLE? amb SÍ/NO/PARCIAL en base als resultats dels passos 2-5.
=== FI CONCLUSIONS ===
""")
```

**Verifica**: el script s'executa sense errors i imprimeix les conclusions.

---

### Pas 7: Actualitza l'índex de plans

Actualitza `plans/README.md` afegint la fila del pla 041:

```
| 041 | [SPIKE — F5] Itineraris formatius A→B→C→D — validació de fonts | P2 | M | — | DONE |
```

## Test plan

Aquest spike no produeix codi de producció, per tant no hi ha tests nous a
escriure. El "test" és l'execució del script `plans/outputs/spike_f5.py`
sense errors i amb resultats documentats.

Si el spike conclou que A→B és derivable localment (esperat), el pla de
construcció (042) haurà d'incloure tests unitaris per a la funció
`build_itinerary_graph(records)`.

## Criteris de DONE

- [ ] `python3 plans/outputs/spike_f5.py` s'executa sense excepcions Python
- [ ] La sortida confirma `[A→B] Mòduls A amb B: 8730` i `SENSE B: 0`
- [ ] La sortida documenta si fichaCP retorna o no Unidades de Competencia (Pas 2)
- [ ] La sortida documenta si el codi dels C LOMLOE és parsejable per a B→C (Pas 3)
- [ ] La sortida confirma que `ciclosFP` retorna D per als C LOE, amb números de mòdul que coincideixen amb B (Pas 4)
- [ ] La sortida documenta si les fitxes D mencionen C (Pas 5)
- [ ] `plans/README.md` actualitzat amb estat DONE per al pla 041
- [ ] El bloc CONCLUSIONS (Pas 6) conté els camps VIABLE? i ESFORÇ AFEGIT emplenats

## Condicions STOP

Atura't i reporta (no improvisis) si:

- El bootstrap del buscadorcertificados retorna HTTP 5xx o bloqueja la sessió
  (segurament han canviat el sistema de cookies — reporta i no reintentis)
- El fitxer `backend/data/ofertes.json` no existeix o té menys de 10.000 registres
  (el pipeline pot estar trencat — no continuar)
- El pas A→B retorna `SENSE B > 0` (l'estructura dels codis ha canviat — STOP)
- `fichaCP` retorna HTML completament diferent a la plantilla descrita (pot ser
  que el ministeri hagi canviat el portal)

## Notes de manteniment

- **Si el spike confirma B→C via fichaCP**: el pla 042 haurà de fer 579+ crides
  HTTP (una per C LOE), amb rate limiting i cache local. Valorar si fa falta
  reescriure `certificados_scraper.py` o crear un nou `itinerari_scraper.py`.
- **Si B→C LOMLOE no té font**: es pot oferir una versió parcial F5 que cobreix
  només els C LOE (579) i mostrar "itinerari no disponible" per als LOMLOE (397).
- **La relació C→D té una limitació important**: els D no tenen `codigo` a
  `ofertes.json`. Per mostrar la fitxa del D als itineraris, cal usar `ficha_url`
  o l'arxiu de `denominacion`.
- **Pla 042** (construcció de F5) hauria de dependre d'aquest spike DONE i del
  pla 030 (BD SQLite) per persistir el graf d'itineraris.
