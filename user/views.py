from django.shortcuts import render
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from utils.cookies import cookie_kwargs_for, is_cross_site
from .serializers import SignupSerializer, LoginSerializer
from  rest_framework_simplejwt.tokens import RefreshToken
from room.models import Room, RoomMembership

# Create your views here.
User = get_user_model()

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "✅회원가입이 완료되었습니다.",
                "id": user.id,
                "name" : user.name,
                "date_joined": user.date_joined
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def _membership_index(self, room_id: int, user_id: int):
    
        user_ids = list(
            RoomMembership.objects
            .filter(room_id=room_id)
            .order_by('joined_at')
            .values_list('user_id', flat=True)
        )
        try:
            return user_ids.index(user_id)
        except ValueError:
            return None

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data['user']

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            owned_ids = list(
                Room.objects.filter(owner=user).values_list('id', flat=True)
            )
            memberships = list(
                RoomMembership.objects.filter(user=user).values('room_id')
            )

            rooms_payload = []
            seen = set()

            # 방장인 방들
            for rid in owned_ids:
                rooms_payload.append({
                    "room_id": rid,
                    "isOwner": True,
            
                    "membership_index": self._membership_index(rid, user.id),
                })
                seen.add(rid)

            # 멤버로 속한 방들
            for m in memberships:
                rid = m["room_id"]
                if rid in seen:
                    continue
                rooms_payload.append({
                    "room_id": rid,
                    "isOwner": False,
                    "membership_index": self._membership_index(rid, user.id),
                })
                seen.add(rid)

            response = Response({
                "message": "로그인 성공",
                "user_id": user.id,            
                "access": access_token,
                "email": user.email,
                "name": user.name,
                "rooms": rooms_payload,       
            }, status=status.HTTP_200_OK)

            opts = cookie_kwargs_for(request)
            response.set_cookie("refresh_token", refresh_token, **opts)
            return response
        

class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
        
                pass

        response = Response({"message": "정상적으로 로그아웃되었습니다."}, status=status.HTTP_200_OK)

        opts = cookie_kwargs_for(request)
        opts.pop("max_age", None)
        opts.pop("expires", None)
        response.set_cookie("refresh_token", "", max_age=0, expires=0, **opts)

        return response


class CookieTokenRefreshRotatingView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        old_refresh_str = request.COOKIES.get("refresh_token")
        if not old_refresh_str:
            return Response({"detail": "refresh_token 쿠키가 없습니다."}, status=status.HTTP_400_BAD_REQUEST,)
        try:
            old_refresh = RefreshToken(old_refresh_str)  

            try:
                old_refresh.blacklist()
            except Exception:
                pass

        
            user_id = old_refresh.payload.get("user_id")
            if not user_id:
                return Response({"detail": "토큰에 user_id가 없습니다."}, status=status.HTTP_401_UNAUTHORIZED)

            user = User.objects.filter(id=user_id).first()
            if not user or not user.is_active:
                return Response({"detail": "사용자를 찾을 수 없거나 비활성화 상태입니다."}, status=status.HTTP_401_UNAUTHORIZED)

            new_refresh = RefreshToken.for_user(user)
            new_access  = str(new_refresh.access_token)

            # 새 refresh를 다시 쿠키로 세팅
            response = Response({"access": new_access}, status=status.HTTP_200_OK)
            opts = cookie_kwargs_for(request)  
            response.set_cookie("refresh_token", str(new_refresh), **opts)
            return response
        except Exception:
            return Response({"detail": "유효하지 않은 refresh token입니다."}, status=status.HTTP_401_UNAUTHORIZED)