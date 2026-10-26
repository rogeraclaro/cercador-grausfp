#!/bin/bash
# Còpia diària de la base de dades d'usuaris (comptes, favorits, alertes) de GrausFP.
# Al VPS, al crontab de root (el servei corre com a root i la BD, en mode WAL, és seva):
#   30 3 * * * /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/scripts/backup_db.sh
# Fa servir l'.backup de sqlite3, que és segur amb el servei en marxa (un cp a mig escriure no ho és).
set -euo pipefail

DB="${GRAUSFP_DB:-/home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/fp_cercador.db}"
DEST="${GRAUSFP_BACKUP_DIR:-/home/masellas-grausfp/backups/databases}"
KEEP_DAYS="${GRAUSFP_BACKUP_KEEP_DAYS:-30}"

mkdir -p "$DEST"
tmp="$DEST/.fp_cercador-$(date +%Y%m%d-%H%M%S).db"
trap 'rm -f "$tmp"' EXIT
sqlite3 "$DB" ".backup '$tmp'"

# Una còpia que no s'obre no serveix: es comprova abans de donar-la per bona.
if [ "$(sqlite3 "$tmp" 'PRAGMA integrity_check;')" != "ok" ]; then
  echo "$(date '+%F %T') ERROR: la còpia no passa integrity_check" >&2
  exit 1
fi

out="$DEST/fp_cercador-$(date +%Y%m%d).db.gz"
gzip -c "$tmp" > "$out"
chown --reference="$DEST" "$out" 2>/dev/null || true
find "$DEST" -name 'fp_cercador-*.db.gz' -mtime +"$KEEP_DAYS" -delete
echo "$(date '+%F %T') OK $out ($(du -h "$out" | cut -f1))"
