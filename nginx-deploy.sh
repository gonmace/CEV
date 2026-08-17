#!/bin/bash
# nginx-deploy.sh — instala/actualiza la config de nginx
# Uso: bash nginx-deploy.sh
# IMPORTANTE: ejecutar solo una vez (primer deploy) o cuando cambie nginx.conf.
#             NO ejecutar en cada deploy — certbot modifica el archivo para SSL
#             y sobreescribirlo eliminaria los certificados configurados.

set -e

if [ ! -f .env ]; then
    echo "Error: no se encontró el archivo .env. Ejecuta: bash setup.sh"
    exit 1
fi
set -a
source .env
set +a

PROJECT_NAME=${PROJECT_NAME:?La variable PROJECT_NAME no está definida en .env}
APP_PORT=${APP_PORT:-8000}
DOMAIN=${DOMAIN:?La variable DOMAIN no está definida en .env}
PROJECT_DIR=$(pwd)
N8N_DOMAIN=${N8N_DOMAIN:-}
N8N_PORT=${N8N_PORT:-8001}
N8N_MCP_ENABLED=${N8N_MCP_ENABLED:-}
N8N_MCP_PORT=${N8N_MCP_PORT:-8002}

NGINX_OUT="${PROJECT_NAME}.conf"
NGINX_AVAILABLE="/etc/nginx/sites-available/${PROJECT_NAME}.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/${PROJECT_NAME}.conf"

echo "▶ Generando ${NGINX_OUT}..."

# Usar Python para sustituciones seguras (evita problemas con caracteres especiales en sed)
python3 - << PYEOF
import re

def substitute(content, replacements):
    for key, value in replacements.items():
        content = content.replace('{{' + key + '}}', value)
    return content

# ── Bloque Django ──────────────────────────────────────────────────────────────
with open('nginx.conf') as f:
    django_block = substitute(f.read(), {
        'DOMAIN': '${DOMAIN}',
        'APP_PORT': '${APP_PORT}',
        'PROJECT_DIR': '${PROJECT_DIR}',
    })

output = django_block

# ── Bloque n8n (si N8N_DOMAIN está definido) ──────────────────────────────────
n8n_domain = '${N8N_DOMAIN}'
if n8n_domain:
    with open('nginx-n8n.conf') as f:
        n8n_block = substitute(f.read(), {
            'N8N_DOMAIN': '${N8N_DOMAIN}',
            'N8N_PORT': '${N8N_PORT}',
        })

    # ── Bloque MCP (si N8N_MCP_ENABLED=true) ──────────────────────────────────
    mcp_enabled = '${N8N_MCP_ENABLED}'
    if mcp_enabled == 'true':
        with open('nginx-n8n-mcp.conf') as f:
            mcp_block = substitute(f.read(), {
                'N8N_MCP_PORT': '${N8N_MCP_PORT}',
            })
        n8n_block = n8n_block.replace('{{MCP_BLOCK}}', mcp_block)
    else:
        n8n_block = n8n_block.replace('{{MCP_BLOCK}}', '')

    output += n8n_block

with open('${NGINX_OUT}', 'w') as f:
    f.write(output)

print("  Config generada correctamente.")
PYEOF

echo "▶ Instalando config en nginx..."
sudo cp "${NGINX_OUT}" "${NGINX_AVAILABLE}"

if [ ! -L "${NGINX_ENABLED}" ]; then
    sudo ln -s "${NGINX_AVAILABLE}" "${NGINX_ENABLED}"
    echo "  Symlink creado: ${NGINX_ENABLED}"
fi

sudo nginx -t
sudo systemctl reload nginx
echo "✓ nginx actualizado y recargado."
echo ""
echo "Próximo paso: obtener certificado SSL con certbot:"
CERTBOT_CMD="sudo certbot --nginx -d ${DOMAIN}"
[ -n "${N8N_DOMAIN}" ] && CERTBOT_CMD="${CERTBOT_CMD} -d ${N8N_DOMAIN}"
echo "  ${CERTBOT_CMD}"
