# 077 — Una pàgina pública per grau, sitemap i robots (SEO)

**Prioritat:** P1 · **Esforç:** M–L · **Depèn de:** 076 (ref estable) · **Estat:** DONE (2026-10-26)

## Problema

Google només veu la portada: els resultats es generen al navegador i no hi ha `robots.txt` ni `sitemap.xml`. La gent busca coses com "certificado de profesionalidad soldadura dónde estudiar" o "trabajar de auxiliar de enfermería qué estudiar", i cap grau té una adreça pròpia amb contingut que Google pugui llegir.

## Solució

Una pàgina HTML per grau, generada al servidor (Flask) a partir de les dades que ja tenim, sempre al dia sense regenerar fitxers:

- **Adreça:** `/grau/<ref>`, per exemple `/grau/ADG_C_002_3B` o `/grau/informatica-comunicaciones~informatica-oficina`. nginx reescriu `/grau/` cap a `/api/grau/` (el mateix patró que `/api/og-page`, `nginx …grausfp.masellas.info.conf:77`). Un ref inexistent dona 404 real.
- **Pàgines de família:** `/families` i `/familia/<prefix>`, amb la llista dels graus de cada família per nivell. Serveixen perquè Google arribi a totes les pàgines amb enllaços, a més del sitemap.
- **`/sitemap.xml`:** dinàmic. Inclou ~13.000 graus, les famílies i les pàgines estàtiques. `lastmod` és la data d'`ofertes.json`, per sota del límit de 50.000.
- **`/robots.txt`:** permet tot excepte `/api/`, `admin.html` i `perfil.html`, i inclou la línia `Sitemap:`. L'URL base surt de la variable `SITE_URL` (per defecte, el domini actual), així que el canvi de domini (punt 6) només en canvia el valor.

## Contingut de cada pàgina (tot el que ja tenim)

- `<h1>` amb la denominació. Etiquetes de Grau, nivell, família, codi, i "Pla antic" si s'escau.
- Un paràgraf fix per grau que explica què és, per exemple "Un Grau C és un certificat professional…". Fa que la pàgina tingui text útil encara que el grau tingui poques dades.
- Contingut específic:
  - B: competències (ECP) i resultats d'aprenentatge, de `b_contingut.json`.
  - A: els seus resultats d'aprenentatge.
  - C de pla antic: unitats de competència, de `bc_loe.json`.
  - D: mòduls, de `d_modulos.json`.
  - E: els D que hi donen accés, de `ce_acces.json`.
  - Observacions.
- **Ocupacions** relacionades, d'`ocupaciones.json`, si n'hi ha. És el contingut que més respon al "vull treballar de…".
- **Centres:** el nombre total i el desglossament per comunitat autònoma (xifres agregades). Hi ha un botó "Veure els centres" que porta a `index.html?ref=…`. La llista amb noms continua tancada per a qui no ha iniciat sessió, com ara.
- **Itinerari:** els graus relacionats directament, d'on venen i on poden continuar (`itinerary_graph`, depth 1), com a enllaços a les seves pàgines `/grau/`. També hi ha el botó "Veure itinerari complet".
- **Fitxa oficial:** no hi ha enllaç directe, per coherència amb la tanca de login. Hi surt el text "Fitxa oficial disponible amb un compte gratuït", que obre el registre.
- **Metadades:** `<title>` del tipus "<denominació> — Grado C de FP | GrausFP", `meta description` generada, `canonical`, `og:*` i JSON-LD de tipus `Course`.
- **Aspecte:** la mateixa barra superior, el peu i `site.css` que les subpàgines (patró de `fonts.html`).
- **Idioma (decisió del propietari, 2026-10-26):** el contingut de la pàgina es genera en castellà (`<html lang="es">`). És l'idioma en què busca la gent de tot Espanya, i els noms oficials ja són en castellà. La barra superior i el peu es tradueixen al català amb `i18n.js` per a qui el tingui triat. No es fa versió catalana separada.

## Passos (TDD al backend)

