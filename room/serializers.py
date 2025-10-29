import secrets, string
from django.db import transaction, IntegrityError
from rest_framework import serializers
from .models import Room, RoomMembership


_ALPHABET = string.ascii_uppercase + string.digits

def _gen_invite_code(length=8):
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))

class RoomSerializer(serializers.ModelSerializer):

    class Meta:
        model = Room
        fields = ("id","patient","invite_code","owner","created_at","updated_at")
        read_only_fields = ("id","invite_code","owner","created_at","updated_at")
    
    def create(self, validated_data):
        user = self.context["request"].user
        with transaction.atomic():
            for _ in range(5):                 
                try:
                    room = Room.objects.create(
                        owner=user,
                        invite_code=_gen_invite_code(),
                        **validated_data
                    )
                    break
                except IntegrityError:
                    continue
            RoomMembership.objects.create(room=room, user=user, role=RoomMembership.Role.OWNER)
        return room