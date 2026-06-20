# Com executar aquests plans — guia per a l'operador

Aquesta guia és per a tu (en Roger), no per als models executors. Explica
com llançar cada pla, en quin ordre, què verificar i quins passos manuals
calen al servidor. Els plans en si (`001-*.md` … `014-*.md`) són
autocontinguts: estan escrits perquè un model SENSE CAP context d'aquesta
sessió els pugui executar només llegint el fitxer.

---

## 1. La idea general

- **Cada pla = una sessió nova i neta** d'un agent (Claude Code o similar).
  No executis dos plans a la mateixa conversa: el context d'un pla
  contamina el següent i el model comença a "recordar" coses en lloc de
  llegir el pla.
- **Un pla, un objectiu, commits atòmics.** Cada pla diu exactament quins
  fitxers pot tocar i com verificar cada pas. Si l'executor surt d'aquest
  perímetre, atura'l.
- **Models barats serveixen.** Els plans estan escrits per a "l'executor
  plausible més fluix": Sonnet o Haiku són suficients per a la majoria.
  Excepcions recomanades: plans **002** i **006** (reescriptura de tests i
  canvi de format de dades) — fes-los amb un model potent o revisa'ls amb
  més atenció.
- **Tu ets el revisor.** Després de cada pla: llegeix el diff
  (`git diff HEAD~1`), comprova els "Done criteria" del pla tu mateix
  (són comandes copiables) i només llavors passa al següent.

## 2. Prompt per llançar un pla

Obre una sessió nova de Claude Code a `fp-cercador/` i enganxa:

```
/improve execute el pla plans/010-treure-artefactes-de-dades-del-git.md al peu de la lletra.
Llegeix-lo sencer abans de tocar res. Executa el "Drift check" del principi.
Respecta les seccions Scope (no toquis res fora d'In scope) i STOP conditions
(si se'n dona una, atura't i informa'm en lloc d'improvisar). Verifica cada
step amb la seva comanda abans de passar al següent. En acabar, marca el pla
com a DONE a plans/README.md i ensenya'm el resum de canvis.
```

(Canvia el nom del fitxer per a cada pla.)

Alternatives equivalents:

- **`/gsd-quick`**: si vols mantenir el flux GSD del projecte, pots fer
  `/gsd-quick executa el pla plans/00X-....md tal com està escrit` — els
  plans encaixen bé com a "quick tasks" perquè ja porten la verificació
  incorporada.
- **`/improve execute plans/00X-....md`**: l'skill improve pot despatxar un
  executor en un worktree aïllat i revisar-ne el diff abans d'integrar-lo.
  És l'opció més segura per als plans 002 i 006.

## 3. Ordre d'execució recomanat

```
FASE A — Fonaments (seqüencial, en aquest ordre exacte):
  001 → 002 → 003

FASE B — Bugs de producció (després de 001; 004 pot anar en paral·lel amb la fase A):
  004, 005 → 006

FASE C — Neteja i seguretat (independents, qualsevol ordre):
  007, 008, 009, 010, 012

FASE D — Documentació (l'últim, perquè documenta l'estat final):
  011

OPCIONALS (quan vulguis, són investigació sense codi):
  013 (quan vulguis)
  014 (després de 005 i 006)
```

Regles d'or:

- **No comencis res abans del 001.** Mentre el 001 no estigui fet, CADA
  execució de `pytest` torna a escriure brossa a l'historial públic. Això
  inclou els pytest que llançaran els executors dels altres plans.
- **No executis plans en paral·lel si comparteixen fitxers.** Conflictes
  coneguts: 010 i 011 toquen tots dos `deploy/DEPLOY.md`; 007 i 011 toquen
  `README.md`. La resta de la fase C és segura en paral·lel.
- Després de **cada** pla de backend (001–007), executa tu mateix:
  `cd backend && python -m pytest tests/ -q` i comprova que
  `git status` només mostra el que el pla declarava.

## 4. Estat actual que has de conèixer abans de començar

- **L'historial està contaminat ARA MATEIX.** Durant l'auditoria s'han
  executat tests (2 vegades), i cada execució ha afegit una entrada falsa
  amb `total=100` a `backend/data/refresh_history.json`, cadascuna amb un
  diff espuri d'~1,6 MB. L'script del Step 3 del pla 001 ho neteja totes
  de cop (filtra per la signatura del mock, no per data).
