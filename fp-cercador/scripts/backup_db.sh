#!/bin/bash
# Còpia diària de la base de dades d'usuaris (comptes, favorits, alertes) de GrausFP.
# Al VPS, al crontab de root (el servei corre com a root i la BD, en mode WAL, és seva):
#   30 3 * * * /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/scripts/backup_db.sh
# Còpia externa: remot rclone "grausfp-drive" al root (vegeu el final del fitxer).
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

# Còpia fora del servidor (Google Drive via rclone, remot configurat al root amb scope drive.file).
# Si el remot no existeix o la pujada falla, la còpia local ja està feta: només s'avisa al log.
REMOTE="${GRAUSFP_BACKUP_REMOTE:-grausfp-drive:GrausFP-copies}"
REMOTE_KEEP="${GRAUSFP_BACKUP_REMOTE_KEEP:-90d}"
if rclone listremotes 2>/dev/null | grep -qx "${REMOTE%%:*}:"; then
  if rclone copy "$out" "$REMOTE" && rclone delete "$REMOTE" --min-age "$REMOTE_KEEP" --include 'fp_cercador-*.db.gz'; then
    echo "$(date '+%F %T') OK pujada a $REMOTE"
  else
    echo "$(date '+%F %T') ERROR: no s'ha pogut pujar a $REMOTE" >&2
    exit 1
  fi
else
  echo "$(date '+%F %T') AVÍS: remot ${REMOTE%%:*} no configurat, sense còpia externa" >&2
fi
