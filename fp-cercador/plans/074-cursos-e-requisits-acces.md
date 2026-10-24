# 074 — Cursos E: requisits d'accés (relació D→E) i columna E a l'itinerari

**Prioritat:** P2 · **Esforç:** M · **Depèn de:** 071 (per exposar-ho); el scraper es pot fer abans · **Estat:** DONE
**Spec:** `docs/superpowers/specs/2026-10-23-itinerari-visual-design.md`

## Objectiu

Saber, per a cada **curs d'especialització (E)**, quins **títols D** hi donen accés, i mostrar-ho a l'itinerari (columna E, que avui està amagada perquè no hi ha dades).

## Font (investigada el 2026-10-23)

- Índex: https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html (el scraper actual ja el fa servir per als registres E): 38 cursos.
- Cada registre E de `ofertes.json` té `ficha_url` = pàgina del curs, patró `/que-estudiar/familias-profesionales/{familia}/ce-{slug}.html` (36 pàgines).
- A cada pàgina, secció plegable `<div class="cdsp"><h2>Requisitos de acceso</h2>…`. Formats observats:
  - **24 pàgines**: `<ul>` on cada títol és un enllaç a la fitxa del D (`<li><a href="/que-estudiar/familias-profesionales/informatica-comunicaciones/admin-sist-informaticos-red.html">Título de Técnico Superior en …</a></li>`). → **lligar per URL** amb el `ficha_url` dels registres D (normalitzant relatiu/absolut, esquema i barra final).
  - **8 pàgines**: `<li>` sense enllaç (p. ex. `ce-comercio-electronico`, 16 títols). → **lligar per nom normalitzat** contra les denominacions D: treure "Título de"/"Título de:", punt final, espais, cua ", establecido en el Real Decreto …", i comparar sense majúscules ni accents.
  - **4 pàgines** en prosa (`ce-desarrollo-equipos-sistemas-electronicos`, `ce-fp-insecticultura`, `ce-mont-integral-mnto-bicicleta…`, `ce-floristeria-arte-floral` "…es el de Técnico en Jardinería y floristería."). → **fitxer de correspondències manual versionat** (p. ex. `backend/ce_acces_overrides.json`, `{E_ficha_url: [D_ficha_url, …]}`; **no** a `backend/data/`, que és gitignored).
  - Totes les pàgines porten després una `<ul>` sobre la via del 20% ("Si no tienes dicha titulación…") que **s'ha d'excloure**.
- Font alternativa/validació: el Real Decret de cada curs al BOE (article "Requisitos de acceso"), p. ex. https://www.boe.es/buscar/act.php?id=BOE-A-2021-7686 (IA i Big Data, 6 títols). No hi ha cap dataset obert nacional.
- Mida: 258 títols en les 32 pàgines amb llista (2–21 per curs, mediana ~6). Hi ha cursos d'accés GM i GS (marcats "(Acceso GM)"/"(Acceso GS)" a la denominació).

## Passos

1. **Scraper** `backend/scrapers/ce_acces_scraper.py` amb funcions pures de parseig (HTML → llista d'enllaços/noms), **TDD** amb fixtures HTML petites dels tres formats (inclosa l'exclusió de la llista del 20%). Les peticions a todofp amb els headers que ja fa servir el projecte (`Referer`, `User-Agent`). Mai als tests reals.
2. Resolució a ids de D: per URL → per nom → overrides. Sortida `backend/data/ce_acces.json`: `{"<E_id>": {"d_ids": [...], "unmatched": ["text del títol", …]}}`.
3. Integra-ho al `pipeline` com a **bloc no fatal** (com SOC o `b_contingut`): si falla, es conserva el fitxer anterior i es registra a l'historial/errors.
4. **Avís a l'admin**: els `unmatched` es mostren a l'estat del refresc (com els altres errors no fatals), perquè el propietari completi l'overrides.
5. Exposa la relació a l'endpoint del pla 071 (arestes `de`, i inversa E→D) i comprova que la columna E apareix a `itinerari.html` (pla 072) sense canvis de frontend més enllà de deixar de forçar-la oculta.

## Verificació

- Tests verds (`cd backend && python3 -m pytest tests -q --ignore=tests/test_pipeline.py -p no:cacheprovider`; 2 fallos coneguts a `test_db.py`).
- Execució real **una vegada** en local (36 peticions, espaiades): informa quants E tenen tots els títols lligats, quants `unmatched` queden, i deixa l'overrides inicial per als 4 casos en prosa.
- `ce-ciberseguridad-entornos-tecnologias-informacion` → 5 D (Administració de Sistemes Informàtics en Xarxa, DAM, DAW, Sistemes de Telecomunicacions i Informàtics, Manteniment Electrònic).

## STOP conditions

- Si todofp ha canviat l'estructura (cap `div.cdsp` amb "Requisitos de acceso"), para i informa.
- Si més d'un 15% dels títols queden sense lligar després de URL + nom, para i informa abans de fer l'overrides a mà.
