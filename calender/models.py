from django.conf import settings
from django.db import models
from room.models import Room  


class CalendarEvent(models.Model):
    class RepeatRule(models.TextChoices):
        NONE = "NONE", "None"
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="calendar_events",
    )
    date = models.DateField(help_text="캘린더에서 선택된 기준 날짜")
    title = models.CharField(max_length=255)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_all_day = models.BooleanField(default=False)
    repeat_rule = models.CharField(
        max_length=10,
        choices=RepeatRule.choices,
        default=RepeatRule.NONE,
    )
    repeat_until = models.DateField(null=True, blank=True)
    description = models.CharField(
        max_length=50,  # 50자 제한
        null=True,
        blank=True,
        help_text="설명(50자 이내)",
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_events",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]

    def __str__(self):
        return f"[{self.room_id}] {self.title} ({self.date})"


class CalendarAttachment(models.Model):
    class AttachmentType(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        AUDIO = "AUDIO", "Audio"

    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file_id = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=AttachmentType.choices)

    # 실제 파일 URL은 파일 서비스 쪽에서 만들어준다고 가정
    url = models.URLField(max_length=2048, blank=True, default="")

    def __str__(self):
        return f"{self.type} - {self.file_id}"
