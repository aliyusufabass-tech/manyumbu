# Phase 5 Completion - Private Messaging, WebSockets, Attachments, Presence, Sync

Phase 5 builds on Phase 4 commit `2088785` and adds private one-to-one messaging, authenticated WebSockets, message requests, attachments, voice-note support metadata, presence, synchronization, mobile chat screens, and restricted admin moderation for reported private content. Group chats, calls, and video calls were not started.

## Backend Summary

- Added deterministic private conversations with exactly two participants and duplicate-pair prevention.
- Added messaging privacy settings, request states, block/status enforcement, unread/archive/mute/clear state, and participant-specific deletion.
- Added text, attachment, voice-note, location, contact, post-share, reel-share, story-reply, reply, forward, edit, delete, reaction, star, pin, delivery, and read-receipt APIs.
- Added JWT-authenticated Channels WebSockets for chat, presence, and notifications.
- Added Redis-backed Channels configuration when `REDIS_URL` is set, with in-memory channel layer for local/test use.
- Bridged Phase 4 story replies into Phase 5 conversations while preserving `StoryReply` records.
- Added restricted admin report moderation for message and conversation reports only.

## Migration

- `manyumbu10/migrations/0005_conversation_and_more.py`

## New Models

- `Conversation`
- `ConversationParticipant`
- `Message`
- `MessageAttachment`
- `MessageDeletion`
- `MessageReaction`
- `MessageReadReceipt`
- `MessageDeliveryReceipt`
- `MessageStar`
- `MessagePin`
- `ConversationMute`
- `ConversationArchive`
- `ConversationClearState`
- `MessageRequest`
- `MessageReport`
- `ConversationReport`
- `UserPresence`
- `UserDevice`
- `WebSocketSession`

## REST API Endpoints

- `GET /api/v1/conversations/`
- `POST /api/v1/conversations/`
- `GET /api/v1/conversations/<conversation_id>/`
- `PATCH /api/v1/conversations/<conversation_id>/`
- `POST /api/v1/conversations/<conversation_id>/read/`
- `POST /api/v1/conversations/<conversation_id>/unread/`
- `POST /api/v1/conversations/<conversation_id>/archive/`
- `POST /api/v1/conversations/<conversation_id>/unarchive/`
- `POST /api/v1/conversations/<conversation_id>/mute/`
- `DELETE /api/v1/conversations/<conversation_id>/mute/`
- `POST /api/v1/conversations/<conversation_id>/clear/`
- `POST /api/v1/conversations/<conversation_id>/report/`
- `GET /api/v1/conversations/<conversation_id>/messages/`
- `POST /api/v1/conversations/<conversation_id>/messages/`
- `GET /api/v1/conversations/<conversation_id>/search/`
- `GET /api/v1/conversations/<conversation_id>/media/`
- `GET /api/v1/messages/<message_id>/`
- `PATCH /api/v1/messages/<message_id>/`
- `DELETE /api/v1/messages/<message_id>/for-me/`
- `DELETE /api/v1/messages/<message_id>/for-everyone/`
- `POST /api/v1/messages/<message_id>/react/`
- `DELETE /api/v1/messages/<message_id>/react/`
- `POST /api/v1/messages/<message_id>/star/`
- `DELETE /api/v1/messages/<message_id>/star/`
- `POST /api/v1/messages/<message_id>/pin/`
- `DELETE /api/v1/messages/<message_id>/pin/`
- `POST /api/v1/messages/<message_id>/forward/`
- `POST /api/v1/messages/<message_id>/report/`
- `POST /api/v1/messages/<message_id>/delivered/`
- `POST /api/v1/messages/<message_id>/read/`
- `GET /api/v1/message-requests/`
- `POST /api/v1/message-requests/<request_id>/accept/`
- `POST /api/v1/message-requests/<request_id>/reject/`
- `POST /api/v1/message-requests/<request_id>/spam/`
- `DELETE /api/v1/message-requests/<request_id>/delete/`
- `GET /api/v1/messages/sync/`
- `GET /api/v1/conversations/sync/`
- `POST /api/v1/devices/`
- `DELETE /api/v1/devices/`
- `GET /api/v1/admin/message-reports/`
- `POST /api/v1/admin/message-reports/<messages|conversations>/<report_id>/<pending|review|resolve|reject>/`

## WebSocket Routes

- `/ws/chat/<conversation_uuid>/?token=<access-token>`
- `/ws/presence/?token=<access-token>`
- `/ws/notifications/?token=<access-token>`

## WebSocket Events

Client to server:

- `message.send`: persists a text message with optional `client_message_id` and `reply_to_id`.
- `message.delivered`: records delivery when an authenticated participant session/device receives a message.
- `message.read`: updates conversation last-read state and read receipts according to privacy settings.
- `typing.start` / `typing.stop`: broadcasts transient conversation typing state.
- `recording.start` / `recording.stop`: broadcasts transient voice-note recording state.
- `presence.heartbeat`: refreshes online presence without writing every heartbeat as a PostgreSQL history row.

