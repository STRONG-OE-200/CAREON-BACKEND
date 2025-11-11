from django.shortcuts import render

# Create your views here.

from django.db import models,IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import status, permissions

from rest_framework.response import Response
from datetime import datetime, timedelta
from django.utils import timezone
from zoneinfo import ZoneInfo
from .models import LogMetric, CareLog
from .serializers import LogMetricSerializer, CareLogSerializer
from room.models import Room
from room.permissions import IsRoomMemberOrOwner


class RoomMetricsListCreateView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsRoomMemberOrOwner]

    def get_object(self, room_id):
        room = get_object_or_404(Room, pk=room_id)
        self.check_object_permissions(self.request, room)
        return room


    def get(self, request, room_id):
        room = self.get_object(room_id)
        defaults = ["체온", "혈압"]
        for label in defaults:
            LogMetric.objects.get_or_create(room=room, label=label)

        qs = room.log_metrics.all().order_by("sort_order", "id")
        data = LogMetricSerializer(qs, many=True).data
        return Response({"items": data}, status=status.HTTP_200_OK)


    def post(self, request, room_id):
        room = self.get_object(room_id)
        serializer = LogMetricSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                metric = serializer.save(room=room)
        except IntegrityError:
            return Response(
                {"detail": "같은 라벨의 항목이 이미 존재합니다."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(LogMetricSerializer(metric).data, status=status.HTTP_201_CREATED)


class RoomMetricDetailView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsRoomMemberOrOwner]

    def get_object(self, room_id, metric_id):
        metric = get_object_or_404(LogMetric, pk=metric_id)
        if metric.room_id != int(room_id):
            return Response({"detail": "잘못된 경로입니다."}, status=status.HTTP_400_BAD_REQUEST)
        room = metric.room
        self.check_object_permissions(self.request, room)
        return metric

    def patch(self, request, room_id, metric_id):
        metric = self.get_object(room_id, metric_id)
        serializer = LogMetricSerializer(metric, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                updated = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "같은 라벨의 항목이 이미 존재합니다."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(LogMetricSerializer(updated).data, status=status.HTTP_200_OK)

    def delete(self, request, room_id, metric_id):
        metric = self.get_object(room_id, metric_id)
        metric.delete()
        return Response({"detail": "deleted"}, status=status.HTTP_200_OK)


class RoomLogsListCreateView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsRoomMemberOrOwner]

    def _get_room(self, room_id):
        room = get_object_or_404(Room, pk=room_id)
        self.check_object_permissions(self.request, room)
        return room

    def get(self, request, room_id: int):
        room = self._get_room(room_id)

       
        date_str = request.query_params.get("date")
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"detail": "date 형식이 올바르지 않습니다. (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST
            )
        else:
            date_obj = timezone.now().date()

        metric_id = request.query_params.get("metric_id")
        qs = CareLog.objects.filter(
            room_id=room.id,
            date_only=date_obj,
        )
        if metric_id:
            qs = qs.filter(metric_id=metric_id)

        qs = qs.select_related("metric", "author").order_by("time_only", "id")
        data = CareLogSerializer(qs, many=True).data
        return Response({"items": data}, status=status.HTTP_200_OK)

    def post(self, request, room_id: int):
        room = self._get_room(room_id)

        ser = CareLogSerializer(
            data=request.data,
            context={"room_id": room.id, "user": request.user},
        )
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            obj = ser.save()
        return Response(CareLogSerializer(obj).data, status=status.HTTP_201_CREATED)


