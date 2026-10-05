# Constructor EV (CEV)

Aplicación Django para gestión de proyectos de construcción con generación de especificaciones técnicas asistida por IA.

## Stack

- **Backend:** Django 5.1+, Gunicorn
- **Base de datos:** SQLite (dev local) / PostgreSQL 17 (Docker y prod)
- **Estilos:** Tailwind CSS v4 + DaisyUI v5
- **IA / Automatización:** n8n (workflows de generación de contenido)
- **Exportación:** python-docx (Word), reportlab (PDF)
- **Archivos estáticos:** Whitenoise
- **Producción:** Docker Compose + Nginx (gzip)

## Apps

| App | URL | Descripción |
|-----|-----|-------------|
| `home` | `/` | Landing page |
| `proyectos` | `/proyectos/` | Gestión de proyectos y especificaciones |
| `servicios` | `/servicios/` | Catálogo de servicios con flujo IA de 5 pasos |
| `pliego_licitacion` | `/pliego/` | Generación de pliegos de licitación |
| `ubi_web` | `/ubicaciones/` | Ubicaciones geográficas dentro de proyectos |

## Desarrollo local

### 1. Clonar y configurar entorno

```bash
git clone https://github.com/gonmace/CEV.git
cd CEV
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
make install
```

### 2. Variables de entorno

```bash
cp .env.example .env
```

Para desarrollo con Django local + SQLite basta con:

```env
DEBUG=True
```

Para desarrollo con PostgreSQL y n8n en Docker:

```env
DEBUG=True
PROJECT_NAME=cev
POSTGRES_DB=cev_db
POSTGRES_USER=cev_user
POSTGRES_PASSWORD=contraseña
N8N_ENCRYPTION_KEY=dev-key-cualquiera
```

### 3. Iniciar el servidor

**Solo Django (SQLite):**
```bash
make dev
```

**Con PostgreSQL + n8n en Docker:**
```bash
make dev-up   # levanta PostgreSQL y n8n
make dev      # corre Django apuntando al postgres del contenedor
```

O manualmente en dos terminales:
```bash
# Terminal 1 — watcher de Tailwind
python manage.py tailwind start

# Terminal 2 — servidor Django
python manage.py migrate
python manage.py runserver
```

- Django: http://127.0.0.1:8000
- n8n: http://localhost:5678

## Flujo de generación de servicios (5 pasos)

1. **Paso 1** — Crear servicio (categoría, subcategoría, solicitante)
2. **Paso 2** — Generar objetivo con IA
3. **Paso 3** — Generar alcance con IA (clasificación + equipos + tablas)
4. **Paso 4** — Generar secciones complementarias con IA
5. **Paso 5** — Revisar y guardar documento consolidado

## n8n — workflows

Los workflows se versionan en `n8n/workflows/`.

```bash
make n8n-export   # exporta workflows desde el contenedor
git add n8n/workflows/
git commit -m "feat: actualizar workflows"
git push
```

## Producción (VPS)

### Variables obligatorias

```env
PROJECT_NAME=cev
DOMAIN=tudominio.com
APP_PORT=8000
ADMIN_URL=mi-panel-secreto/
DEBUG=False
SECRET_KEY=clave-secreta-segura
POSTGRES_DB=cev_db
POSTGRES_USER=cev_user
POSTGRES_PASSWORD=contraseña-segura
N8N_ENCRYPTION_KEY=clave-larga-y-secreta
```

### Desplegar

```bash
make deploy
```

## Comandos

```bash
make install      # pip install + tailwind install
make dev-up       # levanta PostgreSQL + n8n en Docker
make dev          # migrate + tailwind start + runserver
make dev-down     # detiene contenedores de desarrollo
make n8n-export   # exporta workflows de n8n
make migrate      # python manage.py migrate
make migrations   # python manage.py makemigrations
make superuser    # python manage.py createsuperuser
make collect      # collectstatic
make deploy       # bash deploy.sh
make logs         # docker compose logs -f django
make down         # docker compose down
```
