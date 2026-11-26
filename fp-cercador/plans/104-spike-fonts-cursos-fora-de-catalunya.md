# Pla 104 — Investigació: fonts de cursos programats fora de Catalunya

Prioritat P3 · Mida S (investigació, sense codi de producció) · Depèn de: — · Idea 21.
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

## Per què

El propietari vol una alerta «avisa'm quan un centre d'Espanya programi un curs d'aquesta especialitat».
Avui només tenim cursos programats de Catalunya (SOC, PIMEC, Foment, Cecot, CCOO). Amb el pla 099 tindrem
entitats **autoritzades** a tot l'Estat, que no és el mateix. La teleformació hi dona un valor especial:
un curs en línia programat a Madrid el pot fer algú de Girona.

## Què se sap (2026-11-26)

- Existeix un cercador estatal de cursos del SEPE i FUNDAE dins «Experiencia Fundae» (ho diu el SEPE:
  sepe.es/noticia/SEPE/2025/Septiembre/formacion-subvencionada-sepe-colaboracion-fundae). Una web no
  oficial diu que filtra per comunitat, modalitat i família; **no verificat**.
- `www.fundae.es` no respon a peticions automàtiques (ni el 2026-09-25 ni el 2026-11-26; codi 000). No
  se sap si és un bloqueig o la xarxa: provar-ho amb un navegador real.
- Les adreces del cercador de cursos del SEPE provades el 2026-11-26 eren suposades i donen 404; cal
  trobar la bona.
- Aquest cercador no ho cobreix tot: cada comunitat convoca els seus plans i té el seu cercador (com el
  SOC). Veure també la memòria del 2026-09-25 sobre fonts FPO addicionals (FUNDAE «no respon», SEPE
  «residual a Catalunya»).

## Preguntes a respondre

1. El cercador SEPE–FUNDAE es pot llegir automàticament (endpoint, autenticació, captcha, condicions
   d'ús)? Quants cursos té? Porten codi d'especialitat, dates, modalitat, província, entitat i enllaç?
2. Quants són de **teleformació**? Si n'hi ha prou, potser no cal res més.
3. Val la pena afegir els cercadors de 2–3 comunitats grans (Madrid, Andalusia, País Valencià)? Mirar per
   a cadascun: endpoint, volum, camps, i quant de manteniment suposaria.
4. Hi ha dades obertes (datos.gob.es) amb l'oferta programada?

## Lliurable

- `plans/outputs/spike-cursos-fora-catalunya.md` amb les respostes, una mostra de dades de cada font
  viable, i una recomanació: no fer-ho / només teleformació estatal / estatal + N comunitats, amb
  l'estimació de feina. Si és viable, proposar el pla d'implementació (no escriure'l sense el vistiplau
  del propietari).

## Límits

- Només lectura i poques peticions per font. Cap descàrrega massiva en aquesta fase.
- No enviar dades del propietari ni del projecte a cap servei extern.
