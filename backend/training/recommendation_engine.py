"""
미리살핌 - 규칙 기반 추천 알고리즘

사용법 (백엔드 팀원):
    from recommendation_engine import recommend

    result = recommend({
        "userName": "홍길동",
        "age": "AGE_60",
        "activities": ["ACT_MOBILE_BANKING", "ACT_LOAN_INSURANCE"],
        "concerns": ["CONCERN_01", "CONCERN_09"],
        "habit": "HABIT_LISTEN",
    })
    # result 는 아래 "반환값" 항목 참고, 그대로 API 응답 JSON으로 내려주면 됨

이 함수는 순수 함수입니다 (DB, 네트워크 호출 없음). 어떤 프레임워크에서든
survey 응답 dict 하나를 만들어서 recommend()에 넘기고, 반환된 dict를
JSON으로 직렬화해서 응답하면 됩니다.

입력 (survey dict) 필드:
    userName   : str
    age        : AGE_* 코드 1개 (아래 AGE_LABELS 참고)
    activities : ACT_* 코드 리스트 (다중 선택, 0개 이상)
    concerns   : CONCERN_* 코드 리스트 (다중 선택, 0개 이상)
    habit      : HABIT_* 코드 1개

반환값 (dict):
    recommendedCategory    : "T01" ~ "S08" (중분류 코드)
    recommendedSubcategory : "T01-1" 같은 소분류 코드
    channel                : "voice" | "sms"
    title                  : 훈련 제목 (str)
    description            : 훈련 설명 (str)
    difficulty              : "easy" | "normal" | "hard"
    match                  : 적합도 (int, 88~98)
    reasons                : 추천 이유 문장 리스트 (최대 3개)
"""

import random
from typing import Dict, List, TypedDict


# ────────────────────────────────────────────────────────────
# 1. 코드 정의 (프론트-백엔드 계약. 프론트는 이 코드값 그대로 요청에 담아 보내야 함)
# ────────────────────────────────────────────────────────────

AGE_CODES = ["AGE_10", "AGE_20", "AGE_30", "AGE_40", "AGE_50", "AGE_60"]

ACTIVITY_CODES = [
    "ACT_MOBILE_BANKING",   # 모바일 뱅킹
    "ACT_ONLINE_SHOPPING",  # 온라인 쇼핑
    "ACT_SECONDHAND",       # 중고거래
    "ACT_INVESTMENT",       # 주식·코인 투자
    "ACT_PAYMENT",          # 카드·간편결제
    "ACT_LOAN_INSURANCE",   # 대출·보험
    "ACT_JOB",              # 구직·아르바이트
    "ACT_MESSENGER",        # 메신저 사용 (가족·지인 연락)
    "ACT_NONE",             # 해당 없음
]

CONCERN_CODES = [
    "CONCERN_01",  # 계좌가 범죄에 연루되었다는 연락
    "CONCERN_02",  # 가족이 급하게 돈을 요청
    "CONCERN_03",  # 휴대폰이 고장났다며 다른 번호로 연락
    "CONCERN_04",  # 택배 배송에 문제가 있다는 연락
    "CONCERN_05",  # 해외에서 큰 금액이 결제됐다는 연락
    "CONCERN_06",  # 고수익 아르바이트 제안
    "CONCERN_07",  # 원금 보장·고수익 투자 제안
    "CONCERN_08",  # 정부지원 대출 대상자로 선정됐다는 연락
    "CONCERN_09",  # 보안 강화를 위해 앱 설치·화면공유를 요구
    "CONCERN_10",  # 지금 처리 안 하면 계좌·서비스가 정지된다는 압박
    "CONCERN_11",  # 출석 요구·수사 협조 요청
    "CONCERN_12",  # 모바일 청첩장·부고 등 경조사 안내 문자
    "CONCERN_13",  # 설문조사·경품 당첨 안내 문자
    "CONCERN_14",  # SNS·메신저로 친해진 사람이 투자를 권유하거나 돈을 요청
    "CONCERN_15",  # 통신요금 미납이나 서비스 이용료를 안내하는 전화
    "CONCERN_16",  # 교통범칙금·과태료 또는 세금 환급을 안내하는 문자
    "CONCERN_17",  # 온라인에서 알게 된 사람이 호감을 표현하며 접근
    "CONCERN_18",  # 잘 모르겠어요
]

