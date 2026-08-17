#!/bin/bash
# docker/backup.sh — backup de Postgres (Django + n8n) y media/, con rotación.
#
# No existía ningún backup: un fallo de disco en el VPS pierde todos los proyectos,
# especificaciones e imágenes sin posibilidad de recuperación.
#
# Uso manual:
#   bash docker/backup.sh
#
# Uso por cron (ejemplo: todos los días a las 3am, retiene 14 backups):
#   0 3 * * * cd /ruta/al/proyecto && BACKUP_KEEP=14 bash docker/backup.sh >> /var/log/cev-backup.log 2>&1

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "Error: no se encontró .env" >&2
    exit 1
fi
set -a
source .env
set +a

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP="${BACKUP_KEEP:-7}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${BACKUP_DIR}/${TIMESTAMP}"

POSTGRES_CONTAINER="${PROJECT_NAME}_db"
POSTGRES_USER="${POSTGRES_USER:?POSTGRES_USER no está definido en .env}"
POSTGRES_DB="${POSTGRES_DB:?POSTGRES_DB no está definido en .env}"

mkdir -p "${DEST}"
echo "▶ Backup en ${DEST}"

# ── 1. Postgres: base de Django ────────────────────────────────────────────────
if docker ps --format '{{.Names}}' | grep -qx "${POSTGRES_CONTAINER}"; then
    echo "  - pg_dump ${POSTGRES_DB}..."
    docker exec "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        | gzip > "${DEST}/${POSTGRES_DB}.sql.gz"

    # La base de n8n vive en la misma instancia (ver docker/init-db.sql) cuando el
    # profile "n8n" está activo.
    if docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -lqt | cut -d'|' -f1 | grep -qw n8n; then
        echo "  - pg_dump n8n..."
        docker exec "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" -d n8n \
            | gzip > "${DEST}/n8n.sql.gz"
    fi
else
    echo "  ! Contenedor ${POSTGRES_CONTAINER} no está corriendo — se omite el dump de Postgres." >&2
fi

# ── 2. media/ ────────────────────────────────────────────────────────────────────
if [ -d media ] && [ -n "$(ls -A media 2>/dev/null)" ]; then
    echo "  - tar de media/..."
    tar -czf "${DEST}/media.tar.gz" media/
else
    echo "  ! media/ vacío o inexistente — se omite." >&2
fi

# ── 3. Rotación: retener solo los últimos BACKUP_KEEP ────────────────────────────
echo "  - rotando (retener ${BACKUP_KEEP})..."
ls -1dt "${BACKUP_DIR}"/*/ 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | xargs -r rm -rf

echo "✓ Backup completo: $(du -sh "${DEST}" | cut -f1)"
echo ""
echo "Prueba de restore recomendada (no la hace este script):"
echo "  gunzip -c ${DEST}/${POSTGRES_DB}.sql.gz | docker exec -i ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d <db_de_prueba>"
