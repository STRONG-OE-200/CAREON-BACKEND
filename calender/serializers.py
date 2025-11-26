from rest_framework import serializers
from .models import CalendarEvent, CalendarAttachment, UploadedFile
from user.models import CustomUser as User
from django.utils import timezone
from datetime import timezone as dt_timezone


class CalendarAttachmentInputSerializer(serializers.Serializer):
    file_id = serializers.CharField()
    type = serializers.ChoiceField(choices=CalendarAttachment.AttachmentType.choices)


class CalendarAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()  
    class Meta:
        model = CalendarAttachment
        fields = ("id", "type", "url", "file_id")

    def get_url(self, obj):
        try:
            uploaded = UploadedFile.objects.get(id=int(obj.file_id))
        except (UploadedFile.DoesNotExist, ValueError, TypeError):
            return ""

        request = self.context.get("request")
        if uploaded.file and hasattr(uploaded.file, "url"):
            if request is not None:
                return request.build_absolute_uri(uploaded.file.url)
            return uploaded.file.url
        return ""


class AssigneeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name")


class CalendarEventSummarySerializer(serializers.ModelSerializer):
    assignee = AssigneeSerializer(read_only=True)
    start_at = serializers.SerializerMethodField()
    end_at = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = (
            "id",
            "date",
            "title",
            "start_at",
            "end_at",
            "assignee",
            "is_all_day",
        )

    def to_local(self, dt):
        if not dt:
            return None
        
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, dt_timezone.utc)
        
        return timezone.localtime(dt).isoformat()

    def get_start_at(self, obj):
        return self.to_local(obj.start_at)

    def get_end_at(self, obj):
        return self.to_local(obj.end_at)



class CalendarEventSerializer(serializers.ModelSerializer):
    attachments = CalendarAttachmentSerializer(many=True, read_only=True)
    assignee = AssigneeSerializer(read_only=True)
    room_id = serializers.IntegerField(source="room.id", read_only=True)

    start_at = serializers.SerializerMethodField()
    end_at = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = (
            "id",
            "room_id",
            "date",
            "title",
            "start_at",
            "end_at",
            "is_all_day",
            "repeat_rule",
            "repeat_until",
            "description",
            "attachments",
            "assignee",
            "created_at",
            "updated_at",
        )

    def to_local(self, dt):
        if not dt:
            return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, dt_timezone.utc)
        return timezone.localtime(dt).isoformat()

    def get_start_at(self, obj):
        return self.to_local(obj.start_at)

    def get_end_at(self, obj):
        return self.to_local(obj.end_at)



class CalendarEventCreateUpdateSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    title = serializers.CharField(required=False)
    start_at = serializers.DateTimeField(required=False)
    end_at = serializers.DateTimeField(required=False)
    is_all_day = serializers.BooleanField(required=False)
    repeat_rule = serializers.ChoiceField(choices=CalendarEvent.RepeatRule.choices, required=False)
    repeat_until = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(required=False, max_length=50, allow_blank=True)
    attachments = CalendarAttachmentInputSerializer(many=True, required=False, allow_null=True)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        instance = self.instance

        start_at = attrs.get("start_at") or (instance.start_at if instance else None)
        end_at = attrs.get("end_at") or (instance.end_at if instance else None)

        if start_at and end_at and start_at >= end_at:
            raise serializers.ValidationError({
                "error_code": "CALENDAR_TIME_RANGE_INVALID",
                "message": "시작 시간이 종료 시간보다 늦을 수 없습니다.",
                "detail": {"fields": ["start_at", "end_at"]},
            })

        repeat_rule = attrs.get("repeat_rule") or (instance.repeat_rule if instance else None)
        repeat_until = attrs.get("repeat_until") or (instance.repeat_until if instance else None)

        if repeat_rule and repeat_rule != "NONE" and not repeat_until:
            raise serializers.ValidationError({
                "error_code": "CALENDAR_REPEAT_UNTIL_REQUIRED",
                "message": "반복 일정의 종료 날짜가 필요합니다.",
                "detail": {"fields": ["repeat_rule", "repeat_until"]},
            })

        return attrs


class UploadedFileSerializer(serializers.ModelSerializer):
    file_id = serializers.ReadOnlyField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = ["file_id", "type", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file and hasattr(obj.file, "url"):
            if request is not None:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return ""