- **La suite de tests està vermella** (10 failed / 59 passed) fins que es
  faci el pla 002. És l'estat esperat; no deixis que un executor "arregli"
  tests fora del seu pla.
- **El repo git té l'arrel al directori PARE** (`Cercador Graus/`), no a
  `fp-cercador/`. Els fitxers de `deploy/` i el `CLAUDE.md` del projecte
  són a l'arrel. Els plans que els toquen (004, 006, 010, 011, 012) ho
  indiquen explícitament — si un executor diu que "no troba deploy/",
  recorda-li que és a `../deploy/` des de `fp-cercador/`.
- **Tot es commiteja directament a `master`** (és la convenció actual del
  repo). Si prefereixes una branca per pla, digues-ho a l'executor al
  prompt ("crea la branca advisor/00X-nom abans de començar") — els plans
  no ho imposen.
- Cap pla fa `git push`. Els push, els fas tu quan estiguis conforme.

## 5. Passos manuals al servidor (VPS)

Els plans deixen el repo llest, però alguns canvis demanen acció al VPS
(Contabo, CloudPanel). Després de fer `git pull` al servidor:

### Després del pla 001

Si mai s'han executat tests al VPS, el seu `refresh_history.json` també pot
estar contaminat. Comprova-ho i neteja amb el mateix script del Step 3 del
pla 001 (còpia'l al servidor o executa'l per ssh):

```bash
python3 -c "import json; h=json.load(open('backend/data/refresh_history.json')); print([e['ts'] for e in h if e.get('total')==100])"
```

Si imprimeix dates, executa l'script de neteja allà.

### Després del pla 004

```bash
cp deploy/fp-cercador.service /etc/systemd/system/fp-cercador.service
systemctl daemon-reload
systemctl restart fp-cercador
ps aux | grep gunicorn   # esperat: 2 processos (1 master + 1 worker), no 3
```

### Després del pla 006

1. Executa la migració d'historial del Step 2 del pla 006 AL SERVIDOR
   (sobre el `refresh_history.json` del VPS, que és diferent del local).
   Fes còpia abans: `cp backend/data/refresh_history.json backend/data/refresh_history.json.bak`
2. Aplica el conf de nginx i recarrega:
    ```bash
    # còpia el conf al lloc on CloudPanel gestiona el vhost, després:
    nginx -t && systemctl reload nginx
    ```
3. Verifica la compressió i la mida:
    ```bash
    curl -s -H "Accept-Encoding: gzip" -o /dev/null -w "%{size_download} bytes\n" https://EL_TEU_DOMINI/api/refresh-history
    ```
    Esperat: pocs KB (abans: ~11,5 MB).
4. Reinicia el servei Flask (`systemctl restart fp-cercador`) perquè
   carregui el nou `history.py`.

### Diagnòstic del refresh automàtic que "no funciona" (abans i després dels plans 004/005)

El símptoma reportat ("el refresh programat no s'executa sol") té dues causes
conegudes que els plans arreglen: el refresh programat **no escriu mai a
l'historial** (pla 005), així que encara que funcioni no es veu enlloc; i amb
`--workers 2` el `POST /api/admin/scheduler` només programa el job **al worker
que atén la petició** — l'altre no se n'assabenta fins al restart, i
`/api/next-refresh` respon des d'un worker a l'atzar (pla 004).

Per confirmar l'estat real al VPS abans de tocar res:

```bash
# 1. La config persistida està activada?
cat backend/data/scheduler.json
# esperat: {"enabled": true, "day_of_week": "...", "hour": ..., "minute": ...}
# si no existeix o enabled=false → la feature mai ha quedat activada: activa-la
# des del panell admin i REINICIA el servei (així la llegeixen tots els workers)

# 2. Hi ha job programat? (demana-ho 6 vegades: amb 2 workers pot alternar
#    entre una data i null — això ÉS el bug del pla 004)
for i in 1 2 3 4 5 6; do curl -s http://127.0.0.1:8033/api/next-refresh; echo; done

# 3. El darrer intent va fallar? (l'estat d'error del scheduler només es veu aquí)
curl -s http://127.0.0.1:8033/api/refresh-status

# 4. Evidència física: ofertes.json s'ha regenerat a l'hora programada?
ls -la backend/data/ofertes.json

# 5. Logs del servei a l'hora programada
journalctl -u fp-cercador --since "-8 days" | grep -i "refresh\|scheduler\|error" | tail -30
```

