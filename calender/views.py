from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from room.models import Room
from user.models import CustomUser as User
from .models import CalendarEvent, CalendarAttachment
from .serializers import (
    CalendarEventSerializer,
    CalendarEventSummarySerializer,
    CalendarEventCreateUpdateSerializer,
)
from .utils import is_room_member


def error_response(code, msg, status_code, detail=None):
    return Response(
        {
            "success": False,
            "error_code": code,
            "message": msg,
            "detail": detail or {},
        },
        status=status_code,
    )


class RoomEventListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_room(self, room_id, user):
        room = get_object_or_404(Room, id=room_id)
        if not is_room_member(room, user):
            return None, error_response(
                "ROOM_MEMBER_ONLY",
                "해당 방 멤버만 일정에 접근할 수 있습니다.",
                status.HTTP_403_FORBIDDEN,
            )
        return room, None

    def get(self, request, room_id):
        room, err = self.get_room(room_id, request.user)
        if err:
            return err

        date = request.query_params.get("date")
        events = CalendarEvent.objects.filter(room=room)
        if date:
            events = events.filter(date=date)

        serializer = CalendarEventSummarySerializer(events, many=True)
        return Response({"room_id": room.id, "events": serializer.data})
    def post(self, request, room_id):
        room, err = self.get_room(room_id, request.user)
        if err:
            return err

        serializer = CalendarEventCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("CALENDAR_VALIDATION_ERROR", "유효성 검사 실패", 400, serializer.errors)

        v = serializer.validated_data

        assignee = None
        if "assignee_id" in v and v["assignee_id"]:
            try:
                assignee = User.objects.get(id=v["assignee_id"])
            except User.DoesNotExist:
                return error_response("ASSIGNEE_NOT_FOUND", "담당자 없음", 404)

            if not is_room_member(room, assignee):
                return error_response("ASSIGNEE_NOT_ROOM_MEMBER", "담당자는 방 멤버여야 합니다.", 400)

        event = CalendarEvent.objects.create(
            room=room,
            date=v["date"],
            title=v["title"],
            start_at=v["start_at"],
            end_at=v["end_at"],
            is_all_day=v.get("is_all_day", False),
            repeat_rule=v.get("repeat_rule", "NONE"),
            repeat_until=v.get("repeat_until"),
            description=v.get("description"),
            assignee=assignee,
        )

        # attachments
        for att in v.get("attachments", []):
            CalendarAttachment.objects.create(
                event=event,
                file_id=att["file_id"],
                type=att["type"],
            )

        return Response(CalendarEventSerializer(event).data, status=200)


class EventDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_event(self, event_id, user):
        event = get_object_or_404(CalendarEvent, id=event_id)
        if not is_room_member(event.room, user):
            return None, error_response("ROOM_MEMBER_ONLY", "방 멤버만 접근 가능", 403)
        return event, None

    def get(self, request, event_id):
        event, err = self.get_event(event_id, request.user)
        if err:
            return err
        return Response(CalendarEventSerializer(event).data)

    def patch(self, request, event_id):
        event, err = self.get_event(event_id, request.user)
        if err:
            return err

        serializer = CalendarEventCreateUpdateSerializer(instance=event, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("CALENDAR_VALIDATION_ERROR", "유효성 검사 실패", 400, serializer.errors)

        v = serializer.validated_data
        for field, value in v.items():
            if field == "assignee_id":
                if value is None:
                    event.assignee = None
                else:
                    try:
                        assignee = User.objects.get(id=value)
                    except User.DoesNotExist:
                        return error_response("ASSIGNEE_NOT_FOUND", "담당자 없음", 404)
                    if not is_room_member(event.room, assignee):
                        return error_response("ASSIGNEE_NOT_ROOM_MEMBER", "담당자는 방 멤버만 가능", 400)
                    event.assignee = assignee
            else:
                setattr(event, field, value)

        event.save()
        return Response(CalendarEventSerializer(event).data)

    def delete(self, request, event_id):
        event, err = self.get_event(event_id, request.user)
        if err:
            return err
        event.delete()
        return Response({"success": True, "deleted_id": event_id})
