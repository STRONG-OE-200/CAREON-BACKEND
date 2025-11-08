from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

DAY_VALIDATORS = [MinValueValidator(0), MaxValueValidator(6)]
HOUR_VALIDATORS = [MinValueValidator(0), MaxValueValidator(23)]

STATUS_CHOICES = (
    ("draft", "Draft"),
    ("finalized", "Finalized"),
)


class Schedule(models.Model):
    room = models.ForeignKey(
        "room.Room",
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_schedules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "schedules"
        constraints = [
            models.UniqueConstraint(fields=["room", "start_date"], name="uq_schedule_room_start_date"),
            models.CheckConstraint(check=models.Q(end_date__gte=models.F("start_date")), name="chk_sched_start_lte_end"),
        ]


class ScheduleNeededSlot(models.Model):
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="needed_slots",
    )
    day = models.PositiveSmallIntegerField(validators=DAY_VALIDATORS)
    hour = models.PositiveSmallIntegerField(validators=HOUR_VALIDATORS)
    needed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "schedule_needed_slots"
        constraints = [
            models.UniqueConstraint(fields=["schedule", "day", "hour"], name="uq_needed_schedule_day_hour"),
            models.CheckConstraint(check=models.Q(day__gte=0, day__lte=6), name="chk_need_day_0_6"),
            models.CheckConstraint(check=models.Q(hour__gte=0, hour__lte=23), name="chk_need_hour_0_23"),
        ]


class ScheduleAvailabilitySlot(models.Model):
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="availability_slots",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_slots",
    )
    day = models.PositiveSmallIntegerField(validators=DAY_VALIDATORS)
    hour = models.PositiveSmallIntegerField(validators=HOUR_VALIDATORS)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "schedule_availability_slots"
        constraints = [
            models.UniqueConstraint(fields=["schedule", "user", "day", "hour"], name="uq_avail_schedule_user_day_hour"),
            models.CheckConstraint(check=models.Q(day__gte=0, day__lte=6), name="chk_avail_day_0_6"),
            models.CheckConstraint(check=models.Q(hour__gte=0, hour__lte=23), name="chk_avail_hour_0_23"),
        ]


class ScheduleAvailabilitySubmission(models.Model):
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="availability_submissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "schedule_availability_submissions"
        constraints = [
            models.UniqueConstraint(fields=["schedule", "user"], name="uq_submission_schedule_user"),
        ]


class ScheduleConfirmedAssignment(models.Model):
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="confirmed_assignments",
    )
    day = models.PositiveSmallIntegerField(validators=DAY_VALIDATORS)
    hour = models.PositiveSmallIntegerField(validators=HOUR_VALIDATORS)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_shifts",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="finalized_schedules",
    )
    finalized_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "schedule_confirmed_assignments"
        constraints = [
            models.UniqueConstraint(fields=["schedule", "day", "hour"], name="uq_confirmed_schedule_day_hour"),
            models.CheckConstraint(check=models.Q(day__gte=0, day__lte=6), name="chk_confirm_day_0_6"),
            models.CheckConstraint(check=models.Q(hour__gte=0, hour__lte=23), name="chk_confirm_hour_0_23"),
        ]
