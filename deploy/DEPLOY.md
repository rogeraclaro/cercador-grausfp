# Desplegament — Cercador FP España

VPS: Contabo | OS: Ubuntu 24.04 | Panel: CloudPanel

## Prerequisits

- Domini configurat apuntant a la IP del VPS (A record)
- CloudPanel instal·lat i accessible
- Accés SSH com a root (o usuari amb sudo)

## 1. Clonar el repositori

```bash
cd /var/www
git clone <URL_REPO> fp-cercador
cd fp-cercador
```

## 2. Crear i activar virtualenv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r fp-cercador/backend/requirements.txt
deactivate
```

## 3. Configurar variables d'entorn

```bash
cp fp-cercador/backend/.env.example fp-cercador/backend/.env
nano fp-cercador/backend/.env
```

El `.env` ha de contenir:

```
ADMIN_TOKEN=<token-segur-aleatori>
BUSCADOR_COOKIES=JSESSIONID=<valor>; __Host-todofp.es=<valor>
```

Per obtenir `BUSCADOR_COOKIES` → veure la secció **"Renovar les cookies del buscador"** al final d'aquest document.

## 4. Crear directori de logs

```bash
mkdir -p /var/log/fp-cercador
```

## 5. Instal·lar el servei systemd

```bash
cp deploy/fp-cercador.service /etc/systemd/system/fp-cercador.service
systemctl daemon-reload
systemctl enable fp-cercador
systemctl start fp-cercador
# Verificar:
systemctl status fp-cercador
curl http://127.0.0.1:8033/health
```

## 6. Configurar nginx a CloudPanel

**Opció A (recomanada) — via CloudPanel UI:**
1. CloudPanel > Sites > Add Site > Static Site (o PHP si no hi ha opció estàtica)
2. Document Root: `/home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/frontend`
3. Afegir el block `location /api/` i `location /health` des del fitxer
   `deploy/nginx-cloudpanel.conf` a la config nginx del site.
4. CloudPanel > SSL/TLS > Let's Encrypt (activar HTTPS)

**Opció B — manual:**
```bash
# Substituir DOMINI_AQUI pel domini real a nginx-cloudpanel.conf
sed -i 's/DOMINI_AQUI/fp.example.com/g' deploy/nginx-cloudpanel.conf
cp deploy/nginx-cloudpanel.conf /etc/nginx/sites-available/fp-cercador.conf
ln -s /etc/nginx/sites-available/fp-cercador.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## 7. Verificació final

```bash
# Backend directe
curl http://127.0.0.1:8033/health
# Frontend via nginx
curl https://DOMINI_AQUI/
# API via nginx proxy
curl https://DOMINI_AQUI/api/ofertes | head -c 200
```

## 8. Dades inicials i refresh

`data/ofertes.json` **ja està inclòs al repositori** — després d'un `git pull` el frontend
mostra les dades immediatament sense necessitat de cap refresh.

Per regenerar les dades al VPS (si vols dades més recents o has actualitzat `BUSCADOR_COOKIES`):

```bash
curl -X POST https://DOMINI_AQUI/api/admin/refresh \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
# Monitorar progrés:
curl https://DOMINI_AQUI/api/refresh-status
```

**Nota:** El refresh triga ~4s i requereix `BUSCADOR_COOKIES` vàlides al `.env`.

## Gestió del servei

```bash
systemctl status fp-cercador    # Estat
systemctl restart fp-cercador   # Reiniciar (p.ex. despres d'actualitzar el codi)
journalctl -u fp-cercador -f    # Logs en temps real
tail -f /var/log/fp-cercador/error.log
```

## Actualitzar el codi

```bash
cd /home/masellas-grausfp/htdocs/grausfp.masellas.info
git pull
source venv/bin/activate
pip install -r fp-cercador/backend/requirements.txt
deactivate
systemctl restart fp-cercador
```

---

## Renovar les cookies del buscador (quan caduca la sessió)

L'API del buscador de todofp.es autentica via **cookie de sessió** (`JSESSIONID`).
Quan caduca (el pipeline retorna HTML en lloc de JSON), cal renovar-la:

### Passos per obtenir les cookies noves

1. Obre **https://www.todofp.es/buscadorgradosfp/buscador** al navegador
2. Obre **DevTools** (F12) → pestanya **Network** → filtre **Fetch/XHR**
3. Resol el **reCAPTCHA** que apareix a la pàgina
4. Als 3 selects (Grado, Família, Nivell), tria qualsevol opció a cadascun i fes clic a **Buscar**
5. A la pestanya Network apareixerà una petició `buscadorGeneralA` — fes clic dret → **Copy → Copy as cURL**
6. Del cURL copiat, localitza el valor de `-b '...'` — és la cadena de cookies:
   ```
   JSESSIONID=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX; __Host-todofp.es=YYYY...
   ```

### Actualitzar al VPS

```bash
nano /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/.env
# Substituir la línia BUSCADOR_COOKIES= pel nou valor
```

```
BUSCADOR_COOKIES=JSESSIONID=XXXXXXXX; __Host-todofp.es=YYYY...
```

No cal reiniciar el servei — el pipeline llegeix `.env` a cada execució.

### Verificar que funciona

```bash
curl -X POST https://grausfp.masellas.info/api/admin/refresh \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

Ha de retornar JSON amb `total` ~12.768 i `errors: []`.

### Freqüència de caducitat

La sessió dura mentre el servidor de todofp.es mantingui el `JSESSIONID` actiu.
En pràctica caduca en dies/setmanes. Si el frontend mostra 0 resultats o el refresh
falla, renovar les cookies seguint els passos anteriors.