Interpretació ràpida: si (1) és `enabled:false` o no existeix → problema de
configuració, no de codi. Si (2) alterna data/null → bug del pla 004. Si (4)
té mtime de l'hora programada però l'historial no mostra res → bug del pla
005 (funcionava però era invisible). Si (3) mostra `status: error` → mira els
`errors` del JSON i els logs de (5).

**Després d'aplicar els plans 004 i 005 + restart**: activa l'scheduler des
del panell admin, comprova que `/api/next-refresh` retorna SEMPRE la mateixa
data (ja només hi ha un worker), i després de la primera execució programada
verifica que apareix una entrada nova a `historial.html`.

### Després dels plans 005, 007, 009, 012 (canvis de codi/frontend)

Només cal `git pull` + `systemctl restart fp-cercador` (el frontend és
estàtic, nginx el serveix directament del checkout).

### Després del pla 010

Cap acció: `git pull` deixarà els fitxers de dades del servidor com a
untracked i deixaran de donar conflictes. Verifica que
`backend/data/ofertes.json` segueix existint al servidor després del pull.

### Migració futura a domini propi

Quan vulguis moure l'app de `grausfp.masellas.info` a un domini propi, NO és
complicat (el frontend usa rutes relatives i el backend no coneix el domini):
segueix el **pla 019** (`plans/019-migracio-domini.md`) — és una checklist
manual de VPS amb les comandes exactes, l'avís del pas delicat (copiar
`.env` i `backend/data/`, que no són al git) i la redirecció 301 per no
trencar enllaços ni SEO.

## 6. Ruta ràpida: arreglar el refresh automàtic (símptoma prioritari)

El refresh programat "que no funciona sol" es resol amb els plans **004 i
005** (el 005 necessita el 001 abans). Ordre mínim per a aquest símptoma:

```
001 (aïllar tests — prerequisit del 005)
  → 005 (el refresh programat escriu historial)
004 (gunicorn 1 worker — es pot fer en paral·lel amb els altres dos)
```

Després: desplegar al VPS (secció 5), reiniciar el servei, reactivar
l'scheduler des del panell admin i fer la verificació final del diagnòstic.

### Prompts llestos per copiar (una sessió nova de Claude Code per a cadascun)

**Pas 1 — pla 001:**

```
Executa el pla plans/001-aillar-tests-de-dades-reals.md al peu de la lletra.
Llegeix-lo sencer abans de tocar res. Executa el "Drift check" del principi.
Respecta les seccions Scope (no toquis res fora d'In scope) i STOP conditions
(si se'n dona una, atura't i informa'm en lloc d'improvisar). Verifica cada
step amb la seva comanda abans de passar al següent. En acabar, marca el pla
com a DONE a plans/README.md i ensenya'm el resum de canvis.
```

**Pas 2 — pla 005 (només quan el 001 estigui DONE):**

```
Executa el pla plans/005-historial-del-refresh-programat.md al peu de la
lletra. Llegeix-lo sencer abans de tocar res. Executa el "Drift check" del
principi. Comprova a plans/README.md que el pla 001 està DONE (és una
dependència; si no ho està, atura't). Respecta Scope i STOP conditions.
Verifica cada step amb la seva comanda. En acabar, marca el pla com a DONE a
plans/README.md i ensenya'm el resum de canvis.
```

**Pas 3 — pla 004 (en qualsevol moment, sessió a part):**

```
Executa el pla plans/004-gunicorn-un-sol-worker.md al peu de la lletra.
Atenció: els fitxers que toca són a l'arrel del repo git (directori pare de
fp-cercador/): deploy/fp-cercador.service i deploy/DEPLOY.md. Executa el
"Drift check". Respecta Scope i STOP conditions. En acabar, marca el pla com
a DONE a plans/README.md, ensenya'm el resum de canvis i recorda'm els passos
manuals al VPS (daemon-reload + restart).
```

**Pas 4 — verificació al VPS (manual, tu per ssh):** executa el diagnòstic de
la secció 5 ("Diagnòstic del refresh automàtic"). Esperat després dels plans:
`/api/next-refresh` retorna sempre la mateixa data, i la primera execució
programada apareix a `historial.html`.

**Pas 5 — només si DESPRÉS de tot això encara falla** (sessió nova, enganxa-hi
la sortida del diagnòstic):

