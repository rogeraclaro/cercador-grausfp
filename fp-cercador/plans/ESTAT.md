# Estat del projecte — per reprendre des d'un altre ordinador

Última actualització: 2026-11-14. Producció: https://grausfp.es (VPS `contabo`) a `79889dd`
(auditoria en dues passades i pla 081 desplegats el 2026-11-14; `sepe_especs.json` copiat des de local).

## Com reprendre

1. `git clone https://github.com/rogeraclaro/cercador-grausfp.git`. El projecte és a `fp-cercador/`; l'arrel
   del git és la carpeta pare.
2. Les dades (`fp-cercador/backend/data/*.json`) **no són al git**. Cal copiar-les del VPS:
   `scp contabo:/home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/{ofertes,c_modulos,d_modulos,bc_lomloe}.json fp-cercador/backend/data/`
3. El `.env` tampoc no és al git (ADMIN_TOKEN, SMTP, Google OAuth…): copiar-lo a mà del VPS.
4. Tests: `cd fp-cercador/backend && python3 -m pytest tests -q --deselect tests/test_pipeline.py::test_ce_acces_falla_conserva_fitxer_anterior`
   (749 verds el 2026-11-15 amb `--ignore=tests/test_pipeline.py`, que fa peticions de xarxa i es penja
   sense connexió).
5. Local: `python3 app.py` (port 5001) i `python3 -m http.server 8765` dins `frontend/`.

## Deploy (sempre amb l'aprovació explícita del propietari)

`git push cercador-grausfp master`, i després
`ssh contabo 'cd /home/masellas-grausfp/htdocs/grausfp.masellas.info && git pull --ff-only'`.
- Si toca el backend: `systemctl restart fp-cercador`. **Mai diumenge 11:10–11:45**, que és quan corre el
  refresc setmanal.
- Si es canvien textos o `auth.js`/`alertes.js`: apujar la versió `?v=` a totes les pàgines i a
  `I18N_VERSION` de `backend/grau_page.py` (ara `20261115b`; `site.css?v=5`, `footer.js?v=3`).
- Commits: conventional commits, sense atribució d'IA.

## Fet els darrers dies (tot desplegat)

| Què | Commits | Detall |
|---|---|---|
| Botó "Compartir" a cada fila desplegada del cercador | — | `index.html`; sempre al final de la línia |
| Pla 078 — tots els mòduls dels C LOMLOE (també els sense Grau B) | 0525eb9…ee4dda4 | `c_modulos.json`, notes art. 58.3 / neutra / altra família, recompte C→D |
| Pla 079 — 11 mòduls que 10 fitxes todofp ometen, completats amb el BOE | 0ed38f2…a09712c | `_C_MODULOS_BOE_AFEGITS`, `_C_MODULOS_NO_AL_DECRET` (IMA_C_001_4B 0266) |
| Pla 080 — els 400 C auditats contra el seu decret del BOE | f63b5f1…ebf76dc | `--discover` (sumari diari del BOE), RD individuals i de títol; nota `uc_sense_b` |

Detall i proves: `plans/078-*.md`, `plans/079-*.md`, `plans/080-*.md` i `plans/outputs/audit_c_modulos_boe.md`.
Tornar a fer l'auditoria: `python3 scripts/audit_c_modulos_boe.py [--discover] --cache DIR --data DIR`.
La primera vegada, `--discover` triga ~20 min; després va de la memòria cau.

## Pendent

### Dels plans 078–080 (C LOMLOE)
- **SEA_C_004_5B i SEA_C_006_5B, mòdul 1782.** Probablement associat a UC1970_2 (PRL en incendis
  forestals), però el decret de grup (RD 211/2025) no té taula mòdul↔UC. Mantenen la nota de l'art.
  58.3 fins que hi hagi prova. Si se'n troba, s'afegeixen a `_C_MODULOS_UC_SENSE_B` (`backend/app.py`).
- **Avisar el ministeri** (decisió del propietari):
  - les 11 fitxes todofp incompletes (taula a `plans/079-*.md`);
  - el forat del catàleg HOT_C_003_5B → HOT_B_0178;
  - els 36 "catàleg de més" (inofensius).
