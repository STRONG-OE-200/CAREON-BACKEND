# schedule/routing.py
from django.urls import re_path
from .consumers import ScheduleRoomConsumer

websocket_urlpatterns = [
    
    re_path(r"^ws/rooms/(?P<room_id>\d+)/schedules/$", ScheduleRoomConsumer.as_asgi()),
]
