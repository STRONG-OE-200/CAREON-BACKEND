from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Room
from django.http import Http404
from .serializers import *
from .permissions import IsRoomOwner, IsRoomMemberOrOwner
# Create your views here.

class RoomViewSet(viewsets.ModelViewSet):
    
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]


    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise Http404("해당 방을 찾을 수 없습니다.")
        
    def get_queryset(self):
        u = self.request.user
        qs = Room.objects.select_related("owner")
    
        if self.action == "list":
            return qs.filter(Q(owner_id=u.id) | Q(memberships__user_id=u.id)).distinct()
    
        return qs

    
    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]

    
        if self.action in ["retrieve", "members", "leave"]:
            return [permissions.IsAuthenticated(), IsRoomMemberOrOwner()]

    
        if self.action in ["update", "partial_update", "destroy", "remove_member"]:
            return [permissions.IsAuthenticated(), IsRoomOwner()]

    
        return [permissions.IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        self.check_object_permissions(request, room) 
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # 커스텀
    
    # 방 들어가기
    @action(detail=False, methods=["post"], url_path="join")
    def join(self, request):
        ser = RoomJoinSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        membership = ser.save()  
        return Response(RoomMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        room = self.get_object()  # 여기서 객체 찾고, 위 get_permissions 로 403 처리됨
        memberships = (
            RoomMembership.objects
            .filter(room=room)
            .select_related("user", "room")
            .order_by("-joined_at")
        )
        data = RoomMembershipSerializer(memberships, many=True).data
        return Response(data, status=status.HTTP_200_OK)


    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>\d+)")
    def remove_member(self, request, pk=None, user_id=None):
        room = self.get_object()
        # 방장 권한 확인

        try:
            membership = RoomMembership.objects.select_related("user").get(room=room, user_id=user_id)
        except RoomMembership.DoesNotExist:
            return Response({"detail": "해당 멤버를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # OWNER 삭제 방지
        if membership.role == RoomMembership.Role.OWNER:
            return Response({"detail": "방장 계정은 삭제할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        if int(user_id) == request.user.id:
            return Response({"detail": "방장 계정은 삭제할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="leave")
    def leave(self, request, pk=None):
        room = self.get_object()


        try:
            membership = RoomMembership.objects.get(room=room, user=request.user)
        except RoomMembership.DoesNotExist:
            return Response({"detail": "이 방의 멤버가 아닙니다."}, status=status.HTTP_403_FORBIDDEN)

        if membership.role == RoomMembership.Role.OWNER:
            return Response({"detail": "방장은 탈퇴할 수 없습니다. 방을 삭제하거나 소유권 이전이 필요합니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)