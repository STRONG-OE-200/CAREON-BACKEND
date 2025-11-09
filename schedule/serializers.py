from datetime import timedelta, date
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
import re
from .models import Schedule
from room.models import Room



class ScheduleCreateSerializer(serializers.Serializer):
    room_id = serializers.IntegerField(required=True)
    start_date = serializers.DateField(
        input_formats=["%Y-%m-%d"],
        error_messages={
            "invalid": _("start_date는 YYYY-MM-DD 형식이어야 합니다."),
            "null": _("start_date는 필수입니다."),
            "required": _("start_date는 필수입니다."),
        },
    )

    def validate_room_id(self, value):
        if not Room.objects.filter(id=value).exists():
            raise serializers.ValidationError("해당 방을 찾을 수 없습니다.")
        return value

    def validate_start_date(self, value):
        # 반드시 일요일이어야 함
        if value.weekday() != 6:
            raise serializers.ValidationError(
                "start_date는 **일요일(YYYY-MM-DD)** 이어야 합니다."
            )
        return value

    def create(self, validated_data):
        start = validated_data["start_date"]
        end = start + timedelta(days=6)
        schedule = Schedule.objects.create(
            room_id=validated_data["room_id"],
            start_date=start,
            end_date=end,
            created_by=self.context["request"].user,
        )
        return schedule


class ScheduleResponseSerializer(serializers.ModelSerializer):
    schedule_id = serializers.IntegerField(source="id")
    room_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Schedule
        fields = (
            "schedule_id",
            "room_id",
            "start_date",
            "end_date",
            "status",
            "created_by",
        )



class NeededSlotItemSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    hour = serializers.IntegerField(min_value=0, max_value=23)


class ScheduleNeededSubmitSerializer(serializers.Serializer):
    slots = serializers.ListField(
        child=NeededSlotItemSerializer(),
        allow_empty=False,
        error_messages={
            "required": "slots는 필수입니다.",
            "null": "slots는 null일 수 없습니다.",
            "empty": "slots는 비어 있을 수 없습니다.",
        },
    )

    def validate_slots(self, value):
        seen = set()
        for item in value:
            key = (item["day"], item["hour"])
            if key in seen:
                raise serializers.ValidationError(
                    f"중복된 칸이 포함되어 있습니다: day={item['day']}, hour={item['hour']}"
                )
            seen.add(key)
        if len(value) > 168:
            raise serializers.ValidationError("slots 항목이 168개를 초과할 수 없습니다.")
        return value


ISO_WEEK_RE = re.compile(r'^(?P<year>\d{4})-W(?P<week>\d{1,2})$')

class ScheduleQuerySerializer(serializers.Serializer):
    room_id = serializers.IntegerField(
        required=True,
        error_messages={
            "required": "room_id is required",
            "invalid": "room_id must be an integer",
        },
    )

    schedule_id = serializers.IntegerField(required=False)

    week = serializers.CharField(required=False, allow_blank=False)
    only = serializers.ChoiceField(
        required=False,
        choices=("needed", "availability", "confirmed"),
        error_messages={"invalid_choice": "only must be one of: needed, availability, confirmed"},
    )
    expand = serializers.ChoiceField(
        required=False,
        choices=("meta",),
        error_messages={"invalid_choice": "expand must be 'meta' if provided"},
    )

    def validate_week(self, value: str) -> str:

        m = ISO_WEEK_RE.match(value)
        if m:
            y = int(m.group('year'))
            w = int(m.group('week'))
            if not (1 <= w <= 53):
                raise serializers.ValidationError("ISO week must be between 1 and 53.")
            return f"{y}-W{w:02d}"

        # ISO date (YYYY-MM-DD)
        try:
            date.fromisoformat(value)
            return value
        except Exception:
            raise serializers.ValidationError(
                "week must be 'YYYY-Www' (ISO week, e.g. 2025-W45) or 'YYYY-MM-DD'."
            )

    def validate(self, attrs):
        week = attrs.get("week")
        schedule_id = attrs.get("schedule_id")
        if week and schedule_id:
            raise serializers.ValidationError(
                {"non_field_errors": ["Use either 'week' or 'schedule_id' (not both)."]}
            )
        return attrs



