# WebSockets

Routes:

- `/ws/chat/<conversation_id>/?token=<access>`
- `/ws/groups/<group_id>/?token=<access>`
- `/ws/calls/<call_id>/?token=<access>&device=<device_id>`

Events already covered by Phase 5-7 include message creation/edit/delete/reaction/read/delivery/pin, group message events, presence/typing, and call offer/answer/ICE/mute/camera/screen/share/end style signaling. Payload metadata is sanitized before call signaling is persisted.
