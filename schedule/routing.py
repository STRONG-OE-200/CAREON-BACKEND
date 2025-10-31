from django.urls import re_path
from .consumers import ScheduleConsumer

websocket_urlpatterns = [
    re_path(r"^ws/schedule/(?P<room_id>\d+)/$", ScheduleConsumer.as_asgi()),
]
