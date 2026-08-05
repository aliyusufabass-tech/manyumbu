# Phase 7 Completion: Calls, Advanced Moderation, Creator Accounts, and Business Accounts

Phase 7 adds authenticated call records, WebRTC signaling architecture, call history, call reporting, call privacy controls, feature restrictions, a unified moderation queue, appeals, creator/business professional accounts, verification-request architecture, professional insights, mobile call/professional/moderation screens, and admin dashboard review tools.

Phase 7 intentionally does not include production deployment, app-store release work, or production TURN/provider credential provisioning.

## Commit Baseline

- Phase 6 commit: `1f4d5e0 Complete Phase 6 group chats and notifications`

## Migration

- `manyumbu10/migrations/0007_groupsettings_allow_member_call_invites_and_more.py`
- Depends on `manyumbu10.0006_grouprole_notification_email_status_and_more`.
- Additive migration only: adds Phase 7 fields, models, indexes, and constraints.
- Does not reset the database, recreate the custom user model, remove Phase 1-6 data, or replace existing APIs.

## Models Created

- Calls: `Call`, `CallParticipant`, `CallDeviceSession`, `CallSignalEvent`, `CallHistory`, `CallReport`, `CallModerationAction`
- Moderation: `ModerationAction`, `UserFeatureRestriction`, `ModerationAppeal`, `AppealAttachment`, `AppealDecision`, `ModerationEvidenceAccess`
- Professional accounts: `ProfessionalAccount`, `CreatorProfile`, `BusinessProfile`, `VerificationRequest`, `VerificationDocument`, `ProfessionalInsightDaily`, `ContentInsight`, `AudienceInsight`, `BusinessContactAction`

## Existing Models Extended

- `UserPrivacySettings`: call privacy fields for who can call, voice/video allowance, call notifications, and unknown caller silencing.
- `GroupSettings`: group call permissions, voice/video toggles, maximum participants, call join approval placeholder, and member invite placeholder.
- `NotificationPreference`: incoming, missed, declined, and group call notification toggles.

## Call REST APIs

- `POST /api/v1/calls/`
- `GET /api/v1/calls/`
- `GET /api/v1/calls/<call_id>/`
- `POST /api/v1/calls/<call_id>/accept/`
- `POST /api/v1/calls/<call_id>/decline/`
- `POST /api/v1/calls/<call_id>/cancel/`
- `POST /api/v1/calls/<call_id>/end/`
- `POST /api/v1/calls/<call_id>/join/`
- `POST /api/v1/calls/<call_id>/leave/`
- `POST /api/v1/calls/<call_id>/timeout/`
- `POST /api/v1/calls/<call_id>/report/`
- `POST /api/v1/calls/<call_id>/config/`
- `DELETE /api/v1/calls/<call_id>/history/`
- `GET/PATCH /api/v1/calls/privacy/`

## Signaling WebSocket

- Route: `/ws/calls/<call_id>/?token=<jwt>`
- Requires JWT authentication and call participant authorization.
- Rejects nonparticipants.
- Client events: `call.ring`, `call.accept`, `call.decline`, `call.cancel`, `call.end`, `call.join`, `call.leave`, `call.offer`, `call.answer`, `call.ice_candidate`, `call.mute_updated`, `call.camera_updated`, `call.heartbeat`
- Server events: `connection.ready`, `call.offer`, `call.answer`, `call.ice_candidate`, `call.accepted`, `call.declined`, `call.cancelled`, `call.ended`, `call.participant_joined`, `call.participant_left`, `call.state_updated`, `error`
- Signal payloads are stored as safe JSON with secret-like keys removed.

## Professional and Verification APIs

- `GET/PATCH/DELETE /api/v1/professional-account/`
- `POST /api/v1/professional-account/creator/`
- `POST /api/v1/professional-account/business/`
- `GET /api/v1/professional-account/insights/`
- `POST /api/v1/verification-requests/`
- `GET /api/v1/verification-requests/`
- `GET /api/v1/verification-requests/<id>/`

## Moderation and Appeal APIs

- `GET /api/v1/moderation/actions/`
- `GET /api/v1/moderation/restrictions/`
- `POST /api/v1/moderation/actions/<id>/appeal/`
- `GET /api/v1/moderation/appeals/`

## Admin APIs

- `GET /api/v1/admin/moderation/queue/`
- `GET /api/v1/admin/call-reports/`
- `GET /api/v1/admin/appeals/`
- `POST /api/v1/admin/appeals/<id>/<decision>/`
- `GET /api/v1/admin/verification-requests/`
- `POST /api/v1/admin/verification-requests/<id>/approve/`
- `POST /api/v1/admin/verification-requests/<id>/reject/`
- `GET /api/v1/admin/professional-accounts/`
- `POST /api/v1/admin/professional-accounts/<username>/<action>/`
- `POST /api/v1/admin/users/<username>/restrictions/`
- `DELETE /api/v1/admin/users/<username>/restrictions/<id>/`

## Mobile Implementation

- Call API and signaling client abstraction.
- Incoming, outgoing, active, ended, call history, and call privacy screens.
- Active call controls for mute, camera toggle, speaker state, end, decline, report, and connection state display.
- WebRTC capability state that accurately reports when a custom Expo development build is required.
- Creator, business, professional dashboard, verification request, restrictions, and appeal screens.
- Android and iOS native permission declarations for camera, microphone, Bluetooth, notifications, foreground service, audio, and VoIP architecture.

## Admin Dashboard Implementation

- Unified moderation queue.
- Call reports.
- Appeals with approve/reject actions.
- Verification request review with approve/reject actions.
- Professional account review and removal actions.
- User feature restriction creation.

## STUN/TURN Configuration

Environment variables:

- `MANYUMBU_STUN_SERVERS`
- `MANYUMBU_TURN_SERVER`
- `MANYUMBU_TURN_USERNAME`
- `MANYUMBU_TURN_PASSWORD`
- `MANYUMBU_CALL_PROVIDER`
- `MANYUMBU_CALL_TIMEOUT_SECONDS`

Default STUN is `stun:stun.l.google.com:19302`. TURN is not configured by default. TURN secrets and provider credentials must not be committed.

## Native WebRTC Status

- Signaling backend is functional.
- Real media transport requires a React Native WebRTC native module and a custom Expo development build or EAS build.
- Expo Go is not sufficient for native WebRTC media capture/transport.
- TURN infrastructure is required before claiming production-ready call connectivity.
- Optional provider fallback is represented by configuration, not hard-coded credentials.

## Verification Commands

Backend:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python -m compileall manyumbu10 myproject
python manage.py test manyumbu10 -v 1
```

Mobile:

```bash
npm run typecheck
npm run lint
npm run test
npm audit --audit-level=high
```

Admin:

```bash
npm run typecheck
npm run lint
npm run test
npm audit --audit-level=high
```

Docker:

```bash
docker compose config
```

## Known Limitations

- Docker is unavailable in the current environment.
- TURN is not configured by default, so call connectivity is signaling-ready, not production media-ready.
- Native WebRTC media requires a custom Expo development build/EAS build and native module installation.
- Provider fallback for Agora/Twilio is an abstraction/configuration point only; no provider SDK or credentials are committed.
- Calls do not store raw audio/video and do not implement hidden recording.
- Professional insights are basic aggregate placeholders and may be delayed or approximate.
- Verification-document secure storage and retention policy are modeled; production object storage policy must be configured later.
- Mobile tests cover meaningful validation/state logic; full device media tests require native build infrastructure.
