import os
from django.core.exceptions import ImproperlyConfigured

PRODUCTION_REQUIRED_ENV = [
    "DJANGO_SECRET_KEY", "DATABASE_URL", "REDIS_URL", "DJANGO_ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS",
    "EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL",
    "MANYUMBU_STUN_SERVERS", "MANYUMBU_TURN_SERVER", "MANYUMBU_TURN_USERNAME", "MANYUMBU_TURN_PASSWORD",
    "MANYUMBU_MEDIA_PROVIDER", "MANYUMBU_API_URL",
]

CLOUDINARY_REQUIRED_ENV = ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"]


def validate_production_environment(env=None):
    env = env or os.environ
    production_like = env.get("MANYUMBU_ENV", "development") == "production" or env.get("DJANGO_DEBUG", "1") == "0"
    if not production_like:
        return []
    if env.get("SKIP_EMAIL_VERIFICATION", "False").lower() == "true":
        raise ImproperlyConfigured("SKIP_EMAIL_VERIFICATION cannot be enabled in production.")
    missing = [name for name in PRODUCTION_REQUIRED_ENV if not env.get(name)]
    if env.get("MANYUMBU_MEDIA_PROVIDER", "").lower() != "cloudinary":
        missing.append("MANYUMBU_MEDIA_PROVIDER=cloudinary")
    missing.extend([name for name in CLOUDINARY_REQUIRED_ENV if not env.get(name)])
    if missing:
        raise ImproperlyConfigured("Missing production environment variables: " + ", ".join(missing))
    return []
