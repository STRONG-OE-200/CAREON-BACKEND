# utils/cookies.py
from urllib.parse import urlparse
from datetime import timedelta
from django.conf import settings

def is_cross_site(request) -> bool:
    origin = request.headers.get("Origin")
    if not origin:
        return False
    return urlparse(origin).netloc != request.get_host()

def cookie_kwargs_for(request):
    cross = is_cross_site(request)

    # SIMPLE_JWT에서 refresh 수명 가져오기 (기본 7일 가정)
    rt_lifetime: timedelta = settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME")
    if not rt_lifetime:
        # fallback — SimpleJWT 기본값과 맞추거나 원하는 기간으로
        rt_lifetime = timedelta(days=7)

    max_age = int(rt_lifetime.total_seconds())
    

    samesite = "None" if cross else "Lax"
    
    kwargs = {
        "httponly": True,
        "secure": True if samesite == "None" else (not settings.DEBUG),
        #  ↑ 교차 사이트(None)일 땐 무조건 Secure (브라우저 규칙)
        "samesite": samesite,
        "path": "/",
        "max_age": max_age,
    }

    # 여러 서브도메인에서 쿠키를 공유해야 한다면 여기를 활성화
    # 예: 프론트가 careon.io.kr, 다른 서브도메인도 쿠키를 봐야 하는 경우
    # kwargs["domain"] = ".careon.io.kr"

    return kwargs
