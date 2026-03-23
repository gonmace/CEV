#!/bin/bash
# deploy.sh — despliega el proyecto en el VPS
# Uso: bash deploy.sh

set -e

# ── Cargar variables del .env ──────────────────────────────────────────────────
if [ ! -f .env ]; then
    echo "Error: no se encontró el archivo .env"
    exit 1
fi
set -a
source .env
set +a

PROJECT_NAME=${PROJECT_NAME:?La variable PROJECT_NAME no está definida en .env}
APP_PORT=${APP_PORT:-8000}
DOMAIN=${DOMAIN:?La variable DOMAIN no está definida en .env}
PROJECT_DIR=$(pwd)

NGINX_TEMPLATE="${PROJECT_NAME}.conf"
NGINX_AVAILABLE="/etc/nginx/sites-available/${PROJECT_NAME}.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/${PROJECT_NAME}.conf"

echo "━━━ Desplegando: ${PROJECT_NAME} (${DOMAIN}) ━━━"

# ── 1. Actualizar código ───────────────────────────────────────────────────────
echo "▶ Actualizando código..."
git pull origin main

# ── 2. Generar archivo nginx con nombre del proyecto ──────────────────────────
echo "▶ Generando ${NGINX_TEMPLATE}..."

sed -e "s|{{DOMAIN}}|${DOMAIN}|g" \
    -e "s|{{APP_PORT}}|${APP_PORT}|g" \
    -e "s|{{PROJECT_DIR}}|${PROJECT_DIR}|g" \
    nginx.conf > "${NGINX_TEMPLATE}"

# ── 3. Copiar a nginx y activar ───────────────────────────────────────────────
echo "▶ Instalando config en nginx..."

sudo cp "${NGINX_TEMPLATE}" "${NGINX_AVAILABLE}"

if [ ! -L "${NGINX_ENABLED}" ]; then
    sudo ln -s "${NGINX_AVAILABLE}" "${NGINX_ENABLED}"
    echo "  Symlink creado: ${NGINX_ENABLED}"
fi

sudo nginx -t
sudo systemctl reload nginx
echo "  nginx recargado."

# ── 4. Reconstruir y reiniciar contenedores ────────────────────────────────────
echo "▶ Reconstruyendo contenedores Docker..."
docker compose down
docker compose up -d --build

echo ""
echo "✓ Despliegue completado → http://${DOMAIN}"
