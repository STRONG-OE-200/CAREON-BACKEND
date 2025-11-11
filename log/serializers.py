from datetime import datetime, date
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import LogMetric, CareLog


class LogMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogMetric
        fields = ["id", "room", "label", "sort_order"]
        read_only_fields = ["id", "room"]


class CareLogSerializer(serializers.ModelSerializer):
    metric_label = serializers.CharField(source="metric.label", read_only=True)
    date_only = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CareLog
        fields = [
            "id",
            "room",
            "metric",
            "metric_label",
            "author",
            "content",
            "memo",
            "time_only",
            "date_only",
            "created_at",
        ]
        read_only_fields = ["id", "room", "author", "created_at"]

    def validate_date_only(self, value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str) and "T" in value:
            try:
                return date.fromisoformat(value.split("T")[0])
            except Exception:
                raise serializers.ValidationError("date_only는 YYYY-MM-DD 형식이어야 합니다.")
        return value

    def validate(self, attrs):
        metric_obj = attrs.get("metric")
        if metric_obj is None and getattr(self, "instance", None) is not None:
            metric_obj = self.instance.metric
        if metric_obj is None:
            raise serializers.ValidationError("metric은 필수입니다.")

        room_id = self.context.get("room_id")
        if room_id is None and getattr(self, "instance", None) is not None:
            room_id = self.instance.room_id

        metric = get_object_or_404(LogMetric, pk=getattr(metric_obj, "id", metric_obj))
        if metric.room_id != room_id:
            raise serializers.ValidationError("해당 방의 항목(metric)이 아닙니다.")

        label = (metric.label or "").strip().lower()
        val = (attrs.get("content") or (self.instance.content if getattr(self, "instance", None) else "")).strip()

        if label in ["체온", "temperature"]:
            try:
                float(val)
            except ValueError:
                raise serializers.ValidationError("체온은 숫자(float)여야 합니다. 예: 36.8")
        elif label in ["혈압", "blood_pressure"]:
            import re
            if not re.match(r"^\s*\d{2,3}\s*/\s*\d{2,3}\s*$", val):
                raise serializers.ValidationError("혈압은 '수축기/이완기' 형식이어야 합니다. 예: 120/80")

        return attrs

    def create(self, validated_data):
        room_id = self.context.get("room_id")
        author = self.context.get("user")
        if not validated_data.get("date_only"):
            validated_data["date_only"] = timezone.now().date()
        return CareLog.objects.create(room_id=room_id, author=author, **validated_data)
