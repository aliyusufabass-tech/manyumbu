import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

from django.core.asgi import get_asgi_application

# Hii lazima iitwe kabla ya ku-import routing/consumers
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from manyumbu10.websocket_auth import JWTAuthMiddleware
from manyumbu10.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
