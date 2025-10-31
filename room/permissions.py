
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsRoomOwner(BasePermission):

    message = "방장에게만 허용된 작업입니다."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.owner_id == request.user.id


class IsRoomMemberOrOwner(BasePermission):
    message = "해당 방의 멤버만 조회/수정할 수 있습니다."
    def has_object_permission(self, request, view, obj):
        u = request.user
        if not u.is_authenticated:
            return False
        if obj.owner_id == u.id:
            return True
        return obj.memberships.filter(user_id=u.id).exists()