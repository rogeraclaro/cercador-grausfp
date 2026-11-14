# Pla 088 — Pàgines de família enriquides

Origen: auditoria 2026-11-14, idea 6 de 9. Les pàgines ja existeixen (pla 077); el propietari
ha triat **enriquir-les amb dades, en castellà com la resta de pàgines públiques** (sense
versió en català).
Executable per un agent sense context, en una sessió nova. Depèn de: 077 DONE. Fa servir, si
ja estan fets, el pla 087 (`?familia=` a l'adreça del cercador) i el 086 (agenda FPO); si no,
vegeu «Dependències toves».

## Què fa

`/familia/<prefix>` deixa de ser només una llista de graus i passa a ser el resum d'un sector:
xifres, novetats, sortides professionals, cursos que comencen aviat i un accés directe al
cercador filtrat.

## Fets verificats (2026-11-14, no repetir)

- Rutes a `backend/app.py`: `/api/familia/<prefix>` (`familia_publica`) i `/api/families`,
  servides per nginx com a `/familia/<prefix>` i `/families`. Dades a `_get_seo_data()`:
  `seo['families'][prefix] = (familia, records)` i `seo['families_list']`.
- HTML a `backend/grau_page.py::render_familia(familia, prefix, records, site_url)` i
  `render_families`. Pàgines en castellà (`lang="es"`), escapat amb `_e`, plantilla `_shell`.
- 28 famílies en producció. Mides molt diferents: de 966 graus (Agraria) a 1 i 2
  («Mantenimiento y Servicios a la Producción», «Inteligencia Artificial y Data»).
- Sanidad té 40 graus (12 A, 12 B, 3 C, 13 D). És correcte, no un error del catàleg.
- Novetats per família: `history.compute_changes` desa `new_by_grado_meta` i, des del
  2026-11-14, `removed_by_grado_meta`, amb `{denominacio, familia, nivel}` per element.
  Les entrades antigues de l'historial no porten metadades.
- Sortides professionals per grau: `seo['ocupacions'][clau]` (vegeu `_grau_context`).
- Centres per grau: `_grau_centres(ref)` i `_get_effective_oferta_centres()`.
- Els codis de família de l'FPO del SOC són els mateixos prefixos de tres lletres (`ADG`,
  `SAN`…), més `CTR` i `FCO`, que no són famílies del catàleg.
- El cercador ja accepta `?q=…&grado=X`. `?familia=` arriba amb el pla 087.
- Memòria cau de les pàgines públiques: `_SEO_CACHE_CONTROL`. Tests: `tests/test_grau_page.py`.

## Què s'hi afegeix (per ordre a la pàgina)

1. **Resum en xifres**, sota el títol: graus per lletra (A–E), amb enllaç a cada secció;
   «N centros la imparten en M comunidades»; data de l'última actualització.
2. **Botó «Buscar en esta familia»** → `/index.html?familia=<nom>`.
3. **Novedades**: fins a 8 altes i baixes recents de la família, amb data, tretes de
   l'historial. Si no n'hi ha cap amb metadades, la secció no surt.
4. **Salidas profesionales más frecuentes**: les 12 ocupacions que més es repeteixen entre
   els graus de la família, cadascuna amb enllaç a `/index.html?mode=ocupacio&q=<ocupació>`
   (comproveu que el mode ocupació llegeix `q`; si no, afegiu-ho aquí).
5. **Centros por comunidad autónoma**: taula amb el nombre de centres diferents que
   imparteixen algun grau de la família a cada comunitat, ordenada de més a menys.
6. **Cursos FPO que empiezan pronto (Cataluña)**: fins a 6 cursos de l'FPO d'aquesta família
   que comencen en 60 dies, amb data, municipi i enllaç; i «Ver todos» cap al mode FPO.
7. **La llista de graus actual**, sense canvis, al final.

Cada bloc només surt si té dades. Les famílies d'1 o 2 graus han de quedar bé amb tres blocs.

`/families`: a cada família, a més del recompte total, el desglossament «A 12 · B 12 · C 3 ·
D 13».

## Arquitectura

- Mòdul nou i pur `backend/familia_stats.py`:
  `build_familia_stats(records, ocupacions, oferta_centres, centres_index, history, fpo_cursos,
  avui) -> dict`. Sense Flask ni fitxers: rep les dades i torna un dict.
- `_get_seo_data()` calcula i desa les estadístiques de totes les famílies quan es
  reconstrueix (ja té memòria cau per mtime). El bloc FPO depèn de la data: es calcula a
  part amb memòria cau per dia.
- `render_familia` rep un paràmetre nou `stats` (opcional: sense ell, pinta com ara, i els
  tests antics continuen passant).
- JSON-LD: afegir `numberOfItems` a l'`ItemList` si la pàgina ja en té; no inventar tipus
  nous.

## Dependències toves

- **Sense el pla 087**: el botó «Buscar en esta familia» necessita que `index.html` llegeixi
  `?familia=`. Si el 087 no és fet, afegiu només aquesta lectura (validada contra
  `families`), res més.
- **Sense el pla 086**: per al bloc FPO, filtreu directament `soc_cursos.json` per
  `familia.codi` i `dataInici`; si el 086 és fet, reutilitzeu `fpo_agenda.build_agenda`.

## Fases

1. `familia_stats.py` + `tests/test_familia_stats.py`, tests primer: recomptes, centres
   diferents per comunitat (un centre que imparteix tres graus compta un cop), ocupacions
   més freqüents amb empats, novetats amb i sense metadades, FPO dins i fora de la finestra,
   família sense res de res.
2. Integració a `_get_seo_data` i `familia_publica`; mesura del temps de reconstrucció (ha de
   continuar per sota d'1 s amb el catàleg sencer).
3. `render_familia` i `render_families` + tests a `test_grau_page.py`: cada bloc surt i
   s'amaga quan toca, tot el text escapat, enllaços correctes.
4. Estils dins de la plantilla `_shell` (o `site.css` si ja els comparteix), seguint
   `DESIGN.md`. Sense JavaScript nou: les pàgines públiques han de funcionar sense.
5. Verificació: suite verda; al navegador `/familia/SAN`, `/familia/AGA` (la més gran) i una
   d'1 grau; 375 px; validar el JSON-LD; `Lighthouse` de SEO sense regressions.

## STOP — atura't i pregunta

- Si calcular els centres per comunitat de totes les famílies puja la reconstrucció de
  `_get_seo_data` per sobre d'1 s, ensenya la mesura abans d'optimitzar.
- Si cal tocar nginx: còpia de seguretat, com desfer-ho i aprovació del propietari.
- No desplegar sense aprovació explícita. Mai reiniciar diumenge 11:10–11:45.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
