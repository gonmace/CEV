# ── Stage 1: compilar CSS con Node ────────────────────────────────────────────
FROM node:22-slim AS css-builder

# Copiar todo el proyecto para que Tailwind pueda escanear los templates
COPY . /app/

WORKDIR /app/theme/static_src
RUN npm install
RUN npm run build

# ── Stage 2: compilar dependencias Python ─────────────────────────────────────
# gcc/libpq-dev solo hacen falta para compilar wheels (algunos paquetes de
# requirements.txt no traen wheel prebuilt para todas las plataformas); no deben
# quedar en la imagen final — son superficie de ataque y peso muerto.
FROM python:3.12-slim AS python-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 3: imagen de producción ─────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings
ENV PATH=/home/appuser/.local/bin:$PATH

# UID/GID fijos (no el default 1000 del sistema) para poder alinear el dueño de los
# bind mounts (./staticfiles, ./media) sin adivinar qué UID trae la imagen base.
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -m -s /usr/sbin/nologin appuser

WORKDIR /app

# Paquetes instalados por el usuario en el stage anterior (sin gcc/libpq-dev acá).
COPY --from=python-builder /root/.local /home/appuser/.local

COPY --chown=appuser:appuser ./ ./

# Copiar el CSS compilado desde el stage 1
COPY --from=css-builder --chown=appuser:appuser /app/static/css/dist/ ./static/css/dist/

USER appuser

CMD ["sh", "entrypoint.sh"]