```
El refresh automàtic del Cercador FP segueix sense funcionar després d'aplicar
els plans 004 i 005 de plans/ (gunicorn a 1 worker; history.py compartit entre
refresh manual i programat). Llegeix plans/instructions.md secció "Diagnòstic
del refresh automàtic" per al context complet del símptoma i les causes ja
descartades. Aquí tens la sortida del diagnòstic executat al VPS:

[ENGANXA AQUÍ: contingut de scheduler.json, les 6 respostes de
/api/next-refresh, la resposta de /api/refresh-status, ls -la de
backend/data/ofertes.json, i les línies rellevants de journalctl]

Investiga la causa arrel de manera sistemàtica abans de proposar cap fix:
formula hipòtesis, descarta-les amb l'evidència, i si et cal més informació
del servidor demana-me-la (no tens accés ssh directe). No modifiquis codi
fins que tinguem la causa confirmada.
```

## 7. Què fer quan un executor s'encalla

- **Reporta una STOP condition**: és el comportament correcte, no un error.
  Llegeix què ha trobat. El cas més probable és drift (el codi ha canviat
  respecte als extractes del pla, per exemple perquè un altre pla l'ha
  tocat). Si el canvi és el que esperaves d'un pla anterior, digues-li que
  continuï adaptant els números de línia; si és inesperat, mira-ho tu.
- **Vol tocar fitxers fora de l'Scope**: nega-ho i demana-li que expliqui
  per què creu que cal. Gairebé sempre és símptoma que està improvisant.
- **Un test no passa després de 2 intents**: atura la sessió, mira el
  failure tu mateix o passa el pla a un model més potent. No el deixis
  iterar a cegues — els plans estan pensats perquè això no calgui.
- **Marca BLOCKED al README**: deixa-ho escrit amb el motiu; el proper
  executor (o jo, en una futura sessió amb `/improve reconcile`) ho
  reprendrà.

## 8. Després de cada pla — checklist de revisió (30 segons)

1. `git log --oneline -3` — el(s) commit(s) tenen el missatge previst?
2. `git diff HEAD~1 --stat` — només fitxers de l'In scope?
3. Executa els "Done criteria" del pla (són comandes copiables).
4. `cd backend && python -m pytest tests/ -q` — verd (a partir del pla 002)?
5. Actualitzada la fila a `plans/README.md`?

## 9. Feature futura: centres per grau (pla 015)

El pla **015** és l'spike per a la feature "a quins centres s'imparteix cada
grau" (tot l'Estat, amb contacte i estat: passat / inscripció oberta /
anunciat). El pla ja porta incorporat el **mapa de fonts investigat**
(2026-06-10): la candidata primària és el Registre Estatal d'Entitats de
Formació FP (`registrosfp.educacion.gob.es`, cercable per codi d'oferta i amb
exportació), el RCD (`educacion.gob.es/centros`) per al contacte, el SEPE per
al vessant laboral, i l'estratègia de snapshots propis (la mateixa maquinària
de `compute_changes` dels plans 005/006) per derivar els estats. El que NO
dona cap font estatal és "inscripció oberta" — el pla proposa enllaços
profunds als 17 portals d'admissió autonòmics com a primera versió.

Quan executar-lo: idealment amb 005 i 006 ja DONE, i coordinat amb el 013 si
també el fas (tots dos toquen centres del Grado C). El resultat NO és codi:
és `plans/outputs/spike-centres-per-grau.md` amb el disseny i el pressupost
de les fases de construcció (016–018), que aprovaràs tu abans de construir res.

**Prompt per llançar-lo** (sessió nova; millor amb un model potent — és
investigació amb judici, no execució mecànica):

```
Executa el pla plans/015-spike-centres-per-grau.md. És un spike d'investigació
i disseny: el lliurable és plans/outputs/spike-centres-per-grau.md, NO codi —
no modifiquis res fora de plans/outputs/. Llegeix el pla sencer: porta un mapa
de fonts ja investigat que has de VALIDAR (no redescobrir), amb les preguntes
concretes de cada step. Limita les proves contra les fonts del ministeri a
peticions de mostra (<20 per font) amb els headers del projecte, i atura't
immediatament davant de 403/429 o captcha (STOP conditions del pla). En
acabar, marca el pla com a DONE a plans/README.md i fes-me un resum de la
recomanació i les decisions que em queden a mi.
```

## 10. Roadmap de funcionalitats futures (F1–F10)

