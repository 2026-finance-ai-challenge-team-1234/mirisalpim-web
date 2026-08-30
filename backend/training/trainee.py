"""훈련생이 화면에서 입력한 이름·나이·지역.

사기꾼 프롬프트에만 쓰고 **어디에도 저장하지 않는다.** 매 턴 요청 본문에서 받아
그 요청 안에서만 살아 있다가 사라진다 - Django 세션에도, Session 테이블에도,
engine_state.save_state() 에도 들어가지 않는다.

이렇게 하는 이유: 기획서 10절이 "개인정보 — 로그인·수집 없음"을 심사 방어 논리로
쓰고 있고, ERD 에도 담을 테이블이 없다. 그런데 실제 보이스피싱은 상대의 이름을
알고 걸어오므로, 이름 없이는 훈련의 현실감이 크게 떨어진다. 저장하지 않고
전달만 하면 둘 다 지킬 수 있다.

프론트도 localStorage 를 쓰지 않고 변수로 들고 있다가 매 요청에 실어 보낸다.
"""

#: 화면 입력값이라 길 이유가 없다. 프롬프트가 엉뚱하게 길어지는 것도 막는다.
MAX_FIELD_CHARS = 30

#: 주소는 시·구까지만 쓴다. 상세 주소는 사기꾼 발화에 필요하지 않고
#: 가장 민감한 정보라 LLM 으로 보내지 않는다 (팀 결정, 2026-08-29).
REGION_TOKENS = 2


def from_body(body):
    """요청 본문의 trainee 객체 → (이름, 나이, 지역). 없으면 전부 빈 문자열."""
    raw = body.get("trainee") if isinstance(body, dict) else None
    if not isinstance(raw, dict):
        return "", "", ""

    return (
        _clean(raw.get("name")),
        _clean(raw.get("age")),
        _region(raw.get("address")),
    )


def apply(state, name, age, region):
    """상태에 실어 준다. 이 값은 save_state 가 저장하지 않는다."""
    state.trainee_name = name
    state.trainee_age = age
    state.trainee_region = region


def _clean(value):
    if not isinstance(value, str):
        return ""
    return value.strip()[:MAX_FIELD_CHARS]


def _region(value):
    """'서울시 성북구 xx동 123-4' → '서울시 성북구'."""
    cleaned = _clean(value)
    if not cleaned:
        return ""
    return " ".join(cleaned.split()[:REGION_TOKENS])
