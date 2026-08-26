"""P-02 문진 기반 추천 (규칙 기반).

⚠️ 임시 구현이다. 프론트 Survey.jsx 주석과 recommendationApi.js 가 참조하는
`recommendation_engine.py` / `survey-logic-final.md` 는 배포 저장소에 없다.
그 파일이 확보되면 이 모듈을 그것으로 교체하거나 매핑표를 대조해 맞춘다.
API 계약(요청 코드값 / 응답 필드)은 프론트가 이미 쓰고 있는 형태를 그대로 지킨다.

설계 원칙: 추천 결과는 반드시 "실제로 훈련 가능한" track 이어야 한다. 분류표는
54칸인데 시나리오는 12칸만 있어서, 매핑이 가리킨 track 에 시나리오가 없으면
다음 후보로 내려간다.
"""

#: 연령 코드 → Scenario.target_tracks 값
AGE_TO_TARGET_TRACK = {
    "AGE_10": "teen",
    "AGE_20": "young",
    "AGE_30": "young",
    "AGE_40": "middle_age",
    "AGE_50": "middle_age",
    "AGE_60": "senior",
}

#: 대응 습관(Q4) → 진행 난이도. models.Session.DIFFICULTY 주석이 정한 축이다.
#: 잘 대응하는 습관일수록 어려운 시나리오를 준다.
HABIT_TO_DIFFICULTY = {
    "HABIT_HANGUP": "hard",
    "HABIT_VERIFY_OFFICIAL": "hard",
    "HABIT_VERIFY_PERSON": "normal",
    "HABIT_ASK_FAMILY": "normal",
    "HABIT_VARIABLE": "normal",
    "HABIT_LISTEN": "easy",
    "HABIT_ASK_DETAIL": "easy",
    "HABIT_FOLLOW": "easy",
}

#: 걱정되는 상황(Q3) → 선호 track (앞에 있을수록 우선)
CONCERN_TO_TRACKS = {
    "CONCERN_01": ["T04-1", "T01-1", "T01-2"],
    "CONCERN_02": ["T03-1", "T03-8"],
    "CONCERN_03": ["T03-5", "T03-6"],
    "CONCERN_04": ["T07-1", "T07-2"],
    "CONCERN_05": ["T02-5", "T01-5"],
    "CONCERN_06": ["T05-3", "T05-4"],
    "CONCERN_07": ["T08-3", "T02-7"],
    "CONCERN_08": ["T05-1", "T05-2"],
    "CONCERN_09": ["T06-2", "T06-1"],
    "CONCERN_10": ["T01-4", "T01-5"],
    "CONCERN_11": ["T01-1", "T01-3"],
    "CONCERN_12": ["S06-1", "S06-2"],
    "CONCERN_13": ["S06-4", "S06-6"],
    "CONCERN_14": ["T08-1", "T08-3"],
    "CONCERN_15": ["T07-4", "T07-5"],
    "CONCERN_16": ["S05-1", "S05-4"],
    "CONCERN_17": ["T08-1", "T08-4"],
    "CONCERN_18": [],
}

