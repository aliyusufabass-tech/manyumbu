# Phase 1 Architecture

Manyumbu Phase 1 contains Django authentication APIs, an Expo mobile auth flow, an admin login shell, PostgreSQL and Redis Docker services, and environment-driven configuration.

## Authentication Flow

1. The mobile app posts registration data to `/api/v1/auth/register/`.
2. The backend normalizes the phone number to E.164 and stores it as the `User.phone_number` primary key.
3. The user is created inactive and unverified.
4. A six-digit email code is generated securely, stored as a hash, and emailed through the configured backend.
5. `/api/v1/auth/verify-email/` validates unused, unexpired codes and activates the account.
6. Login accepts phone number, email, or username and returns access and refresh tokens only for verified users.
7. Google sign-in currently validates the verified Google identity payload and requires phone/profile completion for new users.

## Phone Primary Key Relationships

All Phase 1 relations point to `settings.AUTH_USER_MODEL`, whose primary key is `phone_number`. Related records include `UserProfile`, `UserSession`, `EmailVerificationCode`, `PasswordResetCode`, and `GoogleAccount`.

## Phase 1 Files

- Django auth models, services, views, URLs, admin, templates, migrations, and tests.
- Mobile Expo Router auth/onboarding screens and API/store modules.
- Admin Vite login shell.
- Dockerfile, `docker-compose.yml`, `.env.example`, requirements, and README.
