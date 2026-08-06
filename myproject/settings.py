import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-manyumbu-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host.strip()]

INSTALLED_APPS = [
    "daphne",
    "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "manyumbu10",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"
ASGI_APPLICATION = "myproject.asgi.application"


def database_config():
    url = os.getenv("DATABASE_URL")
    if not url:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    parsed = urlparse(url)
    if parsed.scheme.startswith("postgres"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or 5432,
        }
    return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}


DATABASES = {"default": database_config()}

AUTH_USER_MODEL = "manyumbu10.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Manyumbu <no-reply@manyumbu.local>")

MANYUMBU_ACCESS_TOKEN_LIFETIME = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "15")))
MANYUMBU_REFRESH_TOKEN_LIFETIME = timedelta(days=int(os.getenv("REFRESH_TOKEN_DAYS", "7")))

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [origin for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin]

REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [REDIS_URL]}}}
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

MANYUMBU_ALLOWED_WS_ORIGINS = [origin for origin in os.getenv("MANYUMBU_ALLOWED_WS_ORIGINS", "").split(",") if origin]


MANYUMBU_STUN_SERVERS = [server.strip() for server in os.getenv("MANYUMBU_STUN_SERVERS", "stun:stun.l.google.com:19302").split(",") if server.strip()]
MANYUMBU_TURN_SERVER = os.getenv("MANYUMBU_TURN_SERVER", "")
MANYUMBU_TURN_USERNAME = os.getenv("MANYUMBU_TURN_USERNAME", "")
MANYUMBU_TURN_PASSWORD = os.getenv("MANYUMBU_TURN_PASSWORD", "")
MANYUMBU_CALL_PROVIDER = os.getenv("MANYUMBU_CALL_PROVIDER", "none")
MANYUMBU_CALL_TIMEOUT_SECONDS = int(os.getenv("MANYUMBU_CALL_TIMEOUT_SECONDS", "45"))

# Phase 8 production-readiness configuration
MANYUMBU_ENV = os.getenv("MANYUMBU_ENV", "development")
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
MANYUMBU_PUBLIC_APP_URL = os.getenv("MANYUMBU_PUBLIC_APP_URL", "")
MANYUMBU_ADMIN_URL = os.getenv("MANYUMBU_ADMIN_URL", "")
MANYUMBU_API_URL = os.getenv("MANYUMBU_API_URL", "")
MANYUMBU_MEDIA_PROVIDER = os.getenv("MANYUMBU_MEDIA_PROVIDER", "local")
MANYUMBU_STORAGE_BUCKET = os.getenv("MANYUMBU_STORAGE_BUCKET", "")
MANYUMBU_PUSH_PROVIDER = os.getenv("MANYUMBU_PUSH_PROVIDER", "expo")
MANYUMBU_PUSH_ENABLED = os.getenv("MANYUMBU_PUSH_ENABLED", "0") == "1"
MANYUMBU_DELETION_GRACE_DAYS = int(os.getenv("MANYUMBU_DELETION_GRACE_DAYS", "30"))
MANYUMBU_RATE_LIMITS = {
    "auth": os.getenv("MANYUMBU_RATE_AUTH", "10/min"),
    "search": os.getenv("MANYUMBU_RATE_SEARCH", "60/min"),
    "messages": os.getenv("MANYUMBU_RATE_MESSAGES", "60/min"),
    "calls": os.getenv("MANYUMBU_RATE_CALLS", "20/hour"),
    "reports": os.getenv("MANYUMBU_RATE_REPORTS", "20/day"),
}
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL or "memory://")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL or "cache+memory://")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "0") == "1"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "0") == "1"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "0") == "1"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "0") == "1"
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "same-origin")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"format": "{\"level\": \"%(levelname)s\", \"logger\": \"%(name)s\", \"message\": \"%(message)s\"}", "style": "%"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}

from .env_validation import validate_production_environment
validate_production_environment()
