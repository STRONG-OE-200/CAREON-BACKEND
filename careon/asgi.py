# careon/asgi.py
import os

# 1) settings 먼저 지정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "careon.settings")

# 2) django 초기화
import django
django.setup()

# 3) 이후에야 django/DRF 의존 모듈 import
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from schedule.ws_auth import JWTAuthMiddleware
from schedule.routing import websocket_urlpatterns

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
