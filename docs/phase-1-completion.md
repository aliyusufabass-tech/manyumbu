# Phase 1 Completion

## Completed Features

- Django foundation with environment-based settings.
- Custom user model with `phone_number` as the primary key.
- E.164 phone-number normalization.
- Registration with full name, username, phone number, email, date of birth, password confirmation, terms, and privacy acceptance.
- Email verification using hashed six-digit codes, 10-minute expiry, single-use records, resend delay, and failed-attempt tracking.
- Login by phone number, email, or username.
- Access and refresh token issuing with server-side refresh sessions.
- Password recovery code architecture.
- Google sign-in start architecture requiring verified Google email and phone-number completion for new users.
- Django admin model registration.
- Expo mobile onboarding, registration, verification, login, forgot-password, and home navigation shell.
- Vite admin login shell.
- Dockerfile, Docker Compose, `.env.example`, README, and Phase 1 architecture notes.

## Test Results

- `python manage.py check`: passed.
- `python manage.py migrate`: passed.
- `python manage.py test manyumbu10 -v 1`: 10 tests passed.
- `python -m compileall manyumbu10 myproject`: passed.
- `npm run typecheck` in `mobile`: passed.
- `npm run typecheck` in `admin-dashboard`: passed.
- `npm audit --audit-level=high` in `admin-dashboard`: zero vulnerabilities.

## API Endpoints

- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/verify-email/`
- `POST /api/v1/auth/resend-code/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/token/refresh/`
- `POST /api/v1/auth/forgot-password/`
- `POST /api/v1/auth/reset-password/`
- `POST /api/v1/auth/google/start/`

## Environment Variables

See `.env.example` for Django, PostgreSQL, Redis, SMTP, Google, Cloudinary, JWT lifetime, mobile API, WebSocket, Firebase, and Agora placeholders.

## Known Limitations

- Simple local HMAC token architecture is in place for Phase 1. A future production hardening pass should replace or wrap this with Simple JWT rotation/blacklisting once dependencies and policy are finalized.
- Google sign-in verifies the architecture contract and pending state, but provider token verification is still pending external credential setup.
- Swagger/OpenAPI wiring is not yet installed.

## Docker Validation Status

Docker files are present, but `docker compose config` could not be run because Docker is not installed or not available on PATH on this machine. When Docker is available, run:

```bash
docker compose config
docker compose up --build
```

## Mobile Dependency Advisory Status

Mobile dependencies install and TypeScript passes. `npm audit` reports Expo transitive advisories involving `postcss` and `uuid`. `npm audit fix` cannot resolve them without `--force`, which would upgrade Expo to a breaking major version. Do not run `npm audit fix --force`; upgrade Expo later through a controlled compatibility-tested process.
