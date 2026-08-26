"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views import defaults
from django.views.generic import TemplateView

from training.http import error_response

API_PREFIX = "/api/"


def health(request):
    return JsonResponse({"status": "ok"})


def not_found(request, exception=None):
    """API 경로의 404 는 JSON 으로 돌려준다.

    기본 404 는 HTML 이라 프론트 client.js 의 res.json() 이 깨지고, 경로 오타든
    엔드포인트 누락이든 전부 code "UNKNOWN" 으로 뭉개진다. 원인을 화면에서
    구분할 수 없게 되는 지점이라 API 하위만 JSON 으로 바꾼다.

    ⚠️ DEBUG=True 면 Django 가 자체 디버그 페이지를 먼저 보여줘서 이 핸들러를
    타지 않는다. 배포(DEBUG=False)에서만 적용된다.
    """
    if request.path.startswith(API_PREFIX):
        return error_response("NOT_FOUND", "요청한 경로를 찾을 수 없습니다.", 404)
    return defaults.page_not_found(request, exception)


def server_error(request):
    """API 경로의 500 도 같은 이유로 JSON 계약을 지킨다."""
    if request.path.startswith(API_PREFIX):
        return error_response(
            "INTERNAL_ERROR", "서버에서 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.", 500
        )
    return defaults.server_error(request)


handler404 = "config.urls.not_found"
handler500 = "config.urls.server_error"


urlpatterns = [
    path("health/", health),
    path("admin/", admin.site.urls),

    # 프론트 client.js의 API_BASE "/api/v1"
    path("api/v1/", include("training.urls")),

    # 반드시 가장 마지막에 배치
    re_path(
        r"^(?!api/|admin/|health/|static/).*$",
        TemplateView.as_view(template_name="index.html"),
    ),
]
