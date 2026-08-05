# Manyumbu App

Manyumbu is a social media and messaging product built in phases. Phase 1 establishes the backend foundation, phone-number registration, email verification, login, password recovery, Google sign-in architecture, mobile auth screens, and an admin login shell.

## Structure

```text
myproject/
+-- mobile/
+-- manyumbu10/
+-- myproject/
+-- admin-dashboard/
+-- templates/
+-- docs/
+-- docker-compose.yml
+-- Dockerfile
+-- requirements.txt
+-- .env.example
```

## Backend

The Django backend exposes versioned endpoints under `/api/v1/`:

- `POST /auth/register/`
- `POST /auth/verify-email/`
- `POST /auth/resend-code/`
- `POST /auth/login/`
- `POST /auth/token/refresh/`
- `POST /auth/forgot-password/`
- `POST /auth/reset-password/`
- `POST /auth/google/start/`

Phone numbers are normalized to E.164 and stored as the custom user model primary key. Users remain inactive until email verification succeeds.

## Local Setup

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py test manyumbu10
```

Django uses SQLite by default for local development. Set `DATABASE_URL` to use PostgreSQL.

## Docker

```bash
docker compose up --build
```

The compose file starts PostgreSQL, Redis, and the Django backend.

## Mobile

```bash
cd mobile
npm install
npm run typecheck
npm run start
```

Set `EXPO_PUBLIC_API_URL` when testing against a non-local backend.

## Admin Dashboard

```bash
cd admin-dashboard
npm install
npm run typecheck
npm run dev
```

Set `VITE_API_URL` when needed.

## Security Notes

- Do not commit real secrets.
- Verification and reset codes are hashed in the database.
- Codes expire after 10 minutes and are single-use.
- Login requires verified and active accounts.
- Refresh sessions are tracked server-side and can be revoked.

## Next Phase

Phase 2 should begin only after Phase 1 tests and TypeScript checks pass. Phase 2 covers profiles and social relationships.

## Phase 2 Profile and Relationships

Phase 2 adds authenticated profile APIs, privacy controls, follow/follow-request workflows, blocking, restricting, muting, close friends, profile search, profile media upload/removal, and mobile screens for profile and relationship management. See `docs/phase-2-completion.md` for endpoint details, test results, known limitations, and manual verification commands.
