from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from log.models import LogMetric
# Create your models here.

class Room(models.Model):
    patient = models.CharField(max_length=100, db_index=True)
    invite_code = models.CharField(max_length=32, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_rooms", db_index=True)
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"Room(id={self.id}, patient={self.patient})"
    


@receiver(post_save, sender=Room)
def create_default_metrics(sender, instance, created, **kwargs):
    if created:
        defaults = ["체온", "혈압"]
        for label in defaults:
            LogMetric.objects.get_or_create(room=instance, label=label)
class RoomMembership(models.Model):


    class Role(models.TextChoices):
        OWNER = "OWNER", "OWNER"
        MEMBER = "MEMBER", "MEMBER"
    
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="room_memberships",
        db_index=True, 
    )

    relation = models.CharField(max_length=30, blank=True, null=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"],
                name= "unique_room_user",
            ),
        ]
        
    def __str__(self):
        return f"RoomMembership(room={self.room.patient}, user={self.user.name}, role={self.role})"