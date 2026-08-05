import os
from django.core.exceptions import ImproperlyConfigured

PRODUCTION_REQUIRED_ENV = [
    "DJANGO_SECRET_KEY", "DATABASE_URL", "REDIS_URL", "DJANGO_ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS",
    "EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL",
    "MANYUMBU_STUN_SERVERS", "MANYUMBU_TURN_SERVER", "MANYUMBU_TURN_USERNAME", "MANYUMBU_TURN_PASSWORD",
]


def validate_production_environment(env=None):
    env = env or os.environ
    if env.get("MANYUMBU_ENV", "development") != "production" and env.get("DJANGO_DEBUG", "1") != "0":
        return []
    missing = [name for name in PRODUCTION_REQUIRED_ENV if not env.get(name)]
    if missing:
        raise ImproperlyConfigured("Missing production environment variables: " + ", ".join(missing))
    return []