HABIT_CODES = [
    "HABIT_HANGUP",           # 바로 끊는다
    "HABIT_LISTEN",           # 일단 이야기를 들어본다
    "HABIT_VERIFY_PERSON",    # 상대방 신원을 먼저 확인한다
    "HABIT_ASK_FAMILY",       # 가족·지인에게 물어본다
    "HABIT_VERIFY_OFFICIAL",  # 해당 기관에 직접 확인한다
    "HABIT_ASK_DETAIL",       # 상대방에게 자세히 물어본다
    "HABIT_FOLLOW",           # 특별히 의심되지 않으면 따른다
    "HABIT_VARIABLE",         # 상황에 따라 다르다
]

CATEGORY_CODES = [
    "T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08",
    "S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08",
]

TIE_THRESHOLD = 0  # 동점 처리 정책: "정확히" 동점일 때만 T계열(전화) 우선.
                    # ⚠️ 가중치 값이 0~3 단위로 촘촘해서, 이 값을 1 이상으로 올리면
                    # 대부분의 카테고리가 "근소한 차이"로 뭉뚱그려져 사실상 항상 전화가
                    # 이기는 부작용이 생김 (실측 확인됨). 절대 임의로 올리지 말 것.


# ────────────────────────────────────────────────────────────
# 2. Q1 연령대 가중치
# ────────────────────────────────────────────────────────────

AGE_WEIGHTS: Dict[str, Dict[str, int]] = {
    "AGE_10": {"T01": 0, "T02": 0, "T03": 1, "T04": 0, "T05": 2, "T06": 1, "T07": 1, "T08": 1,
               "S01": 0, "S02": 1, "S03": 2, "S04": 1, "S05": 1, "S06": 3, "S07": 3, "S08": 1},
    "AGE_20": {"T01": 0, "T02": 1, "T03": 1, "T04": 1, "T05": 3, "T06": 1, "T07": 1, "T08": 2,
               "S01": 1, "S02": 1, "S03": 3, "S04": 2, "S05": 1, "S06": 2, "S07": 2, "S08": 3},
    "AGE_30": {"T01": 1, "T02": 2, "T03": 1, "T04": 1, "T05": 2, "T06": 1, "T07": 1, "T08": 2,
               "S01": 1, "S02": 1, "S03": 2, "S04": 3, "S05": 1, "S06": 2, "S07": 1, "S08": 2},
    "AGE_40": {"T01": 2, "T02": 2, "T03": 2, "T04": 2, "T05": 2, "T06": 1, "T07": 1, "T08": 1,
               "S01": 2, "S02": 2, "S03": 1, "S04": 3, "S05": 2, "S06": 1, "S07": 1, "S08": 2},
    "AGE_50": {"T01": 3, "T02": 2, "T03": 2, "T04": 2, "T05": 2, "T06": 2, "T07": 1, "T08": 1,
               "S01": 3, "S02": 2, "S03": 1, "S04": 2, "S05": 2, "S06": 1, "S07": 1, "S08": 2},
    "AGE_60": {"T01": 3, "T02": 1, "T03": 3, "T04": 3, "T05": 1, "T06": 3, "T07": 1, "T08": 0,
               "S01": 3, "S02": 3, "S03": 1, "S04": 1, "S05": 3, "S06": 1, "S07": 1, "S08": 0},
}

# ────────────────────────────────────────────────────────────
# 3. Q2 활동 가중치 (다중선택 → 선택된 항목들 합산)
# ────────────────────────────────────────────────────────────

