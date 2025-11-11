from django.db import models
from django.conf import settings
from django.db import models
from django.utils import timezone


class LogMetric(models.Model):
    
    room = models.ForeignKey(
        to='room.Room',                 
        on_delete=models.CASCADE,
        related_name='log_metrics',
        db_index=True,
    )
    label = models.CharField(max_length=100)  
    sort_order = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['room']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['room', 'label'], name='uq_logmetric_room_label')
        ]

    def __str__(self) -> str:
        return f"[Room#{self.room_id}] {self.label}"


class CareLog(models.Model):
    
    room = models.ForeignKey(
        to='room.Room',
        on_delete=models.CASCADE,
        related_name='care_logs',
        db_index=True,
    )
    metric = models.ForeignKey(
        to=LogMetric,
        on_delete=models.CASCADE,
        related_name='logs',
        db_index=True,
    )
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,   
        related_name='care_logs',
        db_index=True,
    )

    content = models.TextField()           
    memo = models.TextField(blank=True, null=True)

    time_only = models.TimeField()         
    
    date_only = models.DateField(default=timezone.localdate) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['room']),
            models.Index(fields=['metric']),
            models.Index(fields=['author']),
            models.Index(fields=['room', 'metric', 'date_only', 'time_only']),
        ]

    def __str__(self) -> str:
        return f"[Room#{self.room_id} Metric#{self.metric_id}] {self.date_only} {self.time_only} - {self.content[:30]}"
