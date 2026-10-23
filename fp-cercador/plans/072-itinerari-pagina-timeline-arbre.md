# 072 — Itinerari: pàgina `itinerari.html` (timeline + arbre) i resum al cercador

**Prioritat:** P2 · **Esforç:** M–L · **Depèn de:** 071 · **Estat:** DONE
**Spec:** `docs/superpowers/specs/2026-10-23-itinerari-visual-design.md` · **Maqueta:** https://claude.ai/artifact/8VUN8EBhey4EesvXa19U5d (formes A i B; el propietari pot obrir-la, una sessió nova no).

## Objectiu

Una pàgina pública `frontend/itinerari.html?grado=C&codigo=ADG_C_001_3B` (o `?grado=D&id=12776`) que mostri l'itinerari del grau amb:
- **ordinador (≥ ~760 px):** timeline de 5 columnes A·B·C·D·E (E amagada fins al pla 074), línies corbes entre elements relacionats, el focus ressaltat al centre; passar per sobre d'un element ressalta el seu camí i atenua la resta;
- **mòbil (< ~760 px):** arbre desplegable amb el focus com a arrel ("Porta a: …" a dalt, components desplegables a sota);
- botó a l'ordinador per forçar la vista d'arbre.

I al cercador (`frontend/index.html`), dins el panell de detall de cada grau A/B/C/D, una línia resum `A (4) → B (3) → [C] → D (1)` amb el botó **"Veure itinerari complet"** que obre la pàgina.

## Regles (decidides pel propietari)

- Dades: **una crida** a `/api/itinerari/complet` (pla 071). Cap altra font.
- **Clic en un element = recentrar**: torna a demanar l'endpoint per a aquell node i actualitza la URL amb `history.replaceState` (la pàgina ha de funcionar també entrant directament per URL). Al costat de cada element, enllaç petit a la **fitxa oficial** (`node.ficha`, obrir en pestanya nova, `rel="noopener"`).
- **Pla antic**: etiqueta igual que al cercador per als nodes `plan_antiguo`.
- **Columnes llargues**: 5 primers + "+N més" desplegable; ordena primer els de la mateixa `familia` que el focus, després per codi/denominació.
- **Columna E** oculta si no hi ha cap node E.
- **i18n** CA/ES amb `i18n.js` (claus noves sota `itin.*`); recorda pujar el `?v=` de `i18n.js` a totes les pàgines (vegeu commit `d5f6d30`).
- Estil: `site.css` i tokens existents (`DESIGN.md`); colors per grau consistents entre vistes. Respecta la barra superior/peu compartits (`footer.js`, `feedback.js`) com la resta de subpàgines.
- Sense llibreries noves en aquest pla (Alpine sí; les línies, SVG propi com a la maqueta).
- **Seguretat**: tot text ve de dades raspades → mai `innerHTML` amb dades sense escapar (usa `x-text` d'Alpine o `esc()`); enllaços només via `node.ficha` (ja filtrat a http(s) pel backend) i, per defensa, `safeHttpUrl` com a `index.html`.

## Passos

1. Crea `frontend/itinerari.html` (Alpine) amb estats *carregant / error / sense relacions / dades*. Estat "sense relacions": el grau es mostra sol amb un missatge clar.
2. Timeline: columnes per grau, nodes amb codi + denominació, línies SVG recalculades en carregar fonts i en `resize` (patró de la maqueta). Ressaltat del camí (ascendents + descendents del node apuntat).
3. Arbre: `<details>` per nivells a partir del focus; "Porta a" per als ascendents.
4. Breakpoint automàtic + botó "Vista arbre" a l'ordinador (recorda-ho a `localStorage` amb try/catch).
5. `index.html`: al panell de detall, quan s'obre, demana `/api/itinerari/complet` del registre (lazy, una vegada) i pinta la línia resum amb els recomptes per grau i el botó. No duplicar el que ja mostra el panell.
6. Accessibilitat: nodes focusables amb teclat, `Enter` recentra, focus visible.

## Verificació (Playwright, local)

Backend local amb BD temporal (no cal usuari: és públic): `DB_PATH=<tmp> python3 app.py` (5001) i `python3 -m http.server 8080` a `frontend/`. Comprova a 1440 px i 375 px, CA i ES:
- `ADG_C_001_3B`: 3 B, 12 A, 1 D; recentrar en un A i en el D funciona i canvia la URL;
- un A LOE amb molts pares mostra "+N més";
- un grau sense relacions mostra el missatge buit;
- 0 errors de consola; sense scroll horitzontal de pàgina al mòbil.
Atura els servidors per port en acabar i esborra captures pròpies de `.playwright-mcp/` (la carpeta és versionada).

## STOP conditions

- Si el pla 071 no està desplegat/fet, para.
- Si un itinerari real fa > ~150 nodes i la vista es torna il·legible, para i proposa un límit abans de continuar.
