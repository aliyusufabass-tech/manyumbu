from django.urls import path

from .consumers import CallSignalingConsumer, ChatConsumer, GroupConsumer, NotificationsConsumer, PresenceConsumer

websocket_urlpatterns = [
    path("ws/chat/<uuid:conversation_id>/", ChatConsumer.as_asgi()),
    path("ws/groups/<uuid:group_id>/", GroupConsumer.as_asgi()),
    path("ws/calls/<uuid:call_id>/", CallSignalingConsumer.as_asgi()),
    path("ws/presence/", PresenceConsumer.as_asgi()),
    path("ws/notifications/", NotificationsConsumer.as_asgi()),
]