class LogDetailView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsRoomMemberOrOwner]

    def _get_obj(self, log_id: int) -> CareLog:
        obj = get_object_or_404(CareLog.objects.select_related("room"), pk=log_id)
    
        self.check_object_permissions(self.request, obj.room)
        return obj

    def get(self, request, log_id: int):
        obj = self._get_obj(log_id)
        data = CareLogSerializer(obj).data
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, log_id: int):
        obj = self._get_obj(log_id)

        data = request.data.copy()
        data.setdefault("metric", obj.metric_id)

        ser = CareLogSerializer(obj, data=data, partial=True, context={"room_id": obj.room_id, "user": request.user},)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            obj = ser.save()
        return Response(CareLogSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, log_id: int):
        obj = self._get_obj(log_id)
        obj.delete()
        return Response({"detail": "deleted"}, status=status.HTTP_200_OK)


class RoomChartsView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsRoomMemberOrOwner]

    LABELS_TEMP = {"체온", "temperature"}
    LABELS_BP = {"혈압", "blood_pressure"}
    TZ = ZoneInfo("Asia/Seoul")

    def _check_room(self, request, room_id: int) -> Room:
        room = get_object_or_404(Room, pk=room_id)
        
        self.check_object_permissions(request, room)
        return room

    def _combine_dt(self, d, t):
        return datetime.combine(d, t, tzinfo=self.TZ)

    def _parse_bp(self, s: str):
        # "120/80" → (120, 80)
        s = s.strip()
        try:
            a, b = s.split("/")
            return int(a.strip()), int(b.strip())
        except Exception:
            return None, None

    def get(self, request, room_id: int):
        room = self._check_room(request, room_id)

       
        today = timezone.now().date()
        start_date = today - timedelta(days=6)

        labels = self.LABELS_TEMP | self.LABELS_BP  # set 합치기
        qs = (
            CareLog.objects
            .select_related("metric")
            .filter(
                room_id=room.id,
                date_only__range=[start_date, today],
                metric__label__in=labels,
            )
            .order_by("date_only", "time_only", "id")
        )

        
        temp_points = []
        temp_values = []

        bp_points = []
        bp_sys_vals = []
        bp_dia_vals = []

        for log in qs:
            label = (log.metric.label or "").strip().lower()

            
            t_iso = self._combine_dt(log.date_only, log.time_only).isoformat()

            if label in self.LABELS_TEMP:
                try:
                    val = float(log.content.strip())
                except Exception:
                    
                    continue
                temp_points.append({"t": t_iso, "value": val})
                temp_values.append(val)

            elif label in self.LABELS_BP:
                sys_v, dia_v = self._parse_bp(log.content)
                if sys_v is None or dia_v is None:
                    continue
                bp_points.append({"t": t_iso, "systolic": sys_v, "diastolic": dia_v})
                bp_sys_vals.append(sys_v)
                bp_dia_vals.append(dia_v)

    
        def agg_num(values):
            if not values:
                return None
            return {
                "avg": round(sum(values) / len(values), 2),
                "min": min(values),
                "max": max(values),
            }

        def agg_bp(sys_vals, dia_vals):
            if not sys_vals or not dia_vals:
                return None
            def pack(vs):
                return {
                    "avg": round(sum(vs) / len(vs), 2),
                    "min": min(vs),
                    "max": max(vs),
                }
            return {
                "avg": {"systolic": pack(sys_vals)["avg"], "diastolic": pack(dia_vals)["avg"]},
                "min": {"systolic": pack(sys_vals)["min"], "diastolic": pack(dia_vals)["min"]},
                "max": {"systolic": pack(sys_vals)["max"], "diastolic": pack(dia_vals)["max"]},
            }

        temp_agg_raw = agg_num(temp_values)
        bp_agg_raw = agg_bp(bp_sys_vals, bp_dia_vals)

        resp = {
            "range": {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": today.strftime("%Y-%m-%d"),
                "timezone": "Asia/Seoul",
            },
            "temperature": {
                "unit": "°C",
                "agg": temp_agg_raw, 
                "points": temp_points,
            },
            "blood_pressure": {
                "unit": "mmHg",
                "agg": bp_agg_raw,
                "points": bp_points,
            },
        }
        return Response(resp, status=status.HTTP_200_OK)