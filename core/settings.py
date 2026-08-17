import os
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

ADMIN_URL = config('ADMIN_URL', default='admin/')

SITE_LOGO_URL = config('SITE_LOGO_URL', default='')

# n8n webhooks
# Sin default al dominio de producción: un .env incompleto (a un dev nuevo, o a un
# entorno de staging) antes disparaba workflows reales de n8n y consumía créditos de
# IA de verdad sin que nadie lo pidiera. Con el default vacío, la URL del webhook queda
# mal formada y la llamada falla explícitamente en vez de aterrizar en producción.
N8N_BASE_URL = config('N8N_BASE_URL', default='')

# Header que Django manda en cada llamada a un webhook de n8n (ver
# pliego_licitacion.views.llamar_webhook, servicios/views.py y ubi_web/views.py).
# Los nodos Webhook del lado de n8n están configurados con Header Auth usando el mismo
# nombre/valor (credencial "CEV Django webhook token") — SIN esto, cualquiera que
# conociera la URL del webhook podía dispararlo y quemar créditos de OpenAI sin pasar
# por el sistema de créditos de la app. Vacío por defecto: si falta, las llamadas fallan
# con 401 en vez de silenciosamente no autenticar nada.
N8N_WEBHOOK_TOKEN = config('N8N_WEBHOOK_TOKEN', default='')
N8N_WEBHOOK_TOKEN_HEADER = 'X-N8N-Webhook-Token'

# Application definition

INSTALLED_APPS = [
    'home',
    'accounts',
    'proyectos',
    'servicios',
    'pliego_licitacion',
    'demo',
    'ubi_web',

    'crispy_forms',
    'crispy_tailwind',

    'axes',

    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

INSTALLED_APPS += ['tailwind', 'theme']
TAILWIND_APP_NAME = 'theme'

if DEBUG:
    for local_host in ('localhost', '127.0.0.1', '[::1]'):
        if local_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(local_host)
    INSTALLED_APPS += ['django_browser_reload']
    MIDDLEWARE += ['django_browser_reload.middleware.BrowserReloadMiddleware']
    INTERNAL_IPS = ['127.0.0.1', '::1']
    # Ruta del npm local (configurable por .env para no atarla a una versión de nvm)
    NPM_BIN_PATH = config('NPM_BIN_PATH', default='/home/gonzalo/.nvm/versions/node/v24.18.0/bin/npm')

# Impersonación de usuarios reales por el superuser — en dev Y en producción (el gate es
# is_superuser, no DEBUG; ver accounts/middleware.py). Va después de AuthenticationMiddleware
# porque necesita request.user, y ANTES de ModuleAccessMiddleware para que al impersonar se
# apliquen los permisos del usuario impersonado y no los del superuser.
MIDDLEWARE += ['accounts.middleware.ImpersonationMiddleware']

# Acceso a los módulos Proyectos/Servicios según la capacidad del usuario (ver
# accounts/permissions.py: MODULE_ACCESS). Va al final: necesita request.user ya resuelto,
# incluida la sustitución que hace el middleware de impersonación.
MIDDLEWARE += ['accounts.middleware.ModuleAccessMiddleware']

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'home.context_processors.site_logo',
                'accounts.context_processors.nav_flags',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database: SQLite por defecto en dev, PostgreSQL si se define POSTGRES_DB
if config('POSTGRES_DB', default=''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('POSTGRES_DB'),
            'USER': config('POSTGRES_USER'),
            'PASSWORD': config('POSTGRES_PASSWORD'),
            'HOST': 'localhost' if DEBUG else config('POSTGRES_HOST', default='postgres'),
            # En dev se entra por el puerto publicado en el host (POSTGRES_HOST_PORT del
            # docker-compose.dev.yml); en prod por el puerto interno del contenedor.
            'PORT': config('POSTGRES_HOST_PORT', default='5432') if DEBUG else config('POSTGRES_PORT', default='5432'),
            # Conexiones persistentes (10 min): evita el costo de abrir una conexión TCP
            # nueva por request, que con Postgres es notorio bajo carga.
            'CONN_MAX_AGE': 600,
        }
    }
elif DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    # Sin esto, un `.env` de producción incompleto (falta POSTGRES_DB) arrancaba en
    # SQLite sin avisar: el sitio "funcionaba" pero contra una base vacía y descartable,
    # en vez de fallar ruidosamente al levantar el contenedor.
    raise ImproperlyConfigured(
        'POSTGRES_DB no está definido y DEBUG=False: no se puede arrancar en producción '
        'sin una base de datos Postgres configurada (revisa el .env del servidor).'
    )

