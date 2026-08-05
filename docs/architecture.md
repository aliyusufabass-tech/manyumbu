# Architecture

Manyumbu uses Django, Django Channels, PostgreSQL, Redis, Celery, an Expo mobile client, and a Vite admin dashboard.

Production runtime roles:

- ASGI API/WebSocket web process.
- Celery worker for asynchronous jobs.
- Celery beat for schedules.
- PostgreSQL for relational data.
- Redis for Channels and Celery broker/backing services.
- Object/media provider for production uploads.
- External SMTP, push, monitoring, and STUN/TURN services.
