# Estat del projecte — per reprendre des d'un altre ordinador

Última actualització: 2026-11-14. Producció: https://grausfp.es (VPS `contabo`) a `3f2c303`
(auditoria en dues passades i pla 081 desplegats el 2026-11-14; `sepe_especs.json` copiat des de local).

## Com reprendre

1. `git clone https://github.com/rogeraclaro/cercador-grausfp.git`. El projecte és a `fp-cercador/`; l'arrel
   del git és la carpeta pare.
2. Les dades (`fp-cercador/backend/data/*.json`) **no són al git**. Cal copiar-les del VPS:
   `scp contabo:/home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/{ofertes,c_modulos,d_modulos,bc_lomloe}.json fp-cercador/backend/data/`
3. El `.env` tampoc no és al git (ADMIN_TOKEN, SMTP, Google OAuth…): copiar-lo a mà del VPS.
4. Tests: `cd fp-cercador/backend && python3 -m pytest tests -q --deselect tests/test_pipeline.py::test_ce_acces_falla_conserva_fitxer_anterior`
   (785 verds el 2026-11-15 amb `--ignore=tests/test_pipeline.py`, que fa peticions de xarxa i es penja
   sense connexió).
5. Local: `python3 app.py` (port 5001) i `python3 -m http.server 8765` dins `frontend/`.

## Deploy (sempre amb l'aprovació explícita del propietari)

`git push cercador-grausfp master`, i després
`ssh contabo 'cd /home/masellas-grausfp/htdocs/grausfp.masellas.info && git pull --ff-only'`.
- Si toca el backend: `systemctl restart fp-cercador`. **Mai diumenge 11:10–11:45**, que és quan corre el
  refresc setmanal.
- Si es canvien textos o `auth.js`/`alertes.js`: apujar la versió `?v=` a totes les pàgines i a
  `I18N_VERSION` de `backend/grau_page.py` (ara `20261115e`; `site.css?v=6`, `footer.js?v=3`, `feedback.js?v=5`).
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

### Correspondència certificats ↔ cicles i error a `bc_loe.json` (plans 090–094, escrits el 2026-11-17)
- Origen: dos correus d'un usuari (docent d'FPO) que demanava enllaçar els MF dels certificats amb els
  mòduls dels cicles i poder-ho baixar en Excel. En contrastar dades amb els annexos oficials va sortir
  un error nostre.
- **Pla 090: fet i desplegat el 2026-11-17** (prod `1482d6c`). `bc_loe.json` regenerat en local: 140 certificats perden
  399 UC que eren d'un altre annex, 6 en guanyen 15 (EOCH0108, MAPU0112 i QUIB0108, escanejats, i QUIE0108,
  TMVI0112, FMEM0311) i 4 claus de certificats que ja no són al catàleg desapareixen. Font: annex en 516,
  llista del SEPE en 59, cap en 5 (els de sufix `_N`, sense annex). Informe: `plans/outputs/audit_bc_loe.md`.
  - Desplegat sense reiniciar (l'aplicació rellegeix `bc_loe.json` quan en canvia la data). Còpia de
    l'anterior al VPS: `/root/bc_loe.json.bak-20261117-pre090`; en local, `backend/data/bc_loe.json.bak-pre090`.
    Verificat a producció: ELEM0311 → MF1978_2 i MF1979_2; MF1975_2 → només ELEM0411; MAPU0112 → 3 mòduls.
  - No dispara correus de seguiment de centres: a producció hi ha 4 seguiments actius (comprovat el
    2026-11-17, només lectura) i cap és d'un mòdul B o A LOE.
  - Decisions preses en executar (revisables): els codis surten de les capçaleres `Código: MF####_N` i no de
    les d'UC (falten en uns 80 annexos i en d'altres porten errades); la llista del SEPE té un topall de 8
    codis per certificat i amb 8 es tracta com a possiblement tallada; `--dry-run` ja no escriu el fitxer.
  - Per al 091: en uns 19 certificats el número del MF i el de la UC de l'annex no coincideixen (ADGN0110:
    MF2180_2 amb UC1445_2). `bc_loe.json` desa el número del MF.
