from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

@database_sync_to_async
def _get_user_from_token(token: str | None):
    if not token:
        return AnonymousUser()
    try:
        payload = AccessToken(token)
        uid = payload.get("user_id")
        if not uid:
            return AnonymousUser()
        user = User.objects.filter(id=uid, is_active=True).first()
        return user or AnonymousUser()
    except Exception:
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]

        
        scope["user"] = await _get_user_from_token(token)

        return await self.app(scope, receive, send)
