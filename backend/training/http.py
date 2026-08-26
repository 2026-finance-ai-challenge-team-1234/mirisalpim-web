import json
import uuid

from django.http import JsonResponse


def json_response(data, status=200):
    response = JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = "no-store"
    return response


def error_response(code, message, status, details=None):
    """운영 환경에서 내부 예외, 프롬프트, 모델 응답 원문, DB 키를 담지 않음"""
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "requestId": f"req_{uuid.uuid4().hex[:16]}",
        }
    }
    return json_response(payload, status=status)


def parse_json_body(request):
    """요청 본문을 dict 로 파싱, 형식이 아니면 None."""
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None
