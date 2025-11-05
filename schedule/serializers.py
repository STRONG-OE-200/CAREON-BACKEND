from rest_framework import serializers
from .models import WeekSchedule
from room.models import Room

class WeekScheduleSerializer(serializers.ModelSerializer):
    # 입력/출력 모두 room_id로 쓰고, 내부적으로 model의 room 필드에 매핑
    room_id = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        source="room"
    )

    class Meta:
        model = WeekSchedule
        fields = ["id", "room_id", "week_start", "is_finalized", "created_at"]
        read_only_fields = ["id", "is_finalized", "created_at"]

    def validate_week_start(self, value):
        if value.weekday() != 6:
            raise serializers.ValidationError("week_start는 일요일(YYYY-MM-DD)이어야 합니다.")
        return value

    def validate(self, attrs):
        room = attrs.get("room")
        week_start = attrs.get("week_start")
        if WeekSchedule.objects.filter(room=room, week_start=week_start).exists():
            raise serializers.ValidationError("이미 동일한 주차 스케줄이 존재합니다.")
        return attrs


class NeededCellItemSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    hour = serializers.IntegerField(min_value=0, max_value=23)

class NeededBulkReplaceSerializer(serializers.Serializer):
    cells = NeededCellItemSerializer(many=True, allow_empty=True)

    def validate(self, attrs):
        pairs = [(c["day"], c["hour"]) for c in attrs.get("cells", [])]
        if len(pairs) != len(set(pairs)):
            raise serializers.ValidationError("cells 항목에 중복 (day, hour)이 있습니다.")
        return attrs


class NeededBulkResultSerializer(serializers.Serializer):
    week_schedule_id = serializers.IntegerField()
    updated_cells = serializers.IntegerField()
    updated_at = serializers.DateTimeField()