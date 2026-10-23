# 073 — Itinerari: pestanya "Graf" interactiu (Cytoscape.js) amb exploració

**Prioritat:** P3 · **Esforç:** M · **Depèn de:** 071, 072 · **Estat:** DONE
**Spec:** `docs/superpowers/specs/2026-10-23-itinerari-visual-design.md`

## Objectiu

A `itinerari.html`, **només a l'ordinador**, una pestanya **Timeline | Graf**. El graf mostra el mateix itinerari com a nodes i arestes, es pot **arrossegar i fer zoom**, i permet **explorar**: doble clic en un node hi afegeix els seus veïns directes (`/api/itinerari/complet?...&depth=1`), de manera que la xarxa creix. El mòbil no ofereix aquesta pestanya.

## Excepció de llibreria (decidida pel propietari)

El `CLAUDE.md` del projecte diu "vanilla + Alpine, no afegir-ne cap altre". El propietari ha aprovat **Cytoscape.js** com a segona excepció. Abans de codificar:
1. Vendoritza `cytoscape.min.js` a `frontend/vendor/cytoscape-<versió>.min.js` (versió **3.x exacta i estable, publicada fa més de dues setmanes**; anota la versió i l'origen). Sense CDN, com Alpine.
2. Actualitza el `CLAUDE.md` (secció *Constraints → Tech Stack*) afegint l'excepció: "Cytoscape.js 3.x vendoritzat, només a `itinerari.html`".
3. Carrega'l **només** a `itinerari.html`, i preferiblement en entrar a la pestanya Graf (no en carregar la pàgina), perquè la vista per defecte no en pagui el pes.

## Comportament

- Nodes acolorits per grau (mateixos colors que el timeline), etiqueta curta (codi o denominació retallada), node focus destacat. Etiqueta "pla antic" com a estil (p. ex. vora discontínua).
- Disposició: per nivells (A a l'esquerra … E a la dreta) per mantenir la lectura del timeline — `preset` amb x per grau o `breadthfirst`; prova-ho amb `ADG_C_001_3B` i un A LOE amb molts pares, i tria la que es llegeixi millor.
- **Clic** = mostrar detall (denominació, família, enllaç a la fitxa via `node.ficha`) i botó "Centrar aquí" (recentra tota la pàgina com al timeline). **Doble clic** = afegir veïns (sense duplicar nodes ni arestes; anima l'aparició amb `prefers-reduced-motion` respectat).
- Límit de seguretat: si el graf supera ~300 nodes, avisa i no n'afegeixis més (botó "Reinicia").
- Seguretat: les etiquetes de Cytoscape són text (no HTML); el panell de detall usa `x-text`/`esc()`.

## Verificació (Playwright, local)

Mateix entorn local que el pla 072. A 1440 px: la pestanya canvia de vista, arrossegar i zoom funcionen, doble clic en un B afegeix els seus altres C sense duplicats, "Centrar aquí" recentra. A 375 px la pestanya no apareix. 0 errors de consola. Comprova que `index.html` **no** carrega Cytoscape.

## STOP conditions

- Si cal cap altra llibreria (plugins de Cytoscape inclosos), para i pregunta.
