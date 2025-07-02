# flake8: noqa
from .base import *

DEBUG = True
# DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS += [
    'django_browser_reload',
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

INTERNAL_IPS = [
    "127.0.0.1",
]

EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / "sent_emails"

CORS_ALLOW_ALL_ORIGINS = True

CSRF_COOKIE_SECURE = False

CSRF_USE_SESSIONS = False
