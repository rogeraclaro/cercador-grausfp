---
slug: fix-scraper-pla-antic-familia-pagina
date: 2026-04-23
status: in-progress
---

# Fix scraper pla antic: família i nivell des del capçal de pàgina

## Objectiu
Corregir `pdf_scraper.py` perquè els codis de pla antic (UF/MF) llegeixin la família professional
del capçal de la pàgina del PDF (on diu "Familia Profesional") en lloc de derivar-la del prefix
del codi via PREFIX_MAP. Eliminar la deduplicació per codi quan el mateix codi apareix en
múltiples pàgines/famílies (Grados A, B i C).

## Problema
- `UF` i `MF` → PREFIX_MAP → sempre "Certificados de Profesionalidad" (INCORRECTE)
- El PDF oficial indica la família real al capçal de cada pàgina (top-left, sota "Familia Profesional")
- El nivell per codis antics Grado A i C és `None` (hauria de llegir-se del capçal de pàgina)
- Un codi com UF0044 pot aparèixer en 2 pàgines (2 famílies) però la deduplicació només en conserva una

## Canvis a `fp-cercador/backend/scrapers/pdf_scraper.py`

### 1. Nova funció `_get_familia_from_page(page)`
Afegir després de `_get_nivel_from_page`. Retalla la zona superior esquerra i busca
el text sota l'etiqueta "Familia Profesional".

### 2. Modificar `_extract_records`
- Cridar `page_familia = _get_familia_from_page(page)` per cada pàgina
- Canviar la clau de deduplicació: per codis `is_old`, clau = `(code_cell, page_familia or '')`
- Per codis `is_old`: `familia = page_familia or PREFIX_MAP.get(prefix, 'Desconeguda')`
- Per codis `is_old`: usar `page_level` per al nivell (ja funciona per Grado B; estendre a A i C)
- Canviar `records[code_cell]` → `records[dedup_key]`

## Fitxers afectats
- `fp-cercador/backend/scrapers/pdf_scraper.py` (únic fitxer)
