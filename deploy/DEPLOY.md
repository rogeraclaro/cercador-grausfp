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

El `.env` ha de contenir (vegeu `fp-cercador/backend/.env.example`):

```
# — Obligatori —
ADMIN_TOKEN=<token-segur-aleatori>
SECRET_KEY=<token-segur-aleatori>   # python3 -c "import secrets; print(secrets.token_hex(32))"
BASE_URL=https://<el-teu-domini>    # sense trailing slash; usat als emails d'auth

# — Email (Brevo SMTP) — necessari per a verificació de compte i reset de contrasenya
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=<compte@domini.com>
BREVO_SMTP_KEY=<API_key_brevo>
EMAIL_FROM=noreply@<domini.com>
EMAIL_FROM_NAME=Cercador FP España

# — Brevo API (novetats/newsletters, opcional) —
BREVO_API_KEY=
BREVO_LIST_ID=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=Cercador FP España
```

> Si `SECRET_KEY` és buit, l'app arrenca però els logs mostraran un warning.
> Si `BREVO_SMTP_KEY` és buit, els emails d'auth no s'envien però el registre
> i el login segueixen funcionant (errors als logs).

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

> **Important — no apugis `--workers`**: el backend manté l'scheduler
> (APScheduler), el lock de refresh i l'estat de `/api/refresh-status` en
> memòria del procés. Amb més d'un worker, el refresh programat s'executaria
> duplicat i l'estat seria inconsistent entre workers. Per absorbir més
> trànsit, apuja `--threads`, no `--workers`.

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

> **Nota (pla 006 — gzip):** `nginx-cloudpanel.conf` inclou directives `gzip` per
> comprimir respostes JSON del proxy. Després d'aplicar el fitxer al VPS, recarrega
> nginx: `nginx -t && systemctl reload nginx`.

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

> **Nota**: `backend/data/` no està versionat. En un desplegament nou,
> `/api/ofertes` retornarà 503 fins que llancis el primer refresh des del
> panell admin (o via `POST /api/admin/refresh`).

Per generar les dades al VPS:

```bash
curl -X POST https://DOMINI_AQUI/api/admin/refresh \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
# Monitorar progrés:
curl https://DOMINI_AQUI/api/refresh-status
```

**Nota:** El refresh triga ~4s.

## 9. Base de dades SQLite

La BD (`fp-cercador/backend/data/fp_cercador.db`) es crea automàticament la
primera vegada que arrenca l'app. No cal cap pas manual de migració: `init_db()`
aplica els scripts de `fp-cercador/backend/migrations/` en ordre.

**Còpia de seguretat (cron nocturn, retenció 7 dies)**

```bash
# Crear directori de backups
mkdir -p /home/masellas-grausfp/backups/fp-cercador

# Afegir al cron de root: crontab -e
0 3 * * * sqlite3 /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/fp_cercador.db \
    ".backup /home/masellas-grausfp/backups/fp-cercador/fp_cercador_$(date +\%Y\%m\%d).db" && \
    find /home/masellas-grausfp/backups/fp-cercador -name "*.db" -mtime +7 -delete
```

Verificar que el cron ha funcionat (el dia següent):
```bash
ls -lh /home/masellas-grausfp/backups/fp-cercador/
```

## 10. Checklist de verificació auth en producció

Abans de donar per bo el desplegament d'auth, comprova:

- [ ] **Same-origin**: frontend i backend se serveixen des del mateix domini
  (nginx fa proxy de `/api/` al port 8033). Les cookies d'auth no necessiten
  CORS en producció — same-origin és transparent.
- [ ] **Cookie Secure**: quan l'app corre amb gunicorn (`app.debug = False`),
  les cookies es generen amb `Secure=True` automàticament. Verificar:
  ```bash
  curl -X POST https://<DOMINI>/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrongpw"}' -v 2>&1 | grep -i "set-cookie"
  # Ha de mostrar: Secure; HttpOnly; SameSite=Lax
  ```
- [ ] **Email d'auth funcional**: registra un compte de prova i verifica que
  arriba l'email de verificació. Si no arriba:
  ```bash
  journalctl -u fp-cercador -f | grep "Error enviant"
  ```
- [ ] **Rate limiting**: 6 intents de login fallits consecutius retornen 429.
- [ ] **BD creada**: `ls -lh fp-cercador/backend/data/fp_cercador.db` ha d'existir
  amb mida > 0 després del primer arranc.

**Headers de seguretat nginx (recomanat)**

Afegir al bloc `server` de `nginx-cloudpanel.conf` (o via CloudPanel UI
> Nginx Configuration > Vhost):

```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

Recarregar nginx: `nginx -t && systemctl reload nginx`.

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

## Sobre les cookies del buscador

Des del refactor auto-cookies (maig 2026), el scraper obté les cookies
automàticament amb un GET de bootstrap a
`https://www.todofp.es/buscadorgradosfp/buscador` a cada refresh.
No cal configurar res. Si el refresh falla amb "Bootstrap no ha retornat
JSESSIONID", inspecciona `backend/data/last_failure.html` per veure la
resposta del servidor.
