# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator

class CustomUser(AbstractUser):
    username = None

    email = models.EmailField(
        max_length=254,
        unique=True,
        null=False,
        blank=False,
        db_index=True,
    )

    nickname = models.CharField(
        max_length=50,
        unique=True,
        null=False,
        blank=False,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9가-힣_.]{2,20}$',
                message="닉네임은 2~20자, 영문/숫자/한글/밑줄/점만 사용할 수 있습니다."
            )
        ],
    )

    first_name = models.CharField(max_length=150, null=False, blank=True, default='')
    last_name = models.CharField(max_length=150, null=False, blank=True, default='')
    date_joined = models.DateTimeField(default=timezone.now, db_index=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] 

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    

# class SocialAccount(models.Model):
#     PROVIDER_CHOICES = (
#         ('google', 'Google'),
#         ('kakao', 'Kakao'),
#         ('naver', 'Naver'),
#         ('apple', 'Apple'),
#     )

#     user = models.ForeignKey(CustomUser, on_delete= models.CASCADE, related_name='social_accounts')
#     provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
#     uid = models.CharField(max_length=255)
#     email = models.EmailField(max_length=254, null=True, blank=True)
#     access_token = models.TextField(null=True, blank=True)
#     refresh_token = models.TextField(null=True, blank=True)
#     expires_at = models.DateTimeField(null=True, blank=True)
#     extra_data = models.JSONField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         unique_together = ('provider', 'uid')

#     def __str__(self):
#         return f"{self.provider} - {self.uid}"
