from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

class WeekSchedule(models.Model):
    room = models.ForeignKey(
        "room.Room",
        on_delete=models.CASCADE,
        related_name="week_schedules"
    )
    week_start = models.DateField()
    is_finalized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("room", "week_start")
        ordering = ["-week_start"]

    def __str__(self):
        return f"Room {self.room_id} - {self.week_start}"

    def clean(self):
        if self.week_start.weekday() != 6:
            raise ValidationError("week_start는 일요일(weekday == 6)이어야 합니다.")



class NeededCell(models.Model):
    week = models.ForeignKey(
        WeekSchedule,
        on_delete=models.CASCADE,
        related_name="needed_cells"
    )
    day = models.SmallIntegerField()
    hour = models.SmallIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("week", "day", "hour")
        indexes = [models.Index(fields=["week", "day", "hour"])]

    def __str__(self):
        return f"Week {self.week_id} - d{self.day} h{self.hour}"

    def clean(self):
        if not (0 <= self.day <= 6):
            raise ValidationError("day는 0~6(일~토) 범위여야 합니다.")
        if not (0 <= self.hour <= 23):
            raise ValidationError("hour는 0~23 범위여야 합니다.")