ACTIVITY_WEIGHTS: Dict[str, Dict[str, int]] = {
    "ACT_MOBILE_BANKING":  {"T01": 2, "T02": 2, "T03": 0, "T04": 1, "T05": 0, "T06": 2, "T07": 0, "T08": 0,
                             "S01": 2, "S02": 0, "S03": 0, "S04": 2, "S05": 0, "S06": 0, "S07": 1, "S08": 0},
    "ACT_ONLINE_SHOPPING": {"T01": 0, "T02": 0, "T03": 0, "T04": 0, "T05": 0, "T06": 0, "T07": 1, "T08": 0,
                             "S01": 0, "S02": 0, "S03": 3, "S04": 0, "S05": 0, "S06": 1, "S07": 1, "S08": 0},
    "ACT_SECONDHAND":      {"T01": 0, "T02": 1, "T03": 0, "T04": 0, "T05": 0, "T06": 0, "T07": 0, "T08": 0,
                             "S01": 0, "S02": 0, "S03": 2, "S04": 1, "S05": 0, "S06": 0, "S07": 1, "S08": 0},
    "ACT_INVESTMENT":      {"T01": 0, "T02": 3, "T03": 0, "T04": 0, "T05": 0, "T06": 0, "T07": 0, "T08": 0,
                             "S01": 0, "S02": 0, "S03": 0, "S04": 0, "S05": 0, "S06": 0, "S07": 0, "S08": 3},
    "ACT_PAYMENT":         {"T01": 0, "T02": 2, "T03": 0, "T04": 0, "T05": 0, "T06": 0, "T07": 0, "T08": 0,
                             "S01": 0, "S02": 0, "S03": 0, "S04": 3, "S05": 0, "S06": 0, "S07": 0, "S08": 0},
    "ACT_LOAN_INSURANCE":  {"T01": 0, "T02": 1, "T03": 0, "T04": 0, "T05": 3, "T06": 0, "T07": 0, "T08": 0,
                             "S01": 1, "S02": 0, "S03": 0, "S04": 0, "S05": 0, "S06": 0, "S07": 0, "S08": 3},
    "ACT_JOB":             {"T01": 0, "T02": 0, "T03": 0, "T04": 0, "T05": 3, "T06": 0, "T07": 0, "T08": 1,
                             "S01": 0, "S02": 0, "S03": 0, "S04": 0, "S05": 0, "S06": 0, "S07": 0, "S08": 1},
    "ACT_MESSENGER":       {"T01": 0, "T02": 0, "T03": 2, "T04": 0, "T05": 0, "T06": 0, "T07": 0, "T08": 1,
                             "S01": 0, "S02": 3, "S03": 0, "S04": 0, "S05": 0, "S06": 2, "S07": 0, "S08": 0},
    "ACT_NONE":            {c: 0 for c in CATEGORY_CODES},
}

# ────────────────────────────────────────────────────────────
# 4. Q3 취약상황 가중치 + 소분류 후보 (다중선택)
# ────────────────────────────────────────────────────────────

CONCERN_WEIGHTS: Dict[str, Dict[str, int]] = {
    "CONCERN_01": {"T01": 3, "T04": 3, "S01": 2},
    "CONCERN_02": {"T03": 3, "S02": 3},
    "CONCERN_03": {"T03": 2, "S02": 2},
    "CONCERN_04": {"T07": 2, "S03": 3},
    "CONCERN_05": {"T02": 2, "S04": 3},
    "CONCERN_06": {"T05": 3, "S08": 1},
    "CONCERN_07": {"T02": 2, "S08": 3},
    "CONCERN_08": {"T05": 3, "S05": 1, "S08": 2},
    "CONCERN_09": {"T06": 3, "S07": 3},
    "CONCERN_10": {"T01": 2, "T06": 1, "S01": 1},
    "CONCERN_11": {"T04": 3, "S01": 1},
    "CONCERN_12": {"S06": 3},
    "CONCERN_13": {"S06": 2, "S07": 1},
    "CONCERN_14": {"T08": 3, "S08": 1},
    "CONCERN_15": {"T07": 3},
    "CONCERN_16": {"S05": 3},
    "CONCERN_17": {"T08": 2},
    "CONCERN_18": {},  # 잘 모르겠어요: 특정 카테고리 가중 없음 (아래에서 전체 +1 별도 처리)
}

