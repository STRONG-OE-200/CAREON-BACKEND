# schedule/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from room.models import Room, RoomMembership

class ScheduleRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        user = self.scope.get("user")
        allowed = await self._is_member_or_owner(self.room_id, getattr(user, "id", None))
        if not allowed:
            await self.close(code=4403)  # Forbidden
            return

        self.group_name = f"room_{self.room_id}_schedules"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # 필요하면 클라이언트→서버 이벤트 처리
        pass

    async def schedule_update(self, event):
        # DRF에서 group_send로 보낸 payload를 전달
        await self.send(text_data=json.dumps(event["payload"], ensure_ascii=False))

    @database_sync_to_async
    def _is_member_or_owner(self, room_id, user_id):
        if not user_id:
            return False
        try:
            room = Room.objects.only("id", "owner_id").get(id=room_id)
        except Room.DoesNotExist:
            return False
        if room.owner_id == user_id:
            return True
        return RoomMembership.objects.filter(room_id=room_id, user_id=user_id).exists()
