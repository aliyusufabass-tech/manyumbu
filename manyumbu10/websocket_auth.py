from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

from .services import decode_token


@database_sync_to_async
def user_for_token(token):
    try:
        payload = decode_token(token, expected_type="access")
        return get_user_model().objects.get(phone_number=payload["sub"], is_active=True, is_email_verified=True)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if not token:
            headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
            auth = headers.get("authorization", "")
            if auth.startswith("Bearer "):
                token = auth.removeprefix("Bearer ").strip()
        scope["user"] = await user_for_token(token or "")
        return await self.app(scope, receive, send)