# ── Redis (cache y sesiones) ────────────────────────────────────────────────────
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
WHITENOISE_MANIFEST_STRICT = False

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email: consola en dev, SMTP en prod si se configura EMAIL_HOST
if config('EMAIL_HOST', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Un SMTP caído no debe retener al worker más que esto (core/mail.py envía en
# background, pero el correo de prueba de accounts:email_config es síncrono).
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)

# ── Google Maps ────────────────────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# ── Seguridad ──────────────────────────────────────────────────────────────────
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Solo añade `preload` a la cabecera Strict-Transport-Security; NO envía el dominio
    # a la lista de precarga de los navegadores por sí solo (eso es un paso manual en
    # hstspreload.org, y es cuasi-irreversible: no lo hagas hasta estar seguro de HTTPS).
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

X_FRAME_OPTIONS = 'DENY'

# ── django-axes (protección brute force) ──────────────────────────────────────
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hora
AXES_LOCKOUT_PARAMETERS = ['ip_address', 'username']

# En dev usa la base de datos (funciona con runserver sin Redis levantado);
# en prod usa el cache (Redis), más rápido bajo carga.
if DEBUG:
    AXES_HANDLER = 'axes.handlers.database.AxesDatabaseHandler'
else:
    AXES_HANDLER = 'axes.handlers.cache.AxesCacheHandler'
    AXES_CACHE = 'default'

# ── Content Security Policy ───────────────────────────────────────────────────
# django-csp 4.x lee solo CONTENT_SECURITY_POLICY (dict); las variables sueltas
# CSP_DEFAULT_SRC/CSP_SCRIPT_SRC/... son de la API <4.0 y se ignoran en silencio
# (confirmado: con esas variables el middleware no emitía ninguna cabecera CSP).
#
# script-src/style-src llevan 'unsafe-inline' como transición: hay ~60 templates con
# <script> inline sin nonce (ver templates/base.html, pliego_licitacion/paso8_resultado.html,
# etc.) — activar una política estricta tal cual los rompía a todos en el navegador.
# Endurecer esto a nonces (`request.csp_nonce` + `nonce="{{ request.csp_nonce }}"` en cada
# <script>) es trabajo pendiente; mientras tanto, la defensa real contra XSS es sanitizar el
# HTML generado desde markdown (ver core/sanitize.py), no esta cabecera.
#
# Hosts externos que el proyecto carga de verdad (comprobado por grep sobre los templates):
# TOAST UI Editor (uicdn.toast.com) en los editores de contenido, SortableJS (jsdelivr) para
# reordenar por drag&drop, y Google Fonts en el demo. Sin listarlos, script-src/style-src/
# font-src 'self' los bloquea silenciosamente y esas páginas dejan de funcionar.
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", 'https://uicdn.toast.com', 'https://cdn.jsdelivr.net'],
        'style-src': ["'self'", "'unsafe-inline'", 'https://uicdn.toast.com', 'https://fonts.googleapis.com'],
        'img-src': ["'self'", 'data:'],
        'font-src': ["'self'", 'https://uicdn.toast.com', 'https://fonts.gstatic.com'],
        'connect-src': ["'self'"] if not DEBUG else ["'self'", 'ws://localhost:*', 'ws://127.0.0.1:*'],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'frame-ancestors': ["'self'"],
    }
}

# ── Admins y logging ──────────────────────────────────────────────────────────
ADMINS = [('Admin', 'admin@example.com')]
MANAGERS = ADMINS

# ── Crispy Forms ───────────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# ── Auth redirects ─────────────────────────────────────────────────────────────
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'accounts:login'

# ── Sesión ─────────────────────────────────────────────────────────────────────
# Con «Recordarme» la sesión dura 30 días; sin marcar, el form la acorta con
# set_expiry(0) para que expire al cerrar el navegador (ver CustomLoginView).
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 días

# ── Sites framework ────────────────────────────────────────────────────────────
SITE_ID = 1

# ── django-allauth ─────────────────────────────────────────────────────────────
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True

# Sin estos dos, `is_open_for_signup()` cae en el default de allauth (True) y
# /accounts/signup/ + el login de Google quedan abiertos a cualquiera, saltándose
# la allow-list de accounts.access. Ver accounts/adapters.py.
ACCOUNT_ADAPTER = 'accounts.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.SocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

DEMO_MAX_TRIALS = 2

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'}
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            # 'mail_admins' solo: ADMINS sigue en el placeholder admin@example.com y
            # send_mail usa fail_silently=True, así que un 500 en prod no dejaba rastro
            # en ningún lado (ni docker logs ni correo). 'console' asegura que el
            # traceback llegue a stderr, que gunicorn (--error-logfile -) vuelca a
            # docker logs.
            'handlers': ['mail_admins', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
        **({
            # Sin esto, los logger.error(..., exc_info=True) de las vistas del pliego no
            # dejan rastro en runserver: diagnosticar el spinner colgado en "Guardando
            # título..." hubo que reconstruirlo desde la BD y las ejecuciones de n8n.
            'pliego_licitacion': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
        } if DEBUG else {}),
    },
}
