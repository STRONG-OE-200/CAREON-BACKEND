from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework.exceptions import ValidationError
import random
# from .models import SocialAccount

User = get_user_model()

#회원가입

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'password2', 'nickname', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'date_joined')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("이미 사용 중인 이메일입니다.")
        return value

    def validate_nickname(self, value):
        if value and User.objects.filter(nickname=value).exists():
            raise ValidationError("이미 사용 중인 닉네임입니다.")
        return value
    
    def validate(self, attrs):
        if not attrs.get('is_social'):
            if not attrs.get('password') or not attrs.get('password2'):
                raise ValidationError({"password": "비밀번호를 입력해주세요."})
            if attrs['password'] != attrs['password2']:
                raise ValidationError({"password2": "비밀번호가 일치하지 않습니다."})
        return attrs
    

    def create(self, validated_data):
        validated_data.pop('password2', None)
        password = validated_data.pop('password', None)

        nickname = validated_data.get('nickname')
        first_name = validated_data.get('first_name', 'user')

        if not nickname:
            nickname = f"{first_name}{random.randint(1000,9999)}"
            while User.objects.filter(nickname=nickname).exists():
                nickname = f"{first_name}{random.randint(1000,9999)}"

        user = User.objects.create(
            email=validated_data.get('email'),
            nickname=nickname,
            first_name=first_name,
            last_name=validated_data.get('last_name', ''),
        )

        user.set_password(password)
        user.save()

        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self,data):
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise serializers.ValidationError("이메일과 비밀번호를 모두 입력해주세요.")
        
        user =authenticate(username = email, password = password)

        if not user:
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        
        if not user.is_active:
            raise serializers.ValidationError("비활성화된 계정입니다. 관리자에게 문의하세요.")
        
        data["user"] = user
        return data


# class SocialSignupSerializer(serializers.ModelSerializer):
#     provider = serializers.CharField(write_only=True)
#     access_token = serializers.CharField(write_only=True)
#     refresh_token = serializers.CharField(write_only=True, required=False)
#     expires_at = serializers.DateTimeField(write_only=True, required=False)

#     class Meta:
#         model = User
#         fields = ('id', 'email', 'nickname', 'first_name', 'last_name', 'is_social',
#                   'provider', 'access_token', 'refresh_token', 'expires_at')

#     def validate(self, attrs):
#         provider = attrs.get('provider')
#         token = attrs.get('access_token')

#         # 실제 서비스에서는 여기서 provider API 호출로 토큰 검증
#         # 예: Kakao, Google API로 user info 가져오기
#         # 여기서는 단순화: token이 존재하면 OK
#         if not token:
#             raise serializers.ValidationError("액세스 토큰이 필요합니다.")
#         return attrs

#     def create(self, validated_data):
#         provider = validated_data.pop('provider')
#         access_token = validated_data.pop('access_token')
#         refresh_token = validated_data.pop('refresh_token', None)
#         expires_at = validated_data.pop('expires_at', None)

#         # 소셜에서 가져온 기본 정보 (실제 API 호출 결과)
#         social_email = validated_data.get('email')
#         nickname = validated_data.get('nickname') or f"user{random.randint(1000,9999)}"

#         user, created = User.objects.get_or_create(
#             email=social_email,
#             defaults={
#                 'nickname': nickname,
#                 'first_name': validated_data.get('first_name', ''),
#                 'last_name': validated_data.get('last_name', ''),
#                 'is_social': True
#             }
#         )

#         # SocialAccount 생성
#         SocialAccount.objects.update_or_create(
#             user=user,
#             provider=provider,
#             defaults={
#                 'access_token': access_token,
#                 'refresh_token': refresh_token,
#                 'expires_at': expires_at,
#                 'nickname': nickname,
#             }
#         )

#         return user