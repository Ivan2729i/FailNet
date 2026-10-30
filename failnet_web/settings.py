
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured



# ==================================================
# DIRECTORIOS Y VARIABLES DE ENTORNO
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=False,
)

# ==================================================
# FUNCIONES PARA LEER CONFIGURACIÓN
# ==================================================

def env(nombre, default=None, required=False):

    valor = os.getenv(nombre, default)
    if required and (
        valor is None or not str(valor).strip()
    ):
        raise ImproperlyConfigured(
            f"Falta configurar {nombre} en el entorno."
        )
    return valor

def env_bool(nombre, default=False):
    valor = os.getenv(nombre)
    if valor is None:
        return default
    valor = valor.strip().lower()
    if valor in ("true", "1", "yes", "on"):
        return True
    if valor in ("false", "0", "no", "off"):
        return False
    raise ImproperlyConfigured(
        f"{nombre} debe ser True o False."
    )

def env_int(nombre, default=0):
    valor = env(nombre, default=str(default))
    try:
        numero = int(valor)
    except (ValueError, TypeError):
        raise ImproperlyConfigured(
            f"{nombre} debe ser un número entero."
        )
    if numero < 0:
        raise ImproperlyConfigured(
            f"{nombre} no puede ser negativo."
        )
    return numero

def env_list(nombre, default=""):
    valor = env(nombre, default=default)
    return [
        item.strip()
        for item in valor.split(",")
        if item.strip()
    ]

# ==================================================
# SEGURIDAD Y CONFIGURACIÓN GENERAL
# ==================================================

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    required=True,
)
DEBUG = env_bool(
    "DJANGO_DEBUG",
    default=False,
)
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS"
)
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS"
)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Configura DJANGO_ALLOWED_HOSTS "
        "antes de ejecutar en producción."
    )

# ==================================================
# APLICACIONES INSTALADAS
# ==================================================

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django_mongodb_backend",
    "dashboard.apps.DashboardConfig",
]

# ==================================================
# MIDDLEWARE
# ==================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==================================================
# CONFIGURACIÓN DEL PROYECTO
# ==================================================

ROOT_URLCONF = "failnet_web.urls"
WSGI_APPLICATION = "failnet_web.wsgi.application"
ASGI_APPLICATION = "failnet_web.asgi.application"

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django."
            "DjangoTemplates"
        ),
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

# ==================================================
# BASE DE DATOS
# ==================================================

MONGODB_HOST = env(
    "MONGODB_HOST",
    required=True,
)
MONGODB_USER = env(
    "MONGODB_USER",
    required=True,
)
MONGODB_PASSWORD = env(
    "MONGODB_PASSWORD",
    required=True,
)
MONGODB_DB_NAME = env(
    "MONGODB_DB_NAME",
    required=True,
)
if not MONGODB_HOST.startswith(
    "mongodb+srv://"
):
    raise ImproperlyConfigured(
        "MONGODB_HOST debe comenzar "
        "con mongodb+srv://"
    )

DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "NAME": MONGODB_DB_NAME,
        "HOST": MONGODB_HOST,
        "USER": MONGODB_USER,
        "PASSWORD": MONGODB_PASSWORD,
        "OPTIONS": {
            "authSource": "admin",
            "retryWrites": True,
            "w": "majority",
        },
    }
}

# ==================================================
# CONFIGURACIÓN DE MONGODB
# ==================================================

DEFAULT_AUTO_FIELD = (
    "django_mongodb_backend.fields.ObjectIdAutoField"
)
DATABASE_ROUTERS = [
    "django_mongodb_backend.routers.MongoRouter"
]

# ==================================================
# IDIOMA Y ZONA HORARIA
# ==================================================

LANGUAGE_CODE = env(
    "DJANGO_LANGUAGE_CODE",
    default="es-mx",
)
TIME_ZONE = env(
    "DJANGO_TIME_ZONE",
    default="America/Mexico_City",
)
USE_I18N = True
USE_TZ = True

# ==================================================
# ARCHIVOS ESTÁTICOS
# ==================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.is_dir():
    STATICFILES_DIRS.append(STATIC_DIR)

# ==================================================
# ARCHIVOS CARGADOS
# ==================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int(
    "DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE",
    default=2621440,
)

# ==================================================
# SEGURIDAD HTTP
# ==================================================

SECURE_SSL_REDIRECT = env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    default=not DEBUG,
)
CSRF_COOKIE_SECURE = env_bool(
    "DJANGO_CSRF_COOKIE_SECURE",
    default=not DEBUG,
)
SESSION_COOKIE_SECURE = env_bool(
    "DJANGO_SESSION_COOKIE_SECURE",
    default=not DEBUG,
)
SECURE_HSTS_SECONDS = env_int(
    "DJANGO_SECURE_HSTS_SECONDS",
    default=0,
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = (
    "strict-origin-when-cross-origin"
)
X_FRAME_OPTIONS = "DENY"

# ==================================================
# CORREO ELECTRÓNICO
# ==================================================

MAILERS = {
    "default": {
        "BACKEND": (
            "django.core.mail.backends."
            "console.EmailBackend"
        ),
    },
}

# ==================================================
# LOGGING
# ==================================================

LOG_LEVEL = env(
    "DJANGO_LOG_LEVEL",
    default="INFO",
).upper()
LOG_LEVELS_VALIDOS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}
if LOG_LEVEL not in LOG_LEVELS_VALIDOS:
    raise ImproperlyConfigured(
        "DJANGO_LOG_LEVEL contiene "
        "un nivel no válido."
    )
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": (
                "[{levelname}] "
                "{asctime} "
                "{name}: {message}"
            ),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "dashboard": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

