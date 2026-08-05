# Phase 6 Completion: Group Chats and Notifications

Phase 6 adds group conversations, group roles and moderation, invitations, join requests, group messaging, in-app notifications, push-delivery queue records, mobile group screens, and admin group moderation tools. Phase 6 does not include voice/video calls, monetization, creator tools, business tools, or Phase 7 features.

## Commit Baseline

- Phase 4 commit: `2088785 Complete Phase 4 stories and reels`
- Phase 5 commit: `2f5c057 Complete Phase 5 private messaging and WebSockets`

## Migration

- `manyumbu10/migrations/0006_grouprole_notification_email_status_and_more.py`
- Depends on `manyumbu10.0005_conversation_and_more`.
- The migration adds Phase 6 tables, notification metadata fields, indexes, and uniqueness constraints.
- It does not reset the database, recreate the custom user model, remove Phase 1-5 tables, or delete existing data.
- `Notification.uuid` is indexed rather than unique so existing rows can be migrated safely with Django's generated default behavior.

## Models Created

- `Group`, `GroupRole`, `GroupSettings`, `GroupMember`
- `GroupInvitation`, `GroupJoinRequest`, `GroupBan`, `GroupRestriction`
- `GroupMessage`, `GroupMessageAttachment`, `GroupMessageReaction`, `GroupMessageReadReceipt`, `GroupMessageDeliveryReceipt`, `GroupMessageDeletion`, `GroupMessageStar`, `GroupMessagePin`
- `GroupMute`, `GroupArchive`, `GroupClearState`
- `GroupReport`, `GroupMessageReport`, `GroupAuditLog`
- `NotificationPreference`, `NotificationDelivery`, `PushNotificationDelivery`, `NotificationBatch`, `AdminAnnouncement`

## Notification Model Extensions

The existing `Notification` model now supports UUID addressing, object references, safe payloads, read/seen timestamps, push/email status, priority, and grouping keys while keeping the earlier actor/post/comment/message relationships intact.

## REST API Endpoints

### Groups

- `GET /api/v1/groups/`
- `POST /api/v1/groups/`
- `GET /api/v1/groups/<group_id>/`
- `PATCH /api/v1/groups/<group_id>/`
- `DELETE /api/v1/groups/<group_id>/`
- `GET /api/v1/groups/<group_id>/members/`
- `POST /api/v1/groups/<group_id>/members/`
- `DELETE /api/v1/groups/<group_id>/members/<user_identifier>/`
- `POST /api/v1/groups/<group_id>/<action>/` for `leave`, `transfer-ownership`, `roles`, `ban`, `restrict`, `report`, `mute`, `archive`, `unarchive`, `clear`
- `DELETE /api/v1/groups/<group_id>/mute/`

### Group Messages

- `GET /api/v1/groups/<group_id>/messages/`
- `POST /api/v1/groups/<group_id>/messages/`
- `GET /api/v1/groups/<group_id>/search/`
- `GET /api/v1/groups/<group_id>/media/`
- `PATCH /api/v1/group-messages/<message_id>/`
- `POST /api/v1/group-messages/<message_id>/<action>/` for `react`, `pin`, `star`, `read`, `delivered`, `report`, `forward`
- `DELETE /api/v1/group-messages/<message_id>/<action>/` for `for-me`, `for-everyone`, `react`, `pin`, `star`

### Invitations and Join Requests

- `GET /api/v1/groups/<group_id>/invitations/`
- `POST /api/v1/groups/<group_id>/invitations/`
- `DELETE /api/v1/groups/<group_id>/invitations/<invitation_id>/`
- `POST /api/v1/group-invitations/<token>/join/`
- `GET /api/v1/groups/<group_id>/join-requests/`
- `POST /api/v1/groups/<group_id>/join-requests/`
- `POST /api/v1/groups/<group_id>/join-requests/<request_id>/<action>/` for `approve` and `reject`

### Notifications

- `GET /api/v1/notifications/`
- `POST /api/v1/notifications/read-all/`
- `POST /api/v1/notifications/<notification_id>/read/`
- `POST /api/v1/notifications/<notification_id>/seen/`
- `DELETE /api/v1/notifications/<notification_id>/delete/`
- `GET /api/v1/notification-preferences/`
- `PATCH /api/v1/notification-preferences/`

### Admin

- `GET /api/v1/admin/groups/`
- `GET /api/v1/admin/groups/?kind=group-reports`
- `GET /api/v1/admin/groups/?kind=group-message-reports`
- `POST /api/v1/admin/groups/<group_id>/<action>/` for `suspend`, `restore`, `remove`, `warn-owner`
- `POST /api/v1/admin/announcements/announcement/`

## WebSocket Routes and Events

- `ws://<host>/ws/groups/<group_id>/?token=<jwt>`
- Requires authenticated active group membership and rejects non-members.
- Client events: `group.message.send`, `group.typing.start`, `group.typing.stop`, `group.recording.start`, `group.recording.stop`, `group.presence.heartbeat`
- Server events: `connection.ready`, `group.message.created`, `group.typing.updated`, `group.recording.updated`, `group.message.acknowledged`, `error`

Existing Phase 5 WebSocket routes remain unchanged:

- `/ws/chat/<conversation_id>/`
- `/ws/presence/`
- `/ws/notifications/`

## Mobile Implementation

- Added group types, API client, validation, and WebSocket helper.
- Added group list, create group, group chat, group info/member management, invite/join request controls, and notification preferences screens.
- Added navigation links from the existing Chats screen to Groups and Notifications.
- Added validation tests for group names, descriptions, member parsing, group message requirements, and moderator role detection.

## Admin Implementation

- Added `admin-dashboard/src/api/groups.ts`.
- Added a Groups moderation panel to the admin dashboard with group search, status filters, suspend/restore/remove/warn actions, group report queues, group-message report queues, and announcement sending.

## Verification Commands

Run from the repository root unless noted:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python -m compileall manyumbu10 myproject
python manage.py test manyumbu10 -v 1
```

Run from `mobile/`:

```bash
npm run typecheck
npm run lint
npm run test
npm audit --audit-level=high
```

Run from `admin-dashboard/`:

```bash
npm run typecheck
npm run lint
npm run test
npm audit --audit-level=high
```

Docker validation should be run with Docker Desktop available:

```bash
docker compose config
docker compose up --build
```

## Known Limitations

- Push notifications are queued as `PushNotificationDelivery` records with provider status `not_configured`; no external push provider credentials are committed.
- Email notification fanout is modeled with delivery status fields but not connected to a production email notification pipeline beyond existing auth email support.
- Group media processing, malware scanning, and video transcoding are represented by status fields and validation hooks; asynchronous workers are not included in this phase.
- Admin report status transitions for group reports are currently list/triage oriented; Phase 6 implements group-level moderation actions and announcement sending.
- Voice/video calls, monetization, business tools, and creator analytics are intentionally excluded.
