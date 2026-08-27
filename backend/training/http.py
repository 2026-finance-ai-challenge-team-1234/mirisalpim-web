import json
import logging
import uuid

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def json_response(data, status=200):
    response = JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = "no-store"
    return response


def error_response(code, message, status, details=None, headers=None):
    """운영 환경에서 내부 예외, 프롬프트, 모델 응답 원문, DB 키를 담지 않음"""
    request_id = f"req_{uuid.uuid4().hex[:16]}"

    # 응답에 실어 보낸 requestId 를 로그에도 남긴다. 사용자가 화면에서 본 오류와
    # 서버 로그를 맞춰보려면 두 곳에 같은 값이 있어야 한다.
    # 메시지는 우리가 쓴 안내 문구뿐이라 개인정보가 섞이지 않는다.
    logger.log(
        logging.ERROR if status >= 500 else logging.WARNING,
        "api_error request_id=%s status=%s code=%s",
        request_id,
        status,
        code,
    )

    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "requestId": request_id,
        }
    }
    response = json_response(payload, status=status)
    for name, value in (headers or {}).items():
        response[name] = value
    return response


def parse_json_body(request):
    """요청 본문을 dict 로 파싱, 형식이 아니면 None."""
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None
