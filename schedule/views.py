from django.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WeekSchedule, NeededCell
from .serializers import (
    WeekScheduleSerializer,
    NeededBulkReplaceSerializer,
    NeededBulkResultSerializer,
)
from room.permissions import IsRoomOwner, IsRoomMemberOrOwner

class WeekScheduleCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WeekScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = serializer.validated_data["room"]  # <-- 여기! room_id가 아니라 room
        if not IsRoomOwner().has_object_permission(request, self, room):
            return Response(
                {"detail": "방장에게만 허용된 작업입니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            instance = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "이미 동일한 주차 스케줄이 존재합니다."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(WeekScheduleSerializer(instance).data, status=status.HTTP_201_CREATED)


class NeededBulkView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, week_id: int):
        week = get_object_or_404(WeekSchedule, id=week_id)

        # 멤버 또는 방장만 조회 가능
        if not IsRoomMemberOrOwner().has_object_permission(request, self, week.room):
            return Response(
                {"detail": "해당 방의 멤버만 조회/수정할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = NeededCell.objects.filter(week=week).values("day", "hour").order_by("day", "hour")
        return Response(
            {
                "week_schedule_id": week.id,
                "cells": list(qs),
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request, week_id: int):
        week = get_object_or_404(WeekSchedule, id=week_id)

        # 방장만 수정 가능
        if not IsRoomOwner().has_object_permission(request, self, week.room):
            return Response(
                {"detail": "방장에게만 허용된 작업입니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if week.is_finalized:
            return Response(
                {"detail": "이미 확정된 스케줄은 수정할 수 없습니다."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = NeededBulkReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cells = serializer.validated_data.get("cells", [])

        # 전체 교체(Replace All): 기존 row 삭제 후 새로 삽입
        with transaction.atomic():
            NeededCell.objects.filter(week=week).delete()

            bulk = [
                NeededCell(
                    week=week,
                    day=item["day"],
                    hour=item["hour"],
                    created_by=request.user,
                )
                for item in cells
            ]
            if bulk:
                NeededCell.objects.bulk_create(bulk, ignore_conflicts=False)

        result = NeededBulkResultSerializer(
            {
                "week_schedule_id": week.id,
                "updated_cells": len(cells),
                "updated_at": timezone.now(),
            }
        ).data
        return Response(result, status=status.HTTP_200_OK)