1. `backend/grau_page.py` amb funcions pures. Rebent el registre i els índexs, retornen l'HTML. Tot el text de dades s'escapa amb `html.escape`, sense excepcions.
   - Tests: escapament (una denominació amb `<script>` no s'executa), 404 per a un ref desconegut, contingut específic per a cada grau, enllaços de veïns, canonical i JSON-LD vàlid.
2. Rutes `/api/grau/<ref>`, `/api/familia/<prefix>`, `/api/families` i `/api/sitemap.xml`. Afegir `robots.txt` (estàtic o generat amb `SITE_URL`).
   - Capçalera `Cache-Control: public, max-age=3600`.
   - Els índexs es carreguen en memòria un sol cop i es tornen a carregar quan canvia el `mtime` d'`ofertes.json`.
3. Frontend:
   - Al panell desplegat de cada fila del cercador i a l'itinerari, un enllaç discret "Pàgina del grau", perquè Google trobi les pàgines també des del web.
   - Claus i18n noves (CA/ES) i pujar la versió `?v=`.
4. nginx al VPS, amb confirmació del propietari:
   - `rewrite ^/grau/(.+)$ /api/grau/$1 last;`, i el mateix per a `/familia/` i `/families`;
   - `location = /sitemap.xml` i `location = /robots.txt`.
   - Fer una còpia del fitxer de configuració abans, i `nginx -t` abans de recarregar.
5. Verificació:
   - 20 pàgines aleatòries de cada grau responen 200, i un ref inexistent dona 404;
   - el sitemap és vàlid (XML i nombre d'URLs = registres + famílies + estàtiques);
   - prova a mòbil i ordinador (Playwright), i Lighthouse SEO d'una pàgina de grau ≥ 95.

## Fora d'abast

- Donar d'alta el web a Google Search Console: es fa en el canvi de domini (punt 6), per indexar ja amb l'adreça definitiva. Mentrestant, Google pot anar descobrint les pàgines sol.
- Pàgines per ocupació (`/treballar-de/<ocupació>`): és una bona continuació, però va en un altre pla.

## STOP conditions

- Si una pàgina de grau tarda més de 300 ms a generar-se al servidor, aturar i informar.
- No exposar la llista de centres amb noms ni l'enllaç directe a la fitxa sense login.

## Resultat (2026-10-26)

- `backend/grau_page.py` (funcions pures, tot escapat amb `html.escape`; el JSON-LD sense `<`, `>` ni `&`) i rutes a `app.py`: `/api/grau/<ref>`, `/api/familia/<prefix>`, `/api/families`, `/api/sitemap.xml`, `/api/robots.txt`, amb `Cache-Control: public, max-age=3600`. 404 i 503 en HTML (`noindex`). `SITE_URL` (per defecte `https://grausfp.masellas.info`).
- Contingut: A (RA + ECP del B pare, mateixa funció que `/api/itinerari`), B (ECP + RA), C pla antic (UC de `bc_loe.json` amb el nom del MF), D (mòduls), E (D d'accés + requisits sense resoldre), observacions, ocupacions, centres (total igual que `/api/centres/count` + per comunitat, sense noms), veïns directes del graf (`subgraph`, depth 1). Fitxa oficial: només el text cap a `register.html`. `<base href="/">` perquè `footer.js` i `auth.js` (enllaços relatius) funcionin sota `/grau/`.
- Frontend: enllaç «Pàgina del grau» al panell desplegat del cercador i al panell de detall del graf de l'itinerari; `i18n.js?v=20261026c`.
- Rendiment (còpia de producció, 13.006 registres): 20 pàgines a l'atzar de cada grau → mediana 0,3–0,4 ms, màxim 11 ms. La primera petició després d'un refresc tarda ~450 ms perquè omple les memòries cau compartides (herència de centres ~290 ms, graf ~90 ms; les mateixes que ja fa servir `/api/centres/count`); la part pròpia del pla és ~35 ms.
- Sitemap: 13.006 graus + 28 famílies + 6 estàtiques, 1,3 MB.
- Pendent (propietari): reescriptures nginx al VPS (pas 4) i Lighthouse SEO amb l'adreça definitiva.
