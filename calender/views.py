from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from room.models import Room
from user.models import CustomUser as User
from .models import CalendarEvent, CalendarAttachment
from .serializers import (
    CalendarEventSerializer,
    CalendarEventSummarySerializer,
    CalendarEventCreateUpdateSerializer,
)
from .utils import is_room_member

from .models import UploadedFile
from .serializers import UploadedFileSerializer


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
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return None, error_response(
                "ROOM_NOT_FOUND",
                "요청하신 방을 찾을 수 없습니다.",
                status.HTTP_404_NOT_FOUND,
                detail={"location": "path", "value": f"room_id={room_id}"},
            )

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

        params = request.query_params
        date_str = params.get("date")
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")
        include_time_raw = params.get("include_time")

        # date + (start_date/end_date) 같이 오면 400
        if date_str and (start_date_str or end_date_str):
            return error_response(
                "CALENDAR_INVALID_QUERY",
                "단일 날짜(date)와 기간(start_date, end_date)을 동시에 지정할 수 없습니다.",
                status.HTTP_400_BAD_REQUEST,
                detail={
                    "location": "query",
                    "fields": ["date", "start_date", "end_date"],
                },
            )

        # start_date, end_date 둘 중 하나만 온 경우도 에러 처리
        if (start_date_str and not end_date_str) or (end_date_str and not start_date_str):
            return error_response(
                "CALENDAR_INVALID_QUERY",
                "기간 조회 시 start_date와 end_date를 함께 지정해야 합니다.",
                status.HTTP_400_BAD_REQUEST,
                detail={
                    "location": "query",
                    "fields": ["start_date", "end_date"],
                },
            )

        events = CalendarEvent.objects.filter(room=room).order_by("date", "start_at")

        # date or 기간 필터링
        if date_str:
        
            events = events.filter(date=date_str).order_by("date", "start_at")
        elif start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if not start_date or not end_date:
                return error_response(
                    "CALENDAR_INVALID_QUERY",
                    "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요.",
                    status.HTTP_400_BAD_REQUEST,
                    detail={
                        "location": "query",
                        "fields": ["start_date", "end_date"],
                    },
                )
            events = events.filter(date__range=[start_date, end_date]).order_by("date", "start_at")

        serializer = CalendarEventSummarySerializer(events, many=True)
        data = serializer.data

        # include_time 처리 (기본: False → 시간 null 처리)
        include_time = str(include_time_raw).lower() in ("true", "1", "yes")
        if not include_time:
            for item in data:
                item["start_at"] = None
                item["end_at"] = None

        return Response({"room_id": room.id, "events": data})
    
    def post(self, request, room_id):
        room, err = self.get_room(room_id, request.user)
        if err:
            return err

        serializer = CalendarEventCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("CALENDAR_VALIDATION_ERROR", "유효성 검사 실패", 400, serializer.errors)

        v = serializer.validated_data

    # 담당자 처리
        assignee = None
        if "assignee_id" in v and v["assignee_id"]:
            try:
                assignee = User.objects.get(id=v["assignee_id"])
            except User.DoesNotExist:
                return error_response("ASSIGNEE_NOT_FOUND", "담당자 없음", 404)

            if not is_room_member(room, assignee):
                return error_response("ASSIGNEE_NOT_ROOM_MEMBER", "담당자는 방 멤버여야 합니다.", 400)

        repeat_rule = v.get("repeat_rule", "NONE")
        repeat_until = v.get("repeat_until")

        events = []

        # 원본 이벤트 생성
        base_event = CalendarEvent.objects.create(
            room=room,
            date=v["date"],
            title=v["title"],
            start_at=v["start_at"],
            end_at=v["end_at"],
            is_all_day=v.get("is_all_day", False),
            repeat_rule=repeat_rule,
            repeat_until=repeat_until,
            description=v.get("description"),
            assignee=assignee,
        )
        events.append(base_event)

    # attachments 생성
        for att in v.get("attachments", []):
            CalendarAttachment.objects.create(
                event=base_event,
             file_id=att["file_id"],
                type=att["type"],
            )

    # 반복 일정 실제 여러 개 생성
        if repeat_rule != "NONE" and repeat_until:
            current_date = v["date"]

            while True:
                # 반복 규칙에 따라 날짜 증가
                if repeat_rule == "DAILY":
                    current_date += timedelta(days=1)
                elif repeat_rule == "WEEKLY":
                    current_date += timedelta(weeks=1)
                elif repeat_rule == "MONTHLY":
                    current_date += relativedelta(months=1)

                # 반복 종료 조건
                if current_date > repeat_until:
                    break

                # start/end_at도 날짜만 current_date 기반으로 교체
                new_start = v["start_at"].replace(
                    year=current_date.year,
                    month=current_date.month,
                    day=current_date.day,
                )
                new_end = v["end_at"].replace(
                    year=current_date.year,
                    month=current_date.month,
                    day=current_date.day,
                )

            # 이벤트 생성
                ev = CalendarEvent.objects.create(
                    room=room,
                    date=current_date,
                    title=v["title"],
                    start_at=new_start,
                    end_at=new_end,
                    is_all_day=v.get("is_all_day", False),
                    repeat_rule="NONE",   # 복제된 이벤트들은 반복 X
                    repeat_until=None,
                    description=v.get("description"),
                    assignee=assignee,
                )
                events.append(ev)

            # attachments도 복제
                for att in v.get("attachments", []):
                    CalendarAttachment.objects.create(
                        event=ev,
                        file_id=att["file_id"],
                        type=att["type"],
                    )

    # 기존 API 구조상 원본 이벤트만 반환
        return Response(
            CalendarEventSerializer(base_event, context={"request": request}).data,
            status=200,
        )


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
        return Response(
            CalendarEventSerializer(event, context={"request": request}).data
            )

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
        return Response(
            CalendarEventSerializer(event, context={"request": request}).data
            )

    def delete(self, request, event_id):
        event, err = self.get_event(event_id, request.user)
        if err:
            return err
        event.delete()
        return Response({"success": True, "deleted_id": event_id})

class FileUploadAPIView(APIView):

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        uploaded = request.FILES.get("file")
        file_type = request.data.get("type")

        if not uploaded:
            return Response(
                {"detail": "file 필드는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file_type not in [UploadedFile.FileType.IMAGE, UploadedFile.FileType.AUDIO]:
            return Response(
                {"detail": "type 필드는 IMAGE 또는 AUDIO 여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj = UploadedFile.objects.create(file=uploaded, type=file_type)
        serializer = UploadedFileSerializer(obj, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