Les 10 funcionalitats aprovades (login, favorits, alertes, seguiment de
centres, itineraris, cerca per ocupació, observatori, exportació per a
orientadors, multiidioma i API pública) estan descrites — amb la taula de
referència, les dependències i **el consell de palanca (F1 → F3 → F4, amb
F7 en paral·lel)** — a `plans/futures/ROADMAP-FEATURES.md`. Aquell document
és la font de veritat de la visió; consulta-l'hi abans de prioritzar res.

Spikes ja generats per a la primera tongada (mateix patró que el 015 —
sessió nova, model potent, lliurable a `plans/outputs/`, zero codi):

**Spike 018 — Observatori (F7, onada 1, no necessita login):**

```
Executa el pla plans/018-spike-observatori-oferta.md. És un spike de disseny:
el lliurable és plans/outputs/spike-observatori.md, NO codi — no modifiquis
res fora de plans/outputs/. Llegeix abans plans/futures/ROADMAP-FEATURES.md
(F7). Comprova que els plans 005 i 006 estan DONE a plans/README.md (són
dependències). En acabar, marca el pla DONE i resumeix-me la recomanació.
```

**Spike 016 — Login (F1, onada 2, el fonament):**

```
Executa el pla plans/016-spike-login-fonament.md. És un spike de disseny: el
lliurable és plans/outputs/spike-login.md, NO codi — no modifiquis res fora
de plans/outputs/. Llegeix abans plans/futures/ROADMAP-FEATURES.md (F1 i les
features que en depenen: F2, F3, F4, F8, F10) — el disseny ha de servir-les
totes. Respecta la constraint de dependències (stdlib: sqlite3, smtplib,
werkzeug.security). En acabar, marca el pla DONE i llista'm les decisions
que em demana (SMTP, GDPR, model d'auth recomanat).
```

**Spike 017 — Alertes (F3, onada 3, NOMÉS quan el 016 estigui DONE):**

```
Executa el pla plans/017-spike-alertes-novetats.md. És un spike de disseny:
el lliurable és plans/outputs/spike-alertes.md, NO codi. Llegeix abans
plans/futures/ROADMAP-FEATURES.md (F3) i plans/outputs/spike-login.md (no
re-obris les decisions d'email/BD que aquell ja fixa; si no existeix,
atura't — cal fer primer el pla 016). Comprova que 005 i 006 estan DONE.
En acabar, marca el pla DONE i resumeix-me la recomanació i les preguntes
obertes.
```

Per a la resta de features (F2, F4, F5, F6, F8, F9, F10): quan la seva onada
s'acosti, demana a una sessió de `/improve` que generi el spike corresponent
("genera el pla de spike per a la feature FX del roadmap
plans/futures/ROADMAP-FEATURES.md, seguint el patró dels plans 016-018") —
mantindrà la numeració i actualitzarà l'índex.

## 11. Notes finals

- Els plans **013 i 014 són spikes opcionals**: produeixen un document de
  disseny a `plans/outputs/`, zero codi. Llança'ls quan tinguis ganes de
  decidir sobre aquestes funcionalitats, no abans. El 013 fa unes poques
  peticions reals a webs del ministeri — res d'agressiu, però millor no
  executar-lo en bucle.
- Quan tots els plans P1–P2 estiguin DONE, el canvi visible serà:
  historial públic correcte i lleuger (KB en lloc d'11,5 MB), refreshos
  programats visibles a l'historial, panell admin amb estat consistent,
  suite de tests fiable com a xarxa de seguretat, i ~4.000 línies de codi
  mort fora del repo.
- Si en el futur vols re-auditar, executa `/improve` de nou: llegirà aquest
  `plans/README.md`, no duplicarà troballes i mantindrà la numeració.

---

## Passos manuals post-desplegament

### bc_loe.json (Pla 045)

Després del primer desplegament del pla 045, executa al VPS:

```bash
cd /ruta/al/repo
pip install pdfplumber
python3 scripts/generate_bc_loe.py
```

Triga ~6 min. `bc_loe.json` es genera a `backend/data/bc_loe.json`.
No cal rellançar el servei: Flask llegeix el fitxer a cada petició.

Re-executa el script si s'afegeixen nous certificats C LOE (rarament).

### ocupaciones.json (Pla 047)

Després del primer desplegament del pla 047, executa al VPS:

```bash
cd /ruta/al/repo
python3 scripts/generate_ocupaciones.py
```

Triga ~2-3 min. Genera `backend/data/ocupaciones.json`. No cal rellançar el
servei (Flask llegeix el fitxer amb cache per mtime). Re-executa el script si
s'actualitza el catàleg de certificats o cicles.