# 각 concern이 매칭됐을 때, 해당 중분류 안에서 뽑힐 수 있는 소분류 후보
CONCERN_SUBCATEGORY_CANDIDATES: Dict[str, Dict[str, List[str]]] = {
    "CONCERN_01": {"T01": ["T01-1", "T01-2", "T01-4"], "T04": ["T04-1", "T04-2", "T04-3"], "S01": ["S01-1", "S01-2", "S01-4"]},
    "CONCERN_02": {"T03": ["T03-1", "T03-8"], "S02": ["S02-1", "S02-7"]},
    "CONCERN_03": {"T03": ["T03-5", "T03-6"], "S02": ["S02-4", "S02-5"]},
    "CONCERN_04": {"T07": ["T07-1", "T07-2"], "S03": ["S03-1", "S03-2"]},
    "CONCERN_05": {"T02": ["T02-5"], "S04": ["S04-2"]},
    "CONCERN_06": {"T05": ["T05-3", "T05-6"]},
    "CONCERN_07": {"T02": ["T02-7", "T02-8"], "S08": ["S08-3", "S08-4"]},
    "CONCERN_08": {"T05": ["T05-1", "T05-2"], "S08": ["S08-5", "S08-6", "S08-7"]},
    "CONCERN_09": {"T06": ["T06-1", "T06-2", "T06-3"], "S07": ["S07-1", "S07-2", "S07-7"]},
    "CONCERN_10": {"T01": ["T01-4", "T01-5", "T01-6"], "S01": ["S01-5", "S01-6"]},
    "CONCERN_11": {"T04": ["T04-5", "T04-6"], "S01": ["S01-3"]},
    "CONCERN_12": {"S06": ["S06-1", "S06-2", "S06-3"]},
    "CONCERN_13": {"S06": ["S06-4", "S06-5", "S06-6"]},
    "CONCERN_14": {"T08": ["T08-1", "T08-2", "T08-4"]},
    "CONCERN_15": {"T07": ["T07-4", "T07-5"]},
    "CONCERN_16": {"S05": ["S05-1", "S05-4"]},
    "CONCERN_17": {"T08": ["T08-3", "T08-5"]},
    "CONCERN_18": {},
}

# ────────────────────────────────────────────────────────────
# 5. Q4 대응습관 → 난이도
# ────────────────────────────────────────────────────────────

HABIT_DIFFICULTY: Dict[str, str] = {
    "HABIT_HANGUP": "hard",
    "HABIT_LISTEN": "normal",
    "HABIT_VERIFY_PERSON": "hard",
    "HABIT_ASK_FAMILY": "hard",
    "HABIT_VERIFY_OFFICIAL": "hard",
    "HABIT_ASK_DETAIL": "normal",
    "HABIT_FOLLOW": "easy",
    "HABIT_VARIABLE": "normal",
}

# ────────────────────────────────────────────────────────────
# 6. 중분류 전체 소분류 풀 (매칭 후보가 없을 때 랜덤 폴백용)
# ────────────────────────────────────────────────────────────

SUBCATEGORY_POOL: Dict[str, List[str]] = {
    "T01": [f"T01-{i}" for i in range(1, 10)],
    "T02": [f"T02-{i}" for i in range(1, 9)],
    "T03": [f"T03-{i}" for i in range(1, 9)],
    "T04": [f"T04-{i}" for i in range(1, 7)],
    "T05": [f"T05-{i}" for i in range(1, 7)],
    "T06": [f"T06-{i}" for i in range(1, 7)],
    "T07": [f"T07-{i}" for i in range(1, 7)],
    "T08": [f"T08-{i}" for i in range(1, 6)],
    "S01": [f"S01-{i}" for i in range(1, 10)],
    "S02": [f"S02-{i}" for i in range(1, 8)],
    "S03": [f"S03-{i}" for i in range(1, 6)],
    "S04": [f"S04-{i}" for i in range(1, 8)],
    "S05": [f"S05-{i}" for i in range(1, 8)],
    "S06": [f"S06-{i}" for i in range(1, 7)],
    "S07": [f"S07-{i}" for i in range(1, 8)],
    "S08": [f"S08-{i}" for i in range(1, 8)],
}