- **Pla 091: fet i desplegat el 2026-11-17** (prod `bafeff2`). `backend/data/d_uc_corr.json` (no viatja amb el git) porta
  la correspondència oficial UC ↔ mòdul de 185 dels 195 cicles D, per `ref`: 34 de 34 bàsics, 65 de 67
  mitjans i 86 de 94 superiors. Es genera amb `python3 scripts/build_d_uc_corr.py [--cache DIR]` (manual,
  fora del refresc setmanal; ~10 min sense memòria cau). Informe: `plans/outputs/audit_d_uc_corr.md`.
  - API: `GET /api/correspondencia?cicle=<ref>` i `GET /api/correspondencia?cp=<codi>` (certificat LOE).
    Regla a `backend/uc_corr.py`: una fila només convalida quan el certificat en té totes les UC.
  - 92 cicles tenen la taula vigent en un decret posterior al seu: RD 498/2024 (34 bàsics, apartat «6 bis»),
    499/2024 (27), 500/2024 (27) i els d'«actualización» del 2023 (290, 401, 403 i 404/2023; 6 cicles), que
    el pla no preveia.
  - **Decisió presa en executar (revisable):** els decrets del 2024 canvien els codis d'UC (ELEE0109 porta
    UC0820_2…UC0825_2 i la taula vigent del cicle d'Instal·lacions Elèctriques parla d'UC2340_2…UC2345_2).
    L'índex desa també la taula original a `convalida_anterior` (57 cicles) i l'API hi recorre només quan cap
    UC del certificat surt a la vigent, marcant-ho amb `derogada: true` i `substituida_per`. Afecta 12
    certificats. Decisió del propietari (2026-11-17): la web les ha de mostrar, però deixant molt evident
    que estan derogades; recollit al pla 092. L'equivalència entre UC antigues i noves no és a
    les taules (és als decrets de les qualificacions) i no s'ha tocat.
  - 10 cicles sense taula, i no en poden tenir: 5 anteriors al sistema d'UC i 5 d'aeronàutica sense UC al
    decret. Els 3 del 2007 amb l'annex com a imatge a l'XML (Mecanizado, Panadería, Educación Infantil) es
    llegeixen del PDF del BOE amb pdfplumber (només el generador; el servidor no el necessita).
  - Els números de mòdul no s'han escrit a `d_modulos.json`: l'API els omple en llegir (1.210 mòduls casen
    pel nom). Fer-ho servir a la resta de l'aplicació és una decisió a part.
  - Certificats on el número del MF i el de la UC de l'annex no coincideixen: revisats els 16 pel nom de la
    UC. En 13 és una errada de l'annex i `bc_loe.json` ja és correcte; en 3 (MAPN0310, QUIE0108, TMVI0112)
    la UC real és una altra i es corregeix a `backend/uc_corr_overrides.json`, que només fa servir
    `/api/correspondencia` (no toca `bc_loe.json` ni l'itinerari).
  - Cap fila il·legible: un codi d'UC imprès sense nivell es completa des de la resta del mateix decret.
  - Graus E fora de l'índex per decisió del pla (19 dels 38 tenen taula al decret propi).
  - Desplegat (dues passades el mateix dia) amb `git pull`, `d_uc_corr.json` copiat al VPS (cal tornar-lo a copiar si es regenera) i
    reinici del servei. Verificat a producció: `?cp=ELEE0109` → 0232, 0238, 0240, 0235, 0236 (taula
    substituïda); `?cicle=sanidad~audiologia-protesica` → taula del RD 500/2024.
- **Pla 092: fet i desplegat el 2026-11-17** (prod `56f54ed`). La correspondència del 091 surt a tres llocs:
  - **Itinerari d'un certificat del pla antic**: l'enllaç amb cada cicle porta «Convalida N de M mòduls»
    (o «falten UC») i, sota les vistes, un desplegable per cicle amb els mòduls convalidats i per quines
    UC, les files a mitges, la resta de mòduls del cicle i l'enllaç al decret. Els cicles que només venen
    de `ciclos_fp.json` es mantenen com a «sense detall».
  - **Itinerari d'un cicle i pàgina pública `/grau/<ref>`**: taula mòdul → UC que el convaliden →
    certificats del pla antic que les porten totes.
  - **«Què em falta?»**: secció nova «Convalidacions oficials», a part dels objectius (no se n'ha tocat
    ni l'ordre ni el criteri). Hi aporten UC els certificats LOE i els mòduls B del pla antic.
    «Relacionats» queda per als cicles sense taula.
  - **Taules derogades** (decisió del propietari): es mostren amb l'etiqueta «⚠ Taula derogada», vora
    vermella, avís amb el decret que la substitueix, línia puntejada vermella a l'itinerari, al final de
    la llista i en un grup a part a «Què em falta?». Si algú té UC antigues i noves alhora, surten les
    dues taules del mateix cicle, cadascuna amb la seva etiqueta.
  - Backend: arestes C→D amb `conv`, `mods` i `derogada` a `/api/itinerari/complet`; `certificats` i
    `moduls_restants` a `/api/correspondencia`; `convalidacions` a `/api/que-em-falta`.
  - Verificat al navegador (ca i es, 1280 i 375 px, teclat). Textos: `i18n.js?v=20261117a`.
  - Desplegat amb `git pull` i reinici. Verificat a producció: aresta ELEE0109 → Instal·lacions
    Elèctriques amb `conv: 5`, `derogada: true`; `/grau/fabricacion-mecanica~mecanizado` amb la secció de
    convalidació; «Què em falta?» amb ELEE0109 i MF0836_2 torna la taula vigent i la derogada.
- **Pla 093: fet i desplegat el 2026-11-17** (prod `b61daef`; `c_loe_estructura.json` ja és al VPS). `GET /api/export/estructura?refs=` (CSV `;` amb BOM): certificats
  (una fila per UF amb hores i transversal; LOMLOE per A de cada B) o cicles (mòdul, UC que el convaliden,
  certificats LOE). Botons a l'itinerari i al cercador (filtre C o D, ≤50). Dades: `scripts/generate_c_loe_estructura.py`
  (necessita `pdftotext`) → `backend/data/c_loe_estructura.json` (gitignored, copiat al VPS): 564 de 580
  certificats; 62 amb alguna hora absent (queda buida). ELEE0109: 6 MF, 920 h. Pendent: provar-ho amb l'Excel.
- Revisions menors (094), **TODO**.
- Materials de l'anàlisi (scripts de prova, llistes d'errors, instantània del SEPE):
  `plans/outputs/analisi-20261117/`. Cap codi tocat; res desplegat.
- Pendent del propietari: contestar l'usuari.

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

### Pla 086 «Calendari FPO» — fet i desplegat el 2026-11-15
- Agenda: `backend/fpo_agenda.py`, `GET /api/fpo/agenda?dies=` i la vista «Comencen aviat» del mode FPO
  (`index.html?mode=fpo&vista=agenda`), amb filtres de comarca, modalitat, família i tipus.
- Calendari: `frontend/ics.js` (botó «Afegeix al calendari» a l'agenda i al detall d'una especialitat).
  Proves del format: `node --test scripts/test_ics.js` (10).
- Alertes: migració `015_fpo_alerts.sql`, `/api/fpo/alerts` (CRUD i baixa per enllaç),
  `backend/fpo_alerts_service.py`, botó «Avisa'm de cursos nous» a l'agenda i llista a `perfil.html#fpo`.
  749 tests verds.
- Desplegat amb la migració 015 aplicada; còpia de la BD d'abans a
  `/root/fp_cercador.db.bak-20261115-pre086` (al VPS). El primer correu
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

### Pla 088 «Pàgines de família enriquides» — fet i desplegat el 2026-11-15
- `backend/familia_stats.py` (pur), integrat a `_get_seo_data` (`seo['familia_stats']`) i a `familia_publica`;
  `grau_page.render_familia(..., stats=)` i `render_families(..., per_grado=)`. Sense migració ni JavaScript nou.
  770 tests verds.
- `/familia/<prefix>` ara porta, abans de la llista de graus: xifres per lletra, centres i comunitats, botó
  «Buscar en esta familia», novetats, sortides professionals, centres per comunitat i cursos FPO que comencen
  en 60 dies. Cada bloc només surt si té dades. `/families` porta el desglossament «A 12 · B 12 · C 3 · D 13».
- Reconstrucció de `_get_seo_data` amb el catàleg sencer: 0,12 s (les xifres de les 28 famílies, 0,08 s).
- Desplegat amb reinici del servei; no ha calgut tocar nginx.
- Dependències toves resoltes aquí: `index.html` llegeix `?familia=<nom>` (validat contra les famílies del
  catàleg) i `?mode=ocupacio&q=…` (fa la cerca directament). El pla 087 ja no ha d'afegir `?familia=`.
- Decisions preses en executar (revisables):
  - **Novetats:** només compten les altes i baixes que l'entrada de l'historial també llista per nom. L'entrada
    del 2026-06-17 porta metadades de 12.296 graus però cap nom: és la càrrega inicial i no surt. Ara mateix
    només 5 famílies tenen novetats (AGA, IMP, ELE, TMV, ART), les més recents del juliol.
  - **Sortides professionals:** `ocupaciones.json` barreja oficis amb frases de les fitxes («Tu actividad está
    regulada por…») i trossos mal tallats; es descarten els textos de més de 60 caràcters o 8 paraules i els
    que no comencen per lletra. En queden alguns que no són oficis («Almacén de Medicamentos»). Si cap ocupació
    es repeteix, el títol és «Salidas profesionales», no «…más frecuentes».
  - El bloc FPO enllaça a l'agenda sencera (`?mode=fpo&vista=agenda`): l'agenda no té paràmetre de família.
  - Les pàgines de família no tenen JSON-LD `ItemList`: no hi havia res on afegir `numberOfItems`.
- Verificat al navegador: `/familia/SAN`, `/familia/AGA`, `/familia/MSP` (1 grau) i `/families`, a 1280 i
  375 px. **Sense fer:** Lighthouse de SEO. En local Flask no serveix `site.css`; les captures s'han fet
  injectant-lo, de manera que la barra superior i el peu reals només es veuran a producció.

### Pla 087 «Cerca compartible i Volies dir…» — fet i desplegat el 2026-11-15
- Només frontend: `frontend/search-tools.js` (funcions pures), `index.html`, `i18n.js`. Proves:
  `node --test scripts/test_search_tools.js` (15).
- La cerca per nom queda a l'adreça: `q`, `grado`, `familia`, `nivel`, `pla` (`hide`/`only`), `favs=1`,
  `ordre`, `dir=desc`, `p`. S'escriu amb `replaceState` 300 ms després de l'últim canvi (no omple l'historial
  del navegador) i els valors per defecte no s'escriuen. En carregar, els valors invàlids s'ignoren.
- «Volies dir…»: fins a tres cerques semblants quan no hi ha cap resultat, la cerca té 4 lletres o més i no hi
  ha cap altre filtre. El vocabulari (5.211 paraules) es fa el primer cop que cal, en 21 ms; cada suggeriment
  triga 1–2 ms (el llindar del pla era 50 ms).
- Desplegat sense reiniciar (només frontend). El servei encara té `I18N_VERSION` `20261115c` en memòria fins al
  reinici següent; només afecta la clau de memòria cau d'`i18n.js` a les pàgines `/grau` i `/familia`.
- Decisions preses en executar (revisables):
  - Les funcions pures són en un fitxer propi (`search-tools.js`), com `ics.js`, en lloc de dins del
    `<script>` d'`index.html`: així les proves les importen sense extreure codi amb expressions regulars.
  - A la tornada de l'itinerari (`?grado=X&ref=…`) no es llegeix res de l'adreça: `grado` és el del grau que
    s'obre i la llista ve de `sessionStorage`. Un cop restaurada, l'adreça passa a reflectir-la.
  - Amb més d'una paraula mal escrita no es proposa res; un suggeriment només surt si dona resultats.
  - En canviar al mode per nom, es treuen de l'adreça `mode`, `vista` i `esp`.
  - L'enllaç del perfil (`?ref=X`) acaba amb `?ref=X&q=X`, perquè obrir els centres ja posava el codi a la cerca.
- Verificat al navegador, ca i es: adreça amb tres filtres oberta en una finestra nova, ordre i pàgina, valors
  invàlids, `favs=1` sense sessió, enllaç de l'observatori, enllaç del perfil, tornada de l'itinerari, mode FPO;
  `soldadra` → `soldadura`, `infermeria` sense suggeriment, paraula sense res semblant, filtre actiu; 375 px.

### Pla 089 «Reporta un error en aquesta fitxa» — fet i desplegat el 2026-11-15
- Migració `016_feedback_oferta_ref.sql` (`feedback.oferta_ref`); `POST /api/feedback` accepta `ref` (opcional;
  un `ref` invàlid o que no és al catàleg s'ignora, el comentari es desa igualment); l'avís per correu i
  `GET /api/admin/feedback` porten el grau (`oferta: {denominacion, grado, url}`). 785 tests verds.
- `feedback.js` exposa `window.grausfpFeedback.open({kind, ref, label})`: amb `ref` tria «Dades incorrectes» i
  mostra «Sobre: …», que es pot treure amb ✕. La pestanya normal continua igual.
- Enllaç «Hi ha un error en aquesta fitxa?» a la fila desplegada del cercador, a la capçalera de l'itinerari i
  al peu de `/grau/<ref>` (l'afegeix `feedback.js` a partir de `data-report-ref`; sense JavaScript no surt).
  A `admin.html`, el comentari porta l'enllaç al grau.
- Desplegat amb la migració 016 aplicada; còpia de la BD d'abans a
  `/root/fp_cercador.db.bak-20261115-pre089` (al VPS).
- **Atenció:** el refresc setmanal del 2026-11-15 va acabar a les 12:37, no a les 11:45. La franja «mai
  reiniciar diumenge 11:10–11:45» d'aquest document es queda curta; convé mirar l'hora dels fitxers de
  `backend/data/` abans de reiniciar un diumenge al migdia.
- Decisions preses en executar (revisables):
  - El `ref` s'envia com a camp propi del cos; el `context` no canvia (el backend ja el limita a `path`,
    `query` i `lang`).
  - Si el grau d'un comentari ja no és al catàleg, l'admin en veu el `ref` sense enllaç.
  - L'enllaç de la pàgina pública surt en l'idioma del visitant (com el diàleg), encara que la pàgina sigui en
    castellà.
- Verificat al navegador, ca i es, 1280 i 375 px: des de la fila, l'itinerari i la pàgina pública; teclat
  (Enter obre, Esc tanca i el focus torna a l'enllaç); treure «Sobre»; pestanya normal; sense `feedback.js`
  l'enllaç no surt; el comentari arriba a l'admin amb l'enllaç al grau. Cap correu enviat a les proves
  (`FEEDBACK_NOTIFY_EMAIL` buit). En local Flask no serveix `feedback.js`: a la pàgina pública s'ha injectat.

**Els set plans triats el 2026-11-14 (083–089) estan fets.**

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
- Canvi de domini (pla 019): **fet**, per l'opció A (grausfp.es i www.grausfp.es afegits al site existent; el
  directori del VPS conserva el nom `grausfp.masellas.info`). Verificat el 2026-11-15: `/health`,
  `/api/next-refresh` i `/api/ofertes` responen a grausfp.es; `grausfp.masellas.info` i `www.grausfp.es` fan
  301 cap a `https://grausfp.es` conservant el camí; el certificat cobreix els tres noms (caduca el
  2027-01-26); `robots.txt`, `sitemap.xml`, `canonical` i `og:url` ja diuen grausfp.es (`SITE_URL` aplicat); el
  `redirect_uri` de Google és `https://grausfp.es/api/auth/google/callback`. Sense poder comprovar des d'aquí:
  Search Console i que Google Cloud tingui aquest `redirect_uri` autoritzat. `deploy/` fa servir `DOMINI_AQUI`
  i les rutes de disc de sempre, que continuen sent vàlides.
- Pla 053: preferències d'email (TODO).
- Pla 064: UI de l'FPO extern (PIMEC/Foment). El 063 (backend) és fet.
- Política de privacitat "provisional", lligada al registre GDPR.