- **Automatitzar la detecció.** Executar `--discover` quan aparegui un C nou al catàleg; ara és manual.
  Sense aquest pas, un C nou queda sense auditar.
- **Tests:** `test_refs_api.py` i `test_grau_page.py` no aïllen `C_MODULOS_PATH` (passen igualment).
  `test_ce_acces_falla_conserva_fitxer_anterior` falla des d'abans del 078.

### Auditoria 2026-11-14 (desplegada)
- Correccions aplicades i llista del que queda per decidir: `.planning/quick/261114-ekq-*/261114-ekq-SUMMARY.md`.

### Pla 083 «Què em falta?» — fet i desplegat el 2026-11-14 (prod `8b4418a`)
- `backend/gap.py`, `POST /api/que-em-falta`, `GET/PUT /api/held`, migració `013_user_held.sql`,
  `frontend/que-em-falta.html`, `frontend/held.js`, botó «Ja el tinc» al cercador i a l'itinerari, enllaç a
  la barra i al peu. 624 tests verds.
- Vhost d'nginx: `que-em-falta` afegit a mà a l'expressió regular de pàgines del bloc `?lang=es` (línia 80).
  Còpia d'abans a `/root/grausfp.masellas.info.conf.bak-20261114`. Si CloudPanel regenera el vhost, cal
  tornar-lo a afegir.
- Decisions preses en executar (revisables):
  - Un cicle D que ja es té també cobreix els Graus B dels seus mòduls (el pla només ho deia per als C).
  - Noms de mòdul que canvien amb el nivell («Inglés profesional» 0156/0179, «Maquillaje»…) només casen
    amb el mateix nivell.
  - La nota «Incluye una fase de formación en empresa…» de `d_modulos.json` (184 cicles) no es compta com a
    mòdul; el «Módulo profesional optativo» compta al total però no casa entre cicles.
  - Convalidacions segons el RD 659/2023, art. 126 (verificat al text consolidat del BOE): el Proyecto
    intermodular i la formació en empresa no casen mai entre cicles (126.4); Inglés profesional només entre
    cicles del mateix grau; Digitalización i Sostenibilidad només dins el mateix grau i la mateixa família
    (126.3); Itinerario personal I i II casen entre qualsevol oferta (126.5).
- Sense verificar: «Tutoría» (grau bàsic) casa entre cicles pel nom; l'art. 126 no en diu res.

### Pla 084 «Mode orientador: llistes compartibles» — fet i desplegat el 2026-11-14
- Commits `33f4f8a` (favorits a part, migració `014_shared_lists.sql`), `2355294` (API) i `79392a1` (pàgines).
- `GET/POST /api/lists`, `GET/PATCH/DELETE /api/lists/<id>`, `PUT/DELETE /api/lists/<id>/items/<ref>`,
  `POST/DELETE /api/lists/<id>/share` i la pública `GET /api/llista/<token>`; `frontend/llistes.html`
  (editor), `frontend/llista.html?t=<token>` (vista de només lectura, impressió amb QR), botó «+ Llista» al
  cercador, enllaç al perfil, `frontend/vendor/qrcode-generator-2.0.4.js`. 668 tests verds.
- Desplegat amb la migració 014 aplicada; còpia de la BD d'abans a
  `/root/fp_cercador.db.bak-20261114-pre084` (al VPS). No ha calgut tocar el vhost: les dues pàgines són `noindex` i no entren al sitemap ni al bloc `?lang=es`.