# ────────────────────────────────────────────────────────────
# 7. 중분류 메타데이터 (채널/제목/설명) — 카피는 자유롭게 수정 가능
# ────────────────────────────────────────────────────────────

CATEGORY_META: Dict[str, Dict[str, str]] = {
    "T01": {"channel": "voice", "title": "전화 기반 기관사칭 대응 훈련", "description": "검찰·경찰·금융감독원 등 공공기관을 사칭한 압박형 전화에 대응하는 훈련입니다."},
    "T02": {"channel": "voice", "title": "전화 기반 금융사기 대응 훈련", "description": "대출·카드·투자와 관련된 금융사기 전화에 대응하는 훈련입니다."},
    "T03": {"channel": "voice", "title": "자녀·가족 사칭 전화 대응 훈련", "description": "가족이나 지인을 사칭해 긴급 송금을 요구하는 전화에 대응하는 훈련입니다."},
    "T04": {"channel": "voice", "title": "수사기관 사건 연루 전화 대응 훈련", "description": "본인이 사건에 연루됐다며 협조를 요구하는 전화에 대응하는 훈련입니다."},
    "T05": {"channel": "voice", "title": "대출·취업 사기 전화 대응 훈련", "description": "대출 승인이나 고수익 아르바이트를 미끼로 접근하는 전화에 대응하는 훈련입니다."},
    "T06": {"channel": "voice", "title": "원격제어·악성앱 설치 유도 대응 훈련", "description": "보안 점검을 명목으로 앱 설치나 원격제어를 요구하는 전화에 대응하는 훈련입니다."},
    "T07": {"channel": "voice", "title": "택배·생활 사칭 전화 대응 훈련", "description": "택배나 생활 서비스를 사칭한 전화에 대응하는 훈련입니다."},
    "T08": {"channel": "voice", "title": "관계형성형 사기 대응 훈련", "description": "친밀한 관계를 형성한 뒤 금전을 요구하는 전화(로맨스 스캠 등)에 대응하는 훈련입니다."},
    "S01": {"channel": "sms", "title": "문자 기반 기관사칭 대응 훈련", "description": "공공기관을 사칭한 문자 속 링크에 대응하는 훈련입니다."},
    "S02": {"channel": "sms", "title": "자녀·가족 사칭 문자 대응 훈련", "description": "가족을 사칭해 긴급 송금을 요구하는 문자에 대응하는 훈련입니다."},
    "S03": {"channel": "sms", "title": "택배·배송 스미싱 대응 훈련", "description": "택배 조회를 가장한 문자 속 악성 링크에 대응하는 훈련입니다."},
    "S04": {"channel": "sms", "title": "금융·결제 스미싱 대응 훈련", "description": "결제·환급 안내를 가장한 문자에 대응하는 훈련입니다."},
    "S05": {"channel": "sms", "title": "공공·행정 스미싱 대응 훈련", "description": "과태료·세금 환급 등을 가장한 문자에 대응하는 훈련입니다."},
    "S06": {"channel": "sms", "title": "생활·경조사 스미싱 대응 훈련", "description": "청첩장·경품 등을 가장한 문자에 대응하는 훈련입니다."},
    "S07": {"channel": "sms", "title": "악성앱·피싱 링크 대응 훈련", "description": "악성 앱 설치나 개인정보 입력을 유도하는 문자에 대응하는 훈련입니다."},
    "S08": {"channel": "sms", "title": "투자·대출 스미싱 대응 훈련", "description": "고수익 투자나 저금리 대출을 미끼로 하는 문자에 대응하는 훈련입니다."},
}

