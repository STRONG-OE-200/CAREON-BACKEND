from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response

from .models import Room
from .serializers import RoomSerializer
from .permissions import IsRoomOwner
# Create your views here.

class RoomViewSet(viewsets.ModelViewSet):
    
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        
        return (
            Room.objects
                .filter(Q(owner_id=u.id) | Q(memberships__user_id=u.id))
                .distinct()
                .select_related("owner")
        )
    
    def get_permissions(self):
        
        if self.action == "create":
            return [permissions.IsAuthenticated()]

        
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsRoomOwner()]

        
        return [permissions.IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        self.check_object_permissions(request, room) 
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)