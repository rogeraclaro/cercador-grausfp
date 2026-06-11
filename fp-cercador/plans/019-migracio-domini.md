# Plan 019: Migració a domini propi (checklist operativa)

> **Naturalesa d'aquest pla**: a diferència dels plans 001–012, això és
> majoritàriament feina MANUAL de l'operador al VPS (CloudPanel + ssh), no
> d'un agent executor. L'única part delegable a un agent són els Steps 6–7
> (actualitzar els fitxers de `deploy/` al repo). Executa'l quan tinguis el
> domini nou decidit i registrat.
>
> **Validesa**: escrit el 2026-06-10 contra el commit `5dc92a1`. Si els plans
> 004/006/010/011 ja s'han aplicat, els fitxers de `deploy/` hauran canviat
> una mica — les rutes i el patró són els mateixos.

## Status

- **Priority**: P3 (quan es decideixi el domini)
- **Effort**: S (~30–60 min de feina de servidor; zero codi)
- **Risk**: LOW si se segueix l'ordre (el pas delicat és el Step 4: copiar `.env` i `backend/data/`)
- **Depends on**: cap (compatible abans o després de qualsevol altre pla)
- **Category**: deploy
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Per què és senzill (fets verificats al codi)

- El frontend NO té el domini hardcoded: les 3 pàgines fan
  `API_BASE = hostname === 'localhost' ? 'http://localhost:5001' : ''`
  (p. ex. `frontend/index.html:565-567`) — en producció criden `/api/...`
  en relatiu, mateix origen. Funciona idèntic sota qualsevol domini.
- El backend no referencia cap domini propi (només todofp.es per scraping).
- L'únic acoblament és infraestructura del VPS: el vhost nginx
  (`server_name` + certificat) i les **rutes de disc amb el nom del domini**
  que CloudPanel crea (`/home/masellas-grausfp/htdocs/grausfp.masellas.info/...`),
  clavades a `deploy/fp-cercador.service` (`WorkingDirectory`,
  `EnvironmentFile`, `ExecStart`).

## Decisió prèvia: opció ràpida o neta

- **Opció A (ràpida)**: afegir el domini nou com a domini addicional del
  site existent a CloudPanel. Tot queda on és; el directori conserva el nom
  vell (cosmètic). Steps: 1, 2-A, 5, 7, 8.
- **Opció B (neta)**: site nou de CloudPanel amb el nom del domini nou.
  Steps: tots. És la recomanada si el canvi de domini és definitiu.

## Steps

### Step 1: DNS

Al registrador del domini nou: registre `A` (i `AAAA` si el VPS té IPv6)
apuntant a la IP del VPS de Contabo. Verifica propagació:
`dig +short DOMINI_NOU` → la IP del VPS.

### Step 2-A (opció ràpida): domini addicional al site existent

A CloudPanel: Site → Domains → afegir `DOMINI_NOU` → emetre certificat
Let's Encrypt per al domini nou. Salta al Step 5.

### Step 2-B (opció neta): site nou a CloudPanel

Crea el site per a `DOMINI_NOU` (tipus estàtic/reverse-proxy segons el patró
actual) i emet el certificat. CloudPanel crearà
`/home/<usuari-nou>/htdocs/DOMINI_NOU/`.

### Step 3 (només B): clonar el repo al directori nou

```bash
cd /home/<usuari-nou>/htdocs/DOMINI_NOU
git clone <URL_REPO> .
python3 -m venv venv && venv/bin/pip install -r fp-cercador/backend/requirements.txt
```

### Step 4 (només B) — ⚠️ EL PAS QUE POT TRENCAR COSES: copiar el que NO és al git

`backend/.env` i `backend/data/` (ofertes.json, refresh_history.json,
scheduler.json, last_snapshot.json) **no estan versionats**. Sense copiar-los,
el servei no arrenca (falta ADMIN_TOKEN) i el cercador queda buit fins al
primer refresh.