# ────────────────────────────────────────────────────────────
# 8. 추천 이유 문장 (실제 선택된 항목 기반으로 동적 조합)
# ────────────────────────────────────────────────────────────

AGE_REASON_TEXT = {
    "AGE_10": "10대 연령대에서 자주 노출되는 유형", "AGE_20": "20대 연령대에서 자주 노출되는 유형",
    "AGE_30": "30대 연령대에서 자주 노출되는 유형", "AGE_40": "40대 연령대에서 자주 노출되는 유형",
    "AGE_50": "50대 연령대에서 자주 노출되는 유형", "AGE_60": "60대 이상 연령대에서 자주 노출되는 유형",
}

ACTIVITY_REASON_TEXT = {
    "ACT_MOBILE_BANKING": "모바일 뱅킹 이용", "ACT_ONLINE_SHOPPING": "온라인 쇼핑 이용",
    "ACT_SECONDHAND": "중고거래 이용", "ACT_INVESTMENT": "주식·코인 투자 관심",
    "ACT_PAYMENT": "카드·간편결제 이용", "ACT_LOAN_INSURANCE": "대출·보험 관심",
    "ACT_JOB": "구직·아르바이트 활동", "ACT_MESSENGER": "메신저로 가족·지인과 연락",
}

CONCERN_REASON_TEXT = {
    "CONCERN_01": "계좌 범죄 연루 연락에 대한 우려", "CONCERN_02": "가족 명의의 긴급 송금 요청 우려",
    "CONCERN_03": "휴대폰 고장을 가장한 연락 우려", "CONCERN_04": "택배 배송 관련 연락 우려",
    "CONCERN_05": "해외 결제 안내 연락 우려", "CONCERN_06": "고수익 아르바이트 제안 노출 우려",
    "CONCERN_07": "고수익 투자 제안 노출 우려", "CONCERN_08": "정부지원 대출 안내 연락 우려",
    "CONCERN_09": "앱 설치·화면공유 요구 우려", "CONCERN_10": "서비스 정지 압박 우려",
    "CONCERN_11": "수사 협조 요청 우려", "CONCERN_12": "경조사 안내 문자 노출 우려",
    "CONCERN_13": "설문·경품 이벤트 문자 노출 우려", "CONCERN_14": "SNS 친분을 통한 금전 요구 우려",
    "CONCERN_15": "통신요금·이용료 안내 연락 우려", "CONCERN_16": "과태료·세금 환급 안내 문자 우려",
    "CONCERN_17": "온라인상 호감 표현 접근 우려", "CONCERN_18": "다양한 사기 유형에 대한 전반적 우려",
}


class RecommendResult(TypedDict):
    recommendedCategory: str
    recommendedSubcategory: str
    channel: str
    title: str
    description: str
    difficulty: str
    match: int
    reasons: List[str]


def _compute_category_scores(survey: dict) -> Dict[str, int]:
    scores = {c: 0 for c in CATEGORY_CODES}

    age = survey.get("age")
    if age in AGE_WEIGHTS:
        for c, w in AGE_WEIGHTS[age].items():
            scores[c] += w

    for act in survey.get("activities", []):
        if act in ACTIVITY_WEIGHTS:
            for c, w in ACTIVITY_WEIGHTS[act].items():
                scores[c] += w

    concerns = survey.get("concerns", [])
    if "CONCERN_18" in concerns:  # 잘 모르겠어요 → 전체 균등 +1
        for c in CATEGORY_CODES:
            scores[c] += 1
    for con in concerns:
        if con in CONCERN_WEIGHTS:
            for c, w in CONCERN_WEIGHTS[con].items():
                scores[c] += w

    return scores


def _select_category(scores: Dict[str, int]) -> str:
    top_score = max(scores.values())
    candidates = [c for c, s in scores.items() if s >= top_score - TIE_THRESHOLD]
    voice_candidates = [c for c in candidates if c.startswith("T")]
    if voice_candidates:
        return max(voice_candidates, key=lambda c: scores[c])
    return max(scores, key=lambda c: scores[c])


