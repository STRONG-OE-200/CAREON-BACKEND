# calender/utils.py

from room.models import Room, RoomMembership
from user.models import CustomUser as User


def is_room_member(room: Room, user: User) -> bool:
    """
    프로젝트 실제 구조에 맞춘 방 멤버 체크 함수.
    RoomMembership(room, user)을 통해 멤버를 판별한다.
    """
    return RoomMembership.objects.filter(room=room, user=user).exists()
