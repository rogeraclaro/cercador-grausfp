# 075 — Millores UX/a11y del cercador (revisió externa)

**Prioritat:** P2 · **Esforç:** S-M · **Depèn de:** — · **Estat:** DONE (2026-10-25)
**Origen:** anàlisi UX/UI externa (2026-10-25), verificada contra el codi. Descartats: `aria-sort` (ja existeix, `index.html:3197`) i botó "Cercar" (la cerca és instantània; un botó faria creure que cal prémer-lo).

Tot és frontend (`frontend/index.html`, `frontend/i18n.js`, `frontend/feedback.js`, `frontend/site.css` si cal). Cap canvi de backend. Cada canvi d'i18n: bump `i18n.js?v=` a les 14 pàgines.

## 1. Etiquetes ocultes dels filtres traduïdes

`index.html:2996` i `:3004`: `<label class="sr-only">Família</label>` / `Nivell` estan escrites a mà. Afegir `data-i18n` amb claus noves `index.filter.fam.label` (Família / Familia) i `index.filter.niv.label` (Nivell / Nivel). Repassar la resta de `<label class="sr-only">` d'`index.html` (mode FPO) amb el mateix criteri.

## 2. CA/ES indiquen quin és actiu

`i18n.js:1425`: a més de `lang-btn--active`, posar `aria-pressed="true|false"` a cada `.lang-btn`.

## 3. Filtre "Favorits" usable amb teclat

`index.html` (~3027): l'`<input type="checkbox" tabindex="-1">` dins un `<label @click.prevent>` no es pot activar amb el teclat. Substituir per un `<button type="button" aria-pressed>` amb el mateix aspecte (casella + cor + "Favorits"), mateix comportament (anònim → modal de registre; registrat → alterna `filterFavs` i `resetPage()`), focus visible amb l'outline compartit.

## 4. Pestanya "Feedback" → "Suggeriments"

`fb.tab`: CA "Suggeriments", ES "Sugerencias". Afegir `aria-label` a la pestanya amb una clau nova `fb.tab.aria` ("Envia'ns un suggeriment o avisa'ns d'un error" / "Envíanos una sugerencia o avísanos de un error"). Comprovar que la pestanya vertical no es talla amb el text més llarg (desktop i mòbil).

## 5. Paginació: 100 files i primera/última

- `pageSize: 50` → `100` (`index.html:1801`). Comprovar que la fluïdesa es manté (render de 100 files amb panells tancats).
- Botons "« Primera" i "Última »" a la paginació del mode nom (i FPO si comparteix component), deshabilitats quan toca, amb `aria-label` i claus i18n.
- Corregir PRODUCT.md, que diu 200 files per pàgina.

## 6. "Sense centres registrats" quan el recompte és 0

`index.html:3271`: quan `centres_count(row) === 0` (i el recompte ja s'ha carregat), mostrar un text discret en Umber, no clicable: "Sense centres registrats" / "Sin centros registrados" (clau `index.centres.none`). No una píndola: no hi ha res a obrir.
Cobertura a producció (2026-10-25): tots els graus tenen dades (A/B per herència, C/D/E del Registre Estatal); amb 0: A 2.187/5.953, B 374/1.019, C 141/400, D 12/195, E 11/38, etc. "Registrats" és precís: no afirma que no se n'imparteixi enlloc.
No mostrar res mentre `/api/centres/count` no ha respost (evitar un "Sense centres" fals en carregar).

## 7. Cor de favorits visible a l'ordinador

`.btn-fav` (`index.html:931`) té `opacity: 0` fins al hover. Deixar-lo sempre visible a opacitat reduïda (p. ex. contorn en Faded Ink), ple en hover/actiu com ara. Anònim: clicar → modal de registre (ja funciona). Verificar que no fa soroll visual a la taula (captura abans/després).

## 8. Un sol botó d'alertes a la barra

Treure l'enllaç "Veure alertes" (`index.html:3038`) de la barra de filtres; queda "Desa com a alerta" quan hi ha filtres. Accés a les alertes: "El meu perfil" → pestanya Alertes, i el modal de confirmació en desar-ne una ("Veure les meves alertes"). Si la clau `index.btn.alerts` queda sense ús, esborrar-la (CA i ES).

## Verificació

- Captures desktop (1280) i mòbil (375) del cercador en CA i ES: filtres, fila amb 0 centres, cor, paginació, pestanya Suggeriments.
- Teclat: Tab fins a Favorits i activar amb Espai/Enter; CA/ES amb `aria-pressed` correcte.
- Detector d'Impeccable un cop sobre `index.html`.
- Deploy: frontend sol (push + `git pull` al VPS), sense reiniciar.

## STOP conditions

- Si 100 files per pàgina fa que la pàgina vagi visiblement més lenta en un mòbil (render > ~200 ms), quedar-se a 50 i informar.
- No tocar el modal d'alertes (comparteix classes amb el de registre).

## Resultat (2026-10-25)

- Fets: 1, 2, 3, 4, 6, 7, 8.
- Punt 5: **es queda a 50 files** per la STOP condition: canviar de pàgina tardava ~240 ms amb 100 files i ~160 ms amb 50 (ordinador). Els botons "Primera/Última" no s'han afegit: `buildPagination` ja mostra sempre la pàgina 1 i l'última. PRODUCT.md corregit a 50.
- Punt 1: reutilitza les claus `fpo.filter.familia` i `fpo.filter.nivell` (sense claus noves).