Server to client:

- `connection.ready`
- `message.created`
- `message.delivered`
- `message.read`
- `typing.updated`
- `recording.updated`
- `presence.updated`
- `message.acknowledged`
- `error`

All WebSocket events use `{ "event": string, "version": 1, "data": object, "request_id": optional-string }`.

## Mobile Summary

- Added messaging types, REST API client, WebSocket helper, offline queue helper, and validation tests.
- Added conversation list tab, start-chat screen, chat detail screen, message request screen, and shared-media screen.
- Chat screen includes real backend messages, socket connection state, composer, replies, edits, reactions, stars, pins, delete-for-me, delete-for-everyone, muting/reporting, retry queue, typing indicator, recording indicator, attachment progress state, and shared-media navigation.
- Voice-note recording is represented as explicit record/stop/send-safe state and validation. No microphone file is uploaded without a user send action.

## Admin Dashboard Summary

- Added private-message report API client.
- Added moderation panel for message/conversation reports with status filters and review/resolve/reject actions.
- Admin access remains restricted to reported content/context snapshots and does not expose all private conversations.

## Presence and Synchronization Design

- Presence uses `UserPresence` for coarse state and `WebSocketSession` for active connection tracking.
- Redis is used by Channels when `REDIS_URL` is configured; local tests use the in-memory layer.
- Message/conversation sync endpoints accept cursors and return changed records instead of reloading entire histories.
- Read receipts are symmetrical: when either participant disables read receipts, read timestamps are not exposed to the other user.

## Attachment and Voice-Note Status

- Attachments validate MIME type, extension, size, safe filename, ownership, and malware-scan placeholder state.
- Supported attachment kinds are image, video, document, audio, and voice note.
- Video attachments track processing state but do not claim FFmpeg compression or thumbnail generation when FFmpeg is unavailable.
- Voice notes validate duration, MIME, size, and waveform metadata placeholders.

## Push Notification Status

- Added `UserDevice` registration/removal and notification preference storage.
- In-app notifications are created for private messages.
- External Expo/Firebase push delivery is provider-ready but not enabled because no provider credentials are present.

## Verification Results

Backend:

- `python manage.py check` - passed
- `python manage.py makemigrations --check` - passed
- `python manage.py migrate` - passed
- `python manage.py test -v 1` - passed, 53 tests
- `python -m compileall manyumbu10 myproject` - passed

WebSockets:

- Channels communicator tests passed for authenticated connection, unauthorized token rejection, non-member rejection, and `message.send` persistence/broadcast.

Mobile:

- `npm run typecheck` - passed
- `npm run lint` - passed
- `npm run test` - passed, 13 tests
- `npm audit --audit-level=high` - passed with 0 high and 0 critical vulnerabilities; 10 moderate Expo transitive advisories remain accepted

Admin dashboard:

- `npm run typecheck` - passed
- `npm run lint` - passed
- `npm run test` - passed with no test files found
- `npm audit --audit-level=high` - passed, 0 vulnerabilities

Docker:

- Docker validation remains pending because Docker is not installed or available on this machine.

## Security and Privacy Checks

- JWT authentication is required for REST and WebSocket messaging.
- WebSocket chat connections verify conversation membership and reject invalid/expired tokens.
- Conversation creation enforces account status, blocking, message privacy, and message requests.
- Message responses do not expose phone numbers, tokens, private credentials, or local filesystem paths.
- Read receipts, presence, typing, recording, and message requests respect privacy/request state.
- Duplicate messages are prevented by sender/client-message ID.
- Report moderation records `AdminAuditLog` entries.
- Delete-for-me is participant-specific; delete-for-everyone preserves moderation metadata.

## Known Limitations

- Real push notification delivery is not active until Expo/Firebase credentials and provider settings are configured.
- Attachment upload resume and true secure signed-media URL generation are provider-ready but not fully implemented.
- FFmpeg compression and thumbnail generation remain future work, consistent with the accepted Phase 4 limitation.
- Mobile voice-note UI has record/stop/send-safe state and validation but does not yet depend on a native recording package.
- Docker validation could not be run locally.

## Manual Testing

1. Run `python manage.py migrate`.
2. Start ASGI with Daphne or Django dev server using `myproject.asgi:application`.
3. Start the mobile app with `cd mobile` then `npm run start`.
4. Register and verify two users.
5. Open Chats, start a private chat, send text, reply, edit, react, star, pin, delete for me, and delete for everyone.
6. Test message requests by changing privacy to mutual followers and messaging from a non-mutual user.
7. Test WebSocket reconnect by disabling/re-enabling network and using the retry queue.
8. Send sample image, document, voice-note metadata, location, contact, post-share, reel-share, and story-reply messages.
9. Report a message and conversation, then log in as staff in the admin dashboard to review/resolve/reject the reports.
10. Confirm blocked users cannot start chats, send messages, view presence, or bypass request limits.
