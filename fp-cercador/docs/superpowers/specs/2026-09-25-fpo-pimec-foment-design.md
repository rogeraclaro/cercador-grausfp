# FPO — Cursos de PIMEC i Foment Formació

**Data:** 2026-09-25
**Estat:** disseny aprovat; plans 062, 063 i 064 escrits a `plans/`, pendents d'executar.
Les xifres d'aquest document estan verificades sobre les webs reals (2026-09-25); una
primera versió en tenia de gonfiades (vegeu §3).

## 1. Objectiu

Ampliar el mode "Cursos FPO (Catalunya)" amb dues fonts noves, **PIMEC Formació** i
**Foment Formació**, al costat del SOC. L'usuari cerca en un sol lloc; cada curs
indica la seva **font** i el seu **tipus** (Subvencionat, Bonificable, Diàleg
Social, Altres) perquè no es confongui un curs de pagament o per a empreses amb un
de gratuït.

Motiu: el SOC només publica l'oferta subvencionada oberta ara mateix. Verificat
2026-09-25 sobre el snapshot de producció (861 cursos, 240 entitats): 0 cursos de
PIMEC i 1 de Foment de Terrassa (ens municipal, no Foment del Treball).

## 2. Decisions preses

| Decisió | Elecció |
|---|---|
| On apareixen | Dins la pestanya FPO existent, amb insígnia de font i filtre "Font" |
| Tipus de PIMEC | Tots (Subvencionat, Bonificable, Diàleg Social, Altres), amb insígnia |
| Encaix al model | Una **especialitat sintètica** per títol de curs, que agrupa les edicions |
| Cursos acabats | Es mostren amb la insígnia "Finalitzat" (no s'amaguen) |
| Migració de BD | Cap |

Alternativa descartada: llista plana de cursos apart. Toca menys codi existent però
perd favorits i files desplegables, i queda com un apèndix.

## 3. Fonts de dades

Cap dependència nova: `requests` + `beautifulsoup4`.

### PIMEC (`pimecformacio.org`, Drupal)

- Endpoint: `GET https://pimecformacio.org/ca/formacio-inici/ajax` amb els paràmetres
  `paraula_clau=`, `field_fo_tipus[]=<tipus>` (repetit per als 4 tipus) i
  `formacioPagina=<n>`. Retorna JSON `{data, listcursos, paginador, formulari,
  formacioPagina}`; `listcursos` és l'HTML de 12 targetes. Sense captcha ni cookies;
  `robots.txt` sense restriccions.
- **El `paginador` no es pot creure:** anuncia 19 pàgines i n'hi ha 35. Hi ha **417
  cursos**, no ~228 (xifra d'una primera versió, errònia). Es pagina fins a una pàgina
  sense targetes.
- Per targeta: títol, enllaç a la fitxa, tipus, dates (`28 set. - 26 oct. 2026`),
  hores (`30h`, a vegades decimals), població + modalitat. **L'àrea no surt a la
  targeta**: s'obté escanejant un cop per cada àrea del filtre `field_fo_area[]` (17
  àrees; 320 de 417 cursos en tenen una).
- Distribució: 204 Subvencionat, 163 Altres, 38 Diàleg Social (Subvencionat),
  12 Bonificable. **160 cursos (tots "Altres") són "Dates a concretar" i sense lloc**:
  només 257 tenen dates.
- Els valors reals de `field_fo_tipus` són `Altres`, `Bonificable`,
  `Diàleg Social (Subvencionat)` i `Subvencionat`.

### Foment (`fomentformacio.com`, WordPress)

- Sitemap `https://www.fomentformacio.com/curso_foment-sitemap.xml`: 286 URL (castellà +
  català duplicades). Es fan servir només les fitxes en castellà (`/formacion/...`).
  **27 d'aquestes URL porten un fragment `#edicion-...` i són la mateixa pàgina: hi ha
  114 pàgines úniques** (una primera versió comptava 141 per no treure el fragment).
- **Cada fitxa té 1–4 edicions** (`[data-edition]`): 114 pàgines → **150 edicions**
  (134 actives, 16 ja finalitzades). Cada edició porta Centro (amb coordenades),
  Comienzo, Final, Horario (opcional) i Horas. La modalitat surt del prefix de l'id
  d'edició (`presencial`/`online`/`virtual`).
- Foment no publica un tipus per curs: es fixa `Altres`. Només 5 de 110 títols
  porten codi de certificat.
- `robots.txt` sense restriccions.
- El codi de certificat del títol i el del slug poden no coincidir (`ADGG0208` vs
  `adgd0208`); la família es deriva del títol.

## 4. Model de dades

- Fitxer nou `data/ext_cursos.json`: cursos externs (una edició per element) amb el
  mateix format que `soc_cursos.json` més `font` (`pimec` | `foment`), `tipus`, `area`,
  `certCodi`, `fitxaUrl` i `horariText`. `idCurs` = `PIMEC:<slug>` /
  `FOMENT:<slug>:<id-edició>`.
- **Especialitat sintètica:** el backend agrupa les edicions per títol normalitzat i
  genera un codi `PIMEC:<slug-títol>` / `FOMENT:<slug-títol>` (sense `/`, perquè la
  ruta `DELETE /api/fpo/favorites/<codi>` no admet barres). S'afegeixen a
  `/api/fpo/especialitats` amb `font` i `tipus`.
- **Família:** s'assigna una família del SOC per no barrejar dos vocabularis.
  - PIMEC: diccionari àrea → família (17 àrees). Sense mapa → **FCO** ("Formació
    complementària", família real del SOC; no s'inventa una família "Altres").
  - Foment: tres primeres lletres del codi de certificat del títol (ADGG0208 → ADG).
    Sense codi → FCO. **Limitació coneguda:** només 5 títols porten codi, així que la
    majoria de Foment caurà a FCO i no es podrà filtrar per família.
- **Estat:** els externs no tenen equivalent fiable de l'estat del SOC
  (inscripció/informació/gestió), així que no es mostra aquest estat. L'únic estat
  que es deriva és **`finalitzat`**: un curs extern amb `dataFi` anterior a avui es
  mostra amb la insígnia "Finalitzat" (no s'amaga ni es filtra). Es calcula **en
  llegir**, no en fer el scraping, perquè no quedi com a actiu entre dos refrescos.
  S'aplica a PIMEC i Foment. Dins d'una fila, les edicions finalitzades van al final.

## 5. Pipeline i errors

- Bloc no fatal nou al pipeline, com el del SOC, amb historial i avís d'admin (màxim
  1 per dia per font). Cada scraper és independent. També es refresca des de
  `POST /api/admin/refresh-fpo`. Les entrades van a `soc_refresh_history.json` amb el
  camp `font`, i `historial.html` mostra una columna "Font".
- Snapshot segur: si un scraper retorna 0 cursos o menys de la meitat dels anteriors,
  no se sobreescriu el snapshot antic d'aquella font; s'anota l'error i s'avisa l'admin.

## 6. Favorits

- Cap migració: `fpo_favorites.especialitat_codi` i `fpo_favorite_courses.curs_id`
  són `TEXT` sense clau forana, i el `POST` no valida el codi contra el catàleg.
- Cal ampliar `_fpo_espec_by_codi`, `_fpo_curs_by_id` i `_fpo_fav_course_public`
  (`backend/app.py`) perquè busquin també al snapshot extern i no usin l'enllaç del SOC.
  Sense això, un favorit de PIMEC/Foment es veuria sense títol i els seus cursos
  sortirien com a "finalitzats".

## 7. Frontend (`index.html`, `i18n.js`, `perfil.html`, `fonts.html`, `historial.html`)

- Insígnies de **font** i **tipus** a cada fila i a cada edició (a les files SOC, només
  la de font).
- Dos filtres nous a la barra FPO: "Font" i "Tipus". Per defecte, tot visible.
- Detall d'edició: enllaç a la fitxa oficial de PIMEC/Foment; s'amaguen "Fitxa al
  SOC" i l'estat del SOC; "Dates a concretar" quan no hi ha dates; horari en text.
- Claus i18n noves en català i castellà; la nota de la pestanya deixa de dir que és
  només SOC. Atenció als literals dins `x-text` d'Alpine.
- Perfil (`perfil.html`), `fonts.html` (dues seccions noves) i `historial.html`
  (columna "Font").

## 8. Proves

- TDD al backend (plans 062 i 063): parsers amb HTML/JSON escrit a mà amb l'estructura
  real, agrupació, mapes de família, endpoints, favorits, hook d'admin.
- Frontend (pla 064): sense suite de UI; llista de comprovacions manuals a la Fase 6.
- **Prova en sec feta (2026-09-25):** el codi dels plans s'ha executat sobre una còpia
  temporal: 63 tests passen i, amb les pàgines reals baixades, els scrapers donen 417 de
  PIMEC i 150 de Foment; l'API i el renderitzat d'Alpine (filtres, files, edicions,
  insígnies) funcionen. La prova va destapar tres defectes als plans, ja corregits:
  `datetime` ambigu a `app.py`, un test amb l'esperat incomplet i les URL de Foment amb
  fragment.

## 9. Fora d'abast

- Integració dels cursos externs amb els certificats C (`/api/fpo/by-cert`).
- Cerca per ocupació.
- Altres entitats formadores.
- Millorar la família de Foment amb paraules clau del títol.

## 10. Preguntes obertes

- Mapa àrea → família de PIMEC: és una proposta (pla 063); l'usuari el pot ajustar.
- Els 160 cursos "Altres · dates a concretar" de PIMEC entren igualment (decisió:
  importar tots els tipus); es poden amagar amb el filtre Tipus.
- Les files SOC porten `tipus: ['Subvencionat']` (**suposició**, sense insígnia).
- Una fila sencera de cursos finalitzats no s'atenua: decidir si molesta.
