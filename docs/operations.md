# Operations

Health endpoints:

- `GET /health/`
- `GET /health/live/`
- `GET /health/ready/`

Background jobs are defined in `manyumbu10.tasks` for notifications, story expiry, media processing, data export expiry, account deletion review, cleanup, metrics aggregation, and backup checkpoints.

Run workers with:

```sh
sh scripts/start_worker.sh
sh scripts/start_beat.sh
```

Monitor API latency, database saturation, Redis availability, WebSocket connection count, Celery queue depth, email delivery failures, push delivery failures, media processing failures, and backup success/failure.