- Decisions preses en executar (revisables):
  - **«+ Llista» és un botó propi** al costat de «Compartir», no una opció dins del seu menú: en pantalles
    tàctils «Compartir» obre el menú del sistema i el menú propi no surt mai, de manera que l'opció no s'hi
    hauria pogut fer servir.
  - **Límit per IP de la vista pública:** només compten els tokens que no existeixen (20 per hora); quan una
    IP el gasta, rep 429 a tot fins que passa l'hora. Amb `_auth_rate_ok` tal qual, una classe de més de 20
    alumnes darrere la IP de l'escola s'hauria quedat sense poder obrir l'enllaç.
  - **Tornada del login a la llista:** el token es desa a `sessionStorage` i `next=llista.html`; no s'ha
    tocat la validació de `next` de `login.html`. Després d'entrar cal tornar a prémer «Desa'ls».
  - La llibreria es vendoritza **sense minificar** (57 kB): el paquet d'npm no porta `.min.js` ni fitxer de
    llicència; la capçalera declara MIT i el text és a `qrcode-generator-2.0.4.LICENSE.txt`.
  - `llista.html` porta `<meta name="referrer" content="same-origin">` perquè el token no surti cap a
    altres webs; l'analítica ja exclou la cadena de cerca.
  - Superar els 30 graus d'una llista torna 429, com el límit de llistes.
- Verificat al navegador (ca i es, 1280 i 375 px): crear, afegir tres graus des del cercador, anotar,
  compartir, obrir sense sessió, imprimir, QR descodificat, desar a favorits, regenerar i enllaç antic
  caducat. Sense provar: el QR amb un mòbil de veritat i el diàleg d'impressió real (només `@media print`).

### Pla 085 «Comparador de graus» — fet i desplegat el 2026-11-15
- `backend/compare.py` (`build_comparison`), `GET /api/compara?refs=a,b,c`, `frontend/compara.html`, botó
  «Compara» i barra fixa al cercador (`index.html`), enllaç «Compara amb un altre grau» a `/grau/<ref>` i a
  `itinerari.html`. Sense migració. 690 tests verds.
- Desplegat amb reinici del servei; no ha calgut tocar el vhost (la pàgina és `noindex`).
- `_grau_context` triga ~0,1 ms per grau amb les dades de producció: no ha calgut optimitzar res.
- Decisions preses en executar (revisables):
  - **«Compara» és un botó dins la fila desplegada**, al costat de «Compartir» i «+ Llista», a totes les
    mides: una columna nova no hi cabia a les targetes del mòbil. Cal desplegar el grau per triar-lo.
  - L'API afegeix `moduls_propis` a cada grau (els no comuns), perquè la pàgina no hagi de repetir la
    normalització de noms.
  - Els mòduls comuns són per nom normalitzat, sense les regles de convalidació de l'art. 126 del pla 083:
    «Proyecto intermodular» o «Módulo profesional optativo» surten com a comuns si tots dos cicles en tenen.
    La nota «Incluye una fase de formación en empresa…» no es compta com a mòdul.
  - «Comparteix» a l'ordinador copia l'enllaç directament (sense menú de WhatsApp i correu).
  - Els graus triats es desen a `sessionStorage` amb clau pròpia (`grausfp.compareRefs`), no dins de
    `saveListState()`: així sobreviuen a qualsevol navegació de la pestanya.
- Verificat al navegador (ca i es, 1280 i 375 px): dos D de la mateixa família (6 mòduls comuns), C del pla
  nou amb el seu D (3 de 4), A + D (sense bloc de comuns), C pla antic + B, tres columnes, treure columna,
  comunitat autònoma, plegat de llistes, copiar l'enllaç, estats buit i invàlid, `?compara=`, límit de 3.
  Sense veure en dades reals: el ressaltat d'ocupacions i de «a què dona pas» comuns (cap parella provada
  en tenia); la lògica és als tests de `compare.py`.

### Pla 086 «Calendari FPO» — fet el 2026-11-15, **sense desplegar**
- Agenda: `backend/fpo_agenda.py`, `GET /api/fpo/agenda?dies=` i la vista «Comencen aviat» del mode FPO
  (`index.html?mode=fpo&vista=agenda`), amb filtres de comarca, modalitat, família i tipus.
- Calendari: `frontend/ics.js` (botó «Afegeix al calendari» a l'agenda i al detall d'una especialitat).
  Proves del format: `node --test scripts/test_ics.js` (10).
