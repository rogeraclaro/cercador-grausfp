# Pla 101 — Pàgina pública per especialitat SEPE

Prioritat P2 · Mida L · Depèn de: 096, 099 i 100 · Idees 7, 10 i part de la 16.
Executable per un agent sense context.

## Context comú (llegir abans de començar)

- Origen: sessió del 2026-11-26, després de desplegar el pla 082 (especialitats del SEPE al cercador
  principal). El propietari va repassar 21 idees una per una; aquest pla en recull les decisions.
  Llegir primer `plans/082-cataleg-estatal-especialitats-pagina.md` (secció «Canvi de decisió») i la
  «Diagnosi tècnica» de `plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md`.
- Peces que ja existeixen (pla 082): `backend/scrapers/sepe_scraper.py` (`build_sepe_data`,
  `fetch_programa_pdf`), `backend/app.py` (`_sepe_index`, `_sepe_llista`, `/api/sepe/especialitats`,
  `/api/sepe/programa/<codi>`), `frontend/index.html` (estat `sepe*`, getter `filteredSepe`, bloc
  `<section class="sepe-block">`, pestanya `filterGrado === 'SEPE'`), claus `sepe.*` a `frontend/i18n.js`.
- Convencions: codi, comentaris i commits en anglès (commits convencionals, sense atribució d'IA); text
  d'interfície en català i castellà a `i18n.js` (sense literals dins `x-text`); `x-if` amb una sola arrel.
- En tocar `i18n.js` cal pujar `?v=` a **totes** les pàgines de `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`. En tocar `site.css`,
  `search-tools.js`, `footer.js` o `feedback.js`, pujar el seu `?v=`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
  (tot verd el 2026-11-26: 737) i `python3 -m pytest -q tests/test_sepe_scraper.py`. Frontend:
  `node scripts/test_search_tools.js`.
- `rg` no mira `backend/data/` (és a `.gitignore`): per buscar a les dades cal `rg -uu`.
- Deploy: `git push cercador-grausfp master`; `ssh contabo`, `git pull --ff-only` al directori del site;
  si hi ha canvis de backend, `systemctl restart fp-cercador`. **Mai reiniciar durant un refresc**
  (`curl localhost:8033/api/refresh-status`). Confirmar sempre amb el propietari abans de desplegar.

## Referència

Les pàgines de grau (pla 077): `backend/grau_page.py` (`render_grau`, `_shell`, `render_sitemap`,
`STATIC_PAGES`) i, a `app.py`, `/api/grau/<path:ref>` i `/api/sitemap.xml`. nginx reescriu `/grau/…` cap a
l'API amb un bloc afegit **a mà** al vhost (`/etc/nginx/sites-enabled/grausfp.masellas.info.conf`,
gestionat per CloudPanel: si el regenera, cal tornar-lo a posar). Seguir el mateix patró, idioma i
plantilla.

## Decisions preses amb el propietari

- Adreça `/especialitat/<codi>` (codi net del pla 096; el codi antic redirigeix amb 301).
- Totes les pàgines existeixen, però **al mapa del lloc només hi entren les que tenen el programa llegit**
  (pla 100). La resta porten `<meta name="robots" content="noindex">`: milers de pàgines gairebé buides
  perjudiquen el lloc.
- Una especialitat que desapareix del catàleg conserva la pàgina un temps amb l'avís «ja no és al catàleg
  vigent» (i `noindex`), en lloc de donar 404 de cop.
- L'avís «caduca aviat» (idea 10) no necessita feina pròpia: cap especialitat caduca abans del
  2029-12-31 (3.709 hi caduquen aquell dia; la resta, 2030–2031). La pàgina mostra l'avís sola quan faltin
  menys de 6 mesos (mateixa regla que `fpoVigenciaAviat`).
- «Graus afins»: **no** anomenar així el que només és la mateixa àrea. Sí un enllaç honest «Veure els
  graus de la família …» cap al cercador filtrat. Els «graus relacionats» per ocupació es decideixen al
  pla 103.

## Contingut de la pàgina

1. Títol (`titol_mostra`; en català si el SOC el té), codi, codi antic, etiquetes (Especialitat SEPE,
   sufix, competència transversal).
2. Avís: formació en el treball; no dona cap títol ni certificat oficial.
3. Dades: família i àrea, nivell (amb l'explicació del pla 097), hores, modalitat, vigència.
4. Programa (pla 100): objectiu, mòduls amb hores, requisits d'accés, tutories presencials, «Per a què
   serveix» (vinculacions), ocupacions. Enllaç al PDF (`/api/sepe/programa/<codi>`).
5. Cursos a Catalunya, si n'hi ha (`_soc_espec_index`), amb enllaç a `index.html?mode=fpo&esp=<codi>`.
6. Entitats que la imparteixen (pla 099): carregades amb JS quan el visitant ho demana (no al servidor:
   costaria una petició al SEPE per cada visita de Google).
7. Enllaç «Veure els graus de la família …» i enllaç al cercador del SEPE.
8. «Hi ha un error en aquesta fitxa?» si el pla 098 és fet.

Dades estructurades: `Course` de schema.org amb `provider` genèric (com les de grau) només si no indueix
a pensar que és un títol oficial; si hi ha dubte, no posar-ne.

## Què s'ha de fer

- `backend/especialitat_page.py` (o ampliar `grau_page.py` si queda net): `render_especialitat(rec, ctx,
  site_url)`, reutilitzant `_shell`, `_crumbs`, `_e`, `_json_ld`.
- `app.py`: `GET /api/especialitat/<path:codi>`; 301 des del codi antic; pàgina «ja no vigent» per a codis
  que hi eren (guardar un petit `sepe_retirades.json` en detectar baixes al refresc) i 404 per a la resta.
- Mapa del lloc: afegir les especialitats amb programa llegit. Avui hi ha ~13.000 URL; amb ~7.500 més
  continua per sota del límit de 50.000 per fitxer.
- `index.html`: enllaç «Veure la fitxa completa» al desplegable SEPE (i al panell FPO).
- Pàgines de família (`render_familia`): opcional, una línia «N especialitats del SEPE d'aquesta família»
  amb enllaç al cercador filtrat.
- **nginx**: afegir `/especialitat/` al bloc de reescriptura. Abans, **còpia de seguretat del vhost** i
  deixar escrit com es desfà. Documentar-ho a `../deploy/DEPLOY.md` (arrel del repositori, fora de `fp-cercador/`) al costat del bloc de `/grau/`.

## Tests

- Render: amb programa i sense; amb cursos a Catalunya i sense; especialitat retirada; `noindex` quan
  toca; escapament HTML del text del programa (ve d'un PDF extern: tractar-lo sempre com a text).
- Sitemap: només les que tenen programa. Redirecció del codi antic.

## Verificació

- Local i producció: `/especialitat/SSCE22`, una «PO», una transversal (`CTRC0001`), una sense programa.
- Lighthouse/a11y bàsic com a les de grau. Search Console: enviar el mapa del lloc actualitzat (ho fa el
  propietari).