```bash
cp /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/.env \
   /home/<usuari-nou>/htdocs/DOMINI_NOU/fp-cercador/backend/.env
cp -a /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data \
   /home/<usuari-nou>/htdocs/DOMINI_NOU/fp-cercador/backend/
```

### Step 5: vhost nginx

Aplica el patró de `deploy/nginx-cloudpanel.conf` al vhost del domini nou:
`server_name DOMINI_NOU`, certificats del domini nou, `root` apuntant al
`frontend/` (del directori nou si opció B), bloc `location /api/` cap a
`127.0.0.1:8033`, i el bloc `/health`. Conserva les directives gzip si el
pla 006 ja s'ha aplicat. Verifica: `nginx -t && systemctl reload nginx`.

### Step 6 (només B): systemd

Actualitza `deploy/fp-cercador.service` (al repo) amb les rutes noves
(`WorkingDirectory`, `EnvironmentFile`, els paths de l'`ExecStart`) i
desplega'l:

```bash
cp deploy/fp-cercador.service /etc/systemd/system/fp-cercador.service
systemctl daemon-reload && systemctl restart fp-cercador
systemctl status fp-cercador
```

(Atenció: el port 8033 és el mateix — si durant la transició conviuen els
dos sites, NOMÉS un servei pot escoltar-hi; atura el vell abans d'arrencar
el nou.)

### Step 7: redirecció 301 del domini vell

Deixa el vhost de `grausfp.masellas.info` només amb:

```nginx
server {
    listen 443 ssl http2;
    server_name grausfp.masellas.info;
    ssl_certificate     /etc/letsencrypt/live/grausfp.masellas.info/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/grausfp.masellas.info/privkey.pem;
    return 301 https://DOMINI_NOU$request_uri;
}
```

(I l'equivalent al bloc :80.) Així cap enllaç existent es trenca i el SEO
es traspassa. Mantén-lo mesos, no dies.

### Step 8: actualitzar el repo i verificar

1. Al repo: actualitza `deploy/DEPLOY.md` i `deploy/nginx-cloudpanel.conf`
   amb el domini/rutes nous (delegable a un agent). Commit:
   `chore(deploy): migració a DOMINI_NOU`.
2. Verificació funcional final:

```bash
curl -s https://DOMINI_NOU/health                       # {"status":"ok"}
curl -s https://DOMINI_NOU/api/next-refresh             # JSON (confirma .env i scheduler OK)
curl -s -o /dev/null -w "%{http_code}\n" https://DOMINI_NOU/api/ofertes   # 200
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" https://grausfp.masellas.info/  # 301 → domini nou
```

3. Al navegador: cercador, historial i panell admin (amb el token) sota el
   domini nou.

## Done criteria

- [ ] Les 4 comandes curl del Step 8 donen el resultat esperat
- [ ] Panell admin funcional al domini nou (refresh manual de prova OK)
- [ ] El domini vell fa 301 cap al nou
- [ ] `deploy/DEPLOY.md` i el `.service` del repo reflecteixen les rutes noves
- [ ] (Opció B) el servei vell aturat i deshabilitat (`systemctl disable`)

## STOP conditions / reculada

- Si el servei nou no arrenca: gairebé sempre és el Step 4 (`.env` no
  copiat) — `journalctl -u fp-cercador -n 20` ho dirà ("ADMIN_TOKEN not set").
- Reculada neta en qualsevol moment: el site vell queda intacte fins al
  Step 7; n'hi ha prou de reactivar el servei vell i revertir el vhost.

## Maintenance notes

- Quan caduquin, esborrar el site vell de CloudPanel (després de mesos de
  301) i el certificat orfe.
- Si el pla 010 encara no s'havia aplicat en migrar, el `git clone` nou SÍ
  portarà ofertes.json/refresh_history.json (versions del repo, potencialment
  velles) — el Step 4 els ha de sobreescriure igualment amb els del servidor.
