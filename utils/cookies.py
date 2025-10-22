from urllib.parse import urlparse

def is_cross_site(request) -> bool:
    origin = request.headers.get("Origin")
    if not origin:
        return False  # Postman 등 Origin 없는 경우
    return urlparse(origin).netloc != request.get_host()

def cookie_kwargs_for(request):
    cross = is_cross_site(request)
    return {
        "httponly": True,
        "secure": True,                     # HTTPS 배포 기준 항상 True
        "samesite": "None" if cross else "Lax",
        "path": "/",
    }
