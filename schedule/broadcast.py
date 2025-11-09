from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_to_room(room_id: int, payload: dict):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"room_{room_id}_schedules",
        {"type": "schedule.update", "payload": payload},
    )