def compute_sunday_range_from_week(week: str | None) -> tuple[date, date]:
    """week 파라미터(ISO week 또는 ISO date) → (sunday, saturday)"""
    today = date.today()
    if not week:
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        return (sunday, sunday + timedelta(days=6))

    if ISO_WEEK_RE.match(week):
        y, w = week.split("-W")
        mon = date.fromisocalendar(int(y), int(w), 1)
        sunday = mon - timedelta(days=1)
        return (sunday, sunday + timedelta(days=6))
    else:
        anyday = date.fromisoformat(week)
        sunday = anyday - timedelta(days=(anyday.weekday() + 1) % 7)
        return (sunday, sunday + timedelta(days=6))



class GridCellSerializer(serializers.Serializer):
    isCareNeeded = serializers.BooleanField(required=False)
    availableMembers = serializers.ListField(child=serializers.DictField(), required=False)
    confirmedMember = serializers.DictField(required=False, allow_null=True)

    def to_representation(self, instance):
        rep = {}
        if "isCareNeeded" in instance:
            rep["isCareNeeded"] = bool(instance["isCareNeeded"])
        if "availableMembers" in instance:
            rep["availableMembers"] = instance["availableMembers"]
        if "confirmedMember" in instance:
            rep["confirmedMember"] = instance["confirmedMember"]
        return rep


class ScheduleReadResponseSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    week_id = serializers.IntegerField(allow_null=True)
    week_range = serializers.ListField(child=serializers.CharField())
    status = serializers.ChoiceField(choices=("none", "draft", "finalized"))
    is_owner = serializers.BooleanField()

    # masterGrid는 optional
    masterGrid = serializers.ListField(
        child=serializers.ListField(child=GridCellSerializer()),
        required=False
    )

    meta = serializers.DictField(required=False)


class AvailabilitySlotItemSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    hour = serializers.IntegerField(min_value=0, max_value=23)

class ScheduleAvailabilitySubmitSerializer(serializers.Serializer):
    slots = serializers.ListField(
        child=AvailabilitySlotItemSerializer(),
        allow_empty=False,
        error_messages={
            "required": "slots는 필수입니다.",
            "null": "slots는 null일 수 없습니다.",
            "empty": "slots는 비어 있을 수 없습니다.",
        },
    )

    def validate_slots(self, value):
        seen = set()
        for item in value:
            key = (item["day"], item["hour"])
            if key in seen:
                raise serializers.ValidationError(
                    f"중복된 칸이 포함되어 있습니다: day={item['day']}, hour={item['hour']}"
                )
            seen.add(key)
        if len(value) > 168:
            raise serializers.ValidationError("slots 항목이 168개를 초과할 수 없습니다.")
        return value

class FinalizeAssignmentItemSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    hour = serializers.IntegerField(min_value=0, max_value=23)
    assignee_id = serializers.IntegerField(min_value=1)

class ScheduleFinalizeSerializer(serializers.Serializer):
    assignments = serializers.ListField(
        child=FinalizeAssignmentItemSerializer(),
        allow_empty=False,
        error_messages={
            "required": "assignments는 필수입니다.",
            "null": "assignments는 null일 수 없습니다.",
            "empty": "assignments는 비어 있을 수 없습니다.",
        },
    )

    def validate_assignments(self, value):
        seen = set()
        for item in value:
            key = (item["day"], item["hour"])
            if key in seen:
                raise serializers.ValidationError(
                    f"중복된 칸이 포함되어 있습니다: day={item['day']}, hour={item['hour']}"
                )
            seen.add(key)
        if len(value) > 168:
            raise serializers.ValidationError("assignments 항목이 168개를 초과할 수 없습니다.")
        return value

class ScheduleImportPreviousSerializer(serializers.Serializer):
    source_week_id = serializers.IntegerField(required=False, allow_null=True)

class ScheduleHistoryQuerySerializer(serializers.Serializer):
    room_id = serializers.IntegerField(
        required=True,
        error_messages={
            "required": "room_id is required",
            "invalid": "room_id must be an integer",
        },
    )
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50, default=4)

class ScheduleHistoryItemSerializer(serializers.Serializer):
    week = serializers.CharField()
    status = serializers.ChoiceField(choices=("draft", "finalized"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()

class ScheduleHistoryResponseSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    history = serializers.ListField(child=ScheduleHistoryItemSerializer())