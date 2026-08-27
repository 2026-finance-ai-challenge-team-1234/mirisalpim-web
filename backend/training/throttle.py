"""턴 요청 제한 — 레이트 리밋과 재시도 멱등성.

API 설계 9절: 턴 20회/분/익명 세션 → 429 + Retry-After
API 설계 4-6: Idempotency-Key 로 재시도가 턴을 두 번 진행시키지 않게 한다

⚠️ Django 기본 캐시(LocMemCache)는 프로세스마다 따로 있다. 워커가 여러 개인
배포에서는 실질 한도가 워커 수만큼 늘어난다. 정확한 제한이 필요하면 Redis 같은
공유 캐시를 붙여야 한다 - MVP 에서는 폭주와 요금 폭증을 막는 목적으로 충분하다.
"""

from django.core.cache import cache

#: 익명 세션당 분당 턴 수
TURN_RATE_LIMIT = 20
TURN_RATE_WINDOW_SECONDS = 60

#: 같은 Idempotency-Key 로 다시 오면 이 시간 동안 첫 응답을 그대로 돌려준다
IDEMPOTENCY_TTL_SECONDS = 300


def turn_rate_exceeded(anon_client_id):
    """한도를 넘었으면 재시도까지 남은 초, 아니면 None."""
    key = f"turn-rate:{anon_client_id}"

    if cache.add(key, 1, TURN_RATE_WINDOW_SECONDS):
        return None

    try:
        count = cache.incr(key)
    except ValueError:
        # incr 직전에 창이 끝난 경우. 새 창을 연다.
        cache.set(key, 1, TURN_RATE_WINDOW_SECONDS)
        return None

    return TURN_RATE_WINDOW_SECONDS if count > TURN_RATE_LIMIT else None


def idempotency_cache_key(request, session_id):
    """헤더가 없으면 None - 멱등 처리를 하지 않는다."""
    raw = request.headers.get("Idempotency-Key", "").strip()
    return f"idem:{session_id}:{raw}" if raw else None


def remembered_turn(key):
    return cache.get(key) if key else None


def remember_turn(key, payload):
    if key:
        cache.set(key, payload, IDEMPOTENCY_TTL_SECONDS)