- Alertes: migració `015_fpo_alerts.sql`, `/api/fpo/alerts` (CRUD i baixa per enllaç),
  `backend/fpo_alerts_service.py`, botó «Avisa'm de cursos nous» a l'agenda i llista a `perfil.html#fpo`.
  749 tests verds.
- Per desplegar: push, `git pull` i **reiniciar** `fp-cercador` (aplica la migració 015). El primer correu
  d'alerta sortirà amb el refresc següent en què aparegui un curs nou per a algú amb una alerta.
- Els dos camins de refresc de l'FPO (setmanal a `pipeline.run` i manual a `app._run_fpo_refresh`) fan el
  mateix: `pipeline.fpo_snapshot` abans i `pipeline.notify_fpo_new_courses` després (55 línies noves a
  `pipeline.py`, sense reestructurar-los). Una font que falla conserva el seu snapshot i no dona cursos nous;
  una font sense snapshot anterior tampoc.
- Decisions preses en executar (revisables):
  - **El correu d'alerta és en català**, com la resta de correus (no hi ha idioma desat per usuari).
  - **Baixa amb token dolent o caducat:** redirigeix a `/?unsubscribe_error=1`, amb un avís nou a `auth.js`.
    La baixa pausa l'alerta, no l'esborra.
  - L'alerta des de l'agenda desa la comarca i la família triades i sempre inclou els cursos en línia; l'API
    també accepta `espec_codi` i `inclou_en_linia: false`, però cap botó els envia encara.
  - Amb una comarca triada, l'agenda mostra també **tots** els cursos en línia (decisió del pla): a Bages
    surten 2 cursos presencials i 50 en línia.
  - `perfil.html` ara obre la pestanya del `#` de l'adreça (`#fpo`, `#alertes`, `#seguiment`); abans no ho
    feia i l'enllaç «Gestiona les alertes» no hi hauria arribat.
  - `_get_or_create_unsubscribe_token` d'`alerts_service.py` accepta ara el tipus de token, per no duplicar-lo.
- Verificat al navegador amb dades del VPS del 2026-11-15 (228 cursos en 90 dies, 220 sense data), ca i es,
  1280 i 375 px. **Sense provar:** importar el `.ics` a un calendari de veritat (només n'he validat el format
  i el fitxer baixat) i l'enviament real d'un correu d'alerta (als tests, `send_email` sempre substituït).

### Funcionalitats noves triades pel propietari el 2026-11-14 (plans 087–089, tots TODO)
Un pla per sessió nova. Ordre de prioritat del propietari:
- 088 pàgines de família enriquides ·
  087 filtres a l'adreça i «Volies dir…» · 089 reporta un error a la fitxa.
- 083–086 i 088 tenen el disseny validat pel propietari; a 087 i 089 les decisions tècniques
  són del redactor i es poden revisar abans d'executar.
- 089 afegeix una migració: el número és «el següent lliure» en executar (l'última és la 015).

### Catàleg d'Especialitats Formatives del SEPE (plans 081–082)
- 081: **fet** (commits f0a99b0, a54b18c, 7d46fee): scraper + `sepe_especs.json` + badges i filtre a l'FPO.
- 082: pàgina a part `cataleg-especialitats.html` + proxy del PDF del programa. Depèn de 081 f1–2.
- Clau: el catàleg és formació en el treball (RD 438/2024 art. 24), no Grados A–E; els CP ja no hi són.

### Fora del git a la carpeta arrel (no pujat; cal decidir-ho)
- `grausfp-launch/`: projecte de vídeo (128 MB, amb `.env` propi). No s'ha pujat perquè té un `.env` i
  pesa molt.
- `pt.log`: buit.

### Pendents anteriors (de la memòria de Claude; verificar-ne l'estat abans de fer-hi res)
- Pla 033 (observatori), previst per a ~juliol.
- Canvi de domini: `SITE_URL`, Search Console i Google OAuth.
- Pla 053: preferències d'email (TODO).
- Pla 064: UI de l'FPO extern (PIMEC/Foment). El 063 (backend) és fet.
- Política de privacitat "provisional", lligada al registre GDPR.
