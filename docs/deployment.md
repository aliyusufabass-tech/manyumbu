# Deployment

## Backend

Run the backend through ASGI so WebSockets are served by Daphne:

```sh
sh scripts/start_backend.sh
```

Required production environment variables are validated when `MANYUMBU_ENV=production` or `DJANGO_DEBUG=0`.

Use `docker-compose.production.yml` for a self-managed deployment with PostgreSQL, Redis, backend, worker, and beat services. Use `render.yaml` as a Render blueprint starting point. Set platform secrets outside Git.

## Admin Dashboard

The admin dashboard expects `VITE_API_URL` to point at the production API. `admin-dashboard/vercel.json` configures SPA rewrites and security headers.

## Mobile

The mobile app expects `EXPO_PUBLIC_API_URL`. Production builds require an HTTPS API URL and derive WSS WebSocket URLs automatically.
