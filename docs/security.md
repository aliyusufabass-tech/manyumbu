# Security

- Keep `.env`, database files, uploads, generated builds, caches, keys, and credentials out of Git.
- Use HTTPS for production API/admin/mobile traffic.
- Configure `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, and secure cookie/HSTS settings for production.
- Configure Redis for Channels and Celery in production.
- Keep STUN/TURN credentials secret and rotate them on a fixed schedule.
- Use Sentry or equivalent monitoring through `SENTRY_DSN`; do not log passwords, tokens, or provider credentials.
- Data export and deletion requests require recent authentication confirmation from the client.
