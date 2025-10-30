import secrets, string
from django.db import transaction, IntegrityError
from rest_framework import serializers
from .models import Room, RoomMembership
from rest_framework import exceptions


_ALPHABET = string.ascii_uppercase + string.digits

def _gen_invite_code(length=8):
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))

class RoomSerializer(serializers.ModelSerializer):
    
    relation = serializers.CharField(max_length=30, write_only=True)

    class Meta:
        model = Room
        fields = ("id","patient","relation","invite_code","owner","created_at","updated_at")
        read_only_fields = ("id","invite_code","owner","created_at","updated_at")
    
    def create(self, validated_data):
        user = self.context["request"].user
        relation = validated_data.pop("relation")

        with transaction.atomic():
            room = None
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

            if room is None:
                raise exceptions.ValidationError("초대코드 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")

            
            RoomMembership.objects.create(
                room=room,
                user=user,
                role=RoomMembership.Role.OWNER,
                relation=relation,
            )

        return room

class RoomJoinSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=32)
    patient = serializers.CharField(max_length=100)
    relation = serializers.CharField(max_length=30)

    def validate(self, attrs):
        try:
            room = Room.objects.get(invite_code=attrs["invite_code"], patient=attrs["patient"])
        except Room.DoesNotExist:
            raise serializers.ValidationError("입장코드 또는 환자 정보가 올바르지 않습니다.")
        attrs["room"] = room
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        room = validated_data["room"]
        relation = validated_data["relation"]

        membership, created = RoomMembership.objects.get_or_create(
            room=room,
            user=user,
            defaults={"relation": relation, "role": RoomMembership.Role.MEMBER},
        )
        if not created:
            raise serializers.ValidationError("이미 이 방에 참여 중입니다.")
        return membership


class RoomMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = RoomMembership
        fields = ("id", "room", "user_id", "user_name", "relation", "role", "joined_at")