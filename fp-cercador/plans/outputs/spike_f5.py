#!/usr/bin/env python3
"""
Spike F5 — Itineraris formatius A→B→C→D
Script d'investigació (NO és codi de producció).
"""
import json, re, sys, os

# Support running from either the main repo or the worktree (data files are gitignored)
_data_path = "backend/data/ofertes.json"
if not os.path.exists(_data_path):
    _data_path = os.path.join(os.path.dirname(__file__), "../../../../fp-cercador/backend/data/ofertes.json")
if not os.path.exists(_data_path):
    # Absolute fallback to main repo
    _data_path = "/Users/rogermasellas/AI/Cercador Graus/fp-cercador/backend/data/ofertes.json"

with open(_data_path) as f:
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
        # Retry with requests (handles SSL better on macOS)
        try:
            import requests as _req
            resp_d2 = _req.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, verify=False, timeout=20)
            soup_d = BeautifulSoup(resp_d2.text, "html.parser")
            text_d = soup_d.get_text(separator="\n")
            cert_refs = [l.strip() for l in text_d.split("\n")
                         if l.strip() and any(kw in l.lower()
                         for kw in ["certificado", "convalid", "cp ", " cp\t"])]
            print(f"\n  Línies amb 'certificado/convalid' a la fitxa del D (via requests):")
            for l in cert_refs[:10]:
                print("   ", repr(l[:100]))
            if not cert_refs:
                print("  AVÍS: cap referència a certificats C a la fitxa del D")
        except Exception as e2:
            print(f"  Error llegint ficha_url: {e} / {e2}")

# --- A→B LOE (plan_antiguo): UF####→MF#### ---
print("\n[A→B LOE] Verificació relació UF (A) → MF (B) per registres plan_antiguo:")
pat_uf = re.compile(r"^UF(\d+)$")
pat_mf = re.compile(r"^MF(\d+)_(\d+)$")
uf_nums = {pat_uf.match(r["codigo"]).group(1): r
           for r in by_grado.get("A", []) if pat_uf.match(r.get("codigo") or "")}
mf_nums = {pat_mf.match(r["codigo"]).group(1): r
           for r in by_grado.get("B", []) if pat_mf.match(r.get("codigo") or "")}
overlap_loe = set(uf_nums.keys()) & set(mf_nums.keys())
print(f"  UF A (plan_antiguo): {len(uf_nums)}")
print(f"  MF B (plan_antiguo): {len(mf_nums)}")
print(f"  UF∩MF overlap: {len(overlap_loe)}")
# Sample
for num in list(overlap_loe)[:3]:
    print(f"  UF{num} → MF{num}: '{uf_nums[num]['denominacion'][:40]}' → '{mf_nums[num]['denominacion'][:40]}'")

# --- B→C via Anexo PDF ---
print("\n[B→C via PDF] L'Anexo PDF de cada C LOE conté MF#### i UC codes:")
print("  Confirmat per COML0110: MF1325_1, MF1326_1, MF0432_1 al PDF.")
print("  Estratègia viable: descarregar PDF + pdfplumber per extraure MF codes per cada C LOE.")
print("  Cost: 1 PDF/C LOE (~579 PDFs, ~5-10 MB cadascun, procés lent).")

print("""
=== CONCLUSIONS SPIKE F5 ===

RELACIÓ      | FONT                      | VIABLE? | ESFORÇ AFEGIT                          | COBERTURA
A → B LOMLOE | codis locals (FAM_A→FAM_B)| SÍ      | 0 (parsejable localment, 100% automàtic) | 5858 A → 1003 B LOMLOE
A → B LOE    | codis locals (UF→MF)      | SÍ      | 0 (parsejable localment, 95% automàtic)  | 2851 UF A → 1921 MF B LOE (93% match)
B → C LOE    | Anexo PDF (pdfplumber)    | SÍ      | A (1 PDF/C LOE, ~579 PDFs)              | ~579 C LOE (MF codes al PDF)
B → C LOMLOE | no font identificada      | NO      | desconegut (falta source oficial)        | 397 C LOMLOE (codis seq incompatibles amb B)
C → D        | ciclosFP endpoint         | SÍ      | M (1 crida REST/C LOE, ràpid)           | ~579 C LOE → cicles D (validat: COML0110→3006)
D → E        | no font identificada      | NO      | desconegut (todofp.es no exposa relació) | 195 D, 36 E (cap referència creuada trobada)

NOTES ADDICIONALS:
- A→B: El pla esperava 8730 A→B però el regex del pla (FAM_A_NNNN_PP) captura 5858 LOMLOE.
  Els 2872 restants són registres LOE amb format UF####, que sí que es mapegen via UF→MF (93% cobertura).
- B→C LOE via fichaCP HTML: fichaCP retorna pàgina de navegació sense UC. La font real és el PDF Anexo.
- ciclosFP regex (d{4}\\s*-) captura fals positiu: 0110 del codi cert COML0110. Real match: 3006->ADG_B_3006/COM_B_3006.
- D ficha_url (todofp.es): pàgina de 188 línies, zero referències a certificats C o codis CP.
=== FI CONCLUSIONS ===
""")
