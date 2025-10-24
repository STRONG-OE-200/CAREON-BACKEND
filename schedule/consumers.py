import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ScheduleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"schedule_room_{self.room_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        
        try:
            payload = json.loads(text_data or "{}")
        except Exception:
            payload = {"message": text_data}
        await self.channel_layer.group_send(
            self.group_name, {"type": "ws.broadcast", "payload": payload}
        )

    async def ws_broadcast(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