def _select_subcategory(category: str, concerns: List[str]) -> str:
    candidate_pool: List[str] = []
    for con in concerns:
        sub_map = CONCERN_SUBCATEGORY_CANDIDATES.get(con, {})
        if category in sub_map:
            candidate_pool.extend(sub_map[category])
    if candidate_pool:
        return random.choice(list(set(candidate_pool)))
    return random.choice(SUBCATEGORY_POOL[category])


def _compute_match_percent(scores: Dict[str, int], chosen: str) -> int:
    """적합도 = 선택된 카테고리가 2위를 얼마나 앞섰는가 (88~98).

    "이 유형이 당신 응답에서 다른 유형들보다 얼마나 뚜렷하게 앞섰는가"를 나타낸다.
    격차가 0이면 88(간발의 차), 5 이상이면 98(압도적).

    ⚠️ 기존 식은 scores[chosen] / sum(전체 16개) 였다. 16개 카테고리가 점수를
    나눠 가져서 그 비율(중앙값 0.14)이 88을 넘는 데 필요한 0.283 에 거의 닿지
    못했고, 결과가 사실상 항상 하한값 88 이었다 (무작위 설문 3000건 중 2999건).
    min(98, ...) 과 * 30 이 죽은 코드였다.
    """
    others = sorted((s for c, s in scores.items() if c != chosen), reverse=True)
    lead = scores[chosen] - (others[0] if others else 0)
    return int(min(98, max(88, 88 + min(lead, 5) * 2)))


def _build_reasons(scores_snapshot: dict, survey: dict, category: str) -> List[str]:
    """실제로 이 카테고리 점수에 기여한 응답들만 추려서 이유 문장을 만듦."""
    contributions: List[tuple] = []  # (weight, text)

    age = survey.get("age")
    if age in AGE_WEIGHTS and AGE_WEIGHTS[age].get(category, 0) > 0:
        contributions.append((AGE_WEIGHTS[age][category], AGE_REASON_TEXT.get(age, "")))

    for act in survey.get("activities", []):
        w = ACTIVITY_WEIGHTS.get(act, {}).get(category, 0)
        if w > 0:
            contributions.append((w, ACTIVITY_REASON_TEXT.get(act, "")))

    for con in survey.get("concerns", []):
        w = CONCERN_WEIGHTS.get(con, {}).get(category, 0)
        if w > 0:
            contributions.append((w, CONCERN_REASON_TEXT.get(con, "")))

    contributions.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    reasons = []
    for _, text in contributions:
        if text and text not in seen:
            reasons.append(text)
            seen.add(text)
        if len(reasons) == 3:
            break

    if not reasons:
        reasons = ["설문 응답을 종합적으로 분석한 결과입니다."]

    return reasons


def recommend(survey: dict) -> RecommendResult:
    """설문 응답을 받아 추천 결과를 반환하는 메인 함수."""
    scores = _compute_category_scores(survey)
    category = _select_category(scores)
    subcategory = _select_subcategory(category, survey.get("concerns", []))
    difficulty = HABIT_DIFFICULTY.get(survey.get("habit"), "normal")
    match = _compute_match_percent(scores, category)
    reasons = _build_reasons(scores, survey, category)
    meta = CATEGORY_META[category]

    return {
        "recommendedCategory": category,
        "recommendedSubcategory": subcategory,
        "channel": meta["channel"],
        "title": meta["title"],
        "description": meta["description"],
        "difficulty": difficulty,
        "match": match,
        "reasons": reasons,
    }


if __name__ == "__main__":
    # 간단 테스트
    sample = {
        "userName": "홍길동",
        "age": "AGE_60",
        "activities": ["ACT_MOBILE_BANKING", "ACT_LOAN_INSURANCE"],
        "concerns": ["CONCERN_01", "CONCERN_09"],
        "habit": "HABIT_LISTEN",
    }
    import json
    print(json.dumps(recommend(sample), ensure_ascii=False, indent=2))
