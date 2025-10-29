
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsRoomOwner(BasePermission):

    message = "방장에게만 허용된 작업입니다."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.owner_id == request.user.id