#: 리포트에 보여줄 추천 근거 문구
CONCERN_REASONS = {
    "CONCERN_01": "계좌가 범죄에 연루됐다는 연락을 걱정하고 계십니다",
    "CONCERN_02": "가족의 급한 송금 요청을 걱정하고 계십니다",
    "CONCERN_03": "휴대폰 고장을 이유로 한 번호 변경 연락을 걱정하고 계십니다",
    "CONCERN_04": "택배 배송 문제 안내를 걱정하고 계십니다",
    "CONCERN_05": "해외 결제 승인 연락을 걱정하고 계십니다",
    "CONCERN_06": "고수익 아르바이트 제안을 걱정하고 계십니다",
    "CONCERN_07": "원금 보장·고수익 투자 제안을 걱정하고 계십니다",
    "CONCERN_08": "정부지원 대출 안내를 걱정하고 계십니다",
    "CONCERN_09": "앱 설치·화면공유 요구를 걱정하고 계십니다",
    "CONCERN_10": "계좌·서비스 정지 압박을 걱정하고 계십니다",
    "CONCERN_11": "출석 요구·수사 협조 요청을 걱정하고 계십니다",
    "CONCERN_12": "경조사 안내 문자를 걱정하고 계십니다",
    "CONCERN_13": "설문조사·경품 당첨 문자를 걱정하고 계십니다",
    "CONCERN_14": "SNS 로 친해진 사람의 투자 권유를 걱정하고 계십니다",
    "CONCERN_15": "통신요금 미납 안내 전화를 걱정하고 계십니다",
    "CONCERN_16": "과태료·세금 환급 문자를 걱정하고 계십니다",
    "CONCERN_17": "온라인에서 호감을 표하며 접근하는 상황을 걱정하고 계십니다",
    "CONCERN_18": "",
}

#: 평소 활동(Q2) → 보조 신호. 걱정 항목이 비었을 때 후보를 만든다.
ACTIVITY_TO_TRACKS = {
    "ACT_MOBILE_BANKING": ["T01-5", "T01-4"],
    "ACT_ONLINE_SHOPPING": ["T07-1", "T07-3"],
    "ACT_SECONDHAND": ["S03-3", "T07-1"],
    "ACT_INVESTMENT": ["T08-3", "T02-7"],
    "ACT_PAYMENT": ["T02-5", "T01-5"],
    "ACT_LOAN_INSURANCE": ["T05-1", "T05-2"],
    "ACT_JOB": ["T05-3", "T05-4"],
    "ACT_MESSENGER": ["T03-1", "T03-5"],
    "ACT_NONE": [],
}

#: 아무 신호도 안 맞을 때. 시나리오가 가장 두터운 유형이다.
FALLBACK_TRACKS = ["T01-1", "T01-2", "T03-1", "T05-1"]


def _candidate_tracks(answers):
    """선호 track 을 우선순위대로 늘어놓는다 (중복 제거)."""
    ordered = []
    for concern in answers.get("concerns") or []:
        ordered.extend(CONCERN_TO_TRACKS.get(concern, []))
    for activity in answers.get("activities") or []:
        ordered.extend(ACTIVITY_TO_TRACKS.get(activity, []))
    ordered.extend(FALLBACK_TRACKS)

    seen = set()
    return [t for t in ordered if not (t in seen or seen.add(t))]


def recommend(answers, trainable_tracks):
    """문진 응답 → 추천 track. 훈련 불가능한 track 은 절대 반환하지 않는다.

    trainable_tracks 가 비어 있으면 None (적재된 시나리오가 하나도 없는 상태).
    """
    if not trainable_tracks:
        return None

    for track in _candidate_tracks(answers):
        if track in trainable_tracks:
            return {
                "track": track,
                "difficulty": HABIT_TO_DIFFICULTY.get(answers.get("habit"), "normal"),
                "target_track": AGE_TO_TARGET_TRACK.get(answers.get("age")),
                "matched": _matched_reasons(answers, track),
            }

    # 후보가 전부 미적재면 훈련 가능한 것 중 하나로 떨어뜨린다.
    return {
        "track": sorted(trainable_tracks)[0],
        "difficulty": HABIT_TO_DIFFICULTY.get(answers.get("habit"), "normal"),
        "target_track": AGE_TO_TARGET_TRACK.get(answers.get("age")),
        "matched": [],
    }


def _matched_reasons(answers, track):
    """추천된 track 을 실제로 지목한 걱정 항목의 문구만 모은다."""
    reasons = []
    for concern in answers.get("concerns") or []:
        if track in CONCERN_TO_TRACKS.get(concern, []):
            text = CONCERN_REASONS.get(concern)
            if text:
                reasons.append(text)
    return reasons
