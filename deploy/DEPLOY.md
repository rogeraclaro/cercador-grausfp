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
# Editar .env i posar el valor real d'ADMIN_TOKEN
nano fp-cercador/backend/.env
```

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

## 8. Primer refresh de dades

```bash
curl -X POST https://DOMINI_AQUI/api/admin/refresh \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
# Monitorar progrés:
curl https://DOMINI_AQUI/api/refresh-status
```

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
