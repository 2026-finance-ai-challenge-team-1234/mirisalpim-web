"""훈련 채점 — 규칙 기반, 결정론적.

리포트 문서(§1·§8)의 원칙: 점수·등급은 코드가 계산하고 LLM 은 해석만 한다.
DB 도 LLM 도 타지 않는 순수 함수라 단독으로 테스트한다.

등급 기준은 기획서 §5.2 표를 따른다.
"""

from dataclasses import dataclass, field

#: 위험행동 심각도. 리포트 문서 "확정 2. 위험행동은 심각도에 따라 차등 반영".
#: ⚠️ 어느 행동이 치명적인지는 팀 확인 전 잠정값이다.
CRITICAL_ACTIONS = {"transfer_consent", "app_install", "personal_info"}
MINOR_ACTIONS = {"link_click", "isolation_accepted"}

#: 정상 시나리오를 사기로 신고한 경우. S~D 와 분리해서 다룬다.
FALSE_ALARM = "오탐"

#: DB·ai_core 의 snake_case 값 → API 가 내보내는 이름.
#: turns 의 riskWarnings[].type 과 judgment 의 riskyActions 가 같은 표기를 쓰도록
#: 여기 한 곳에서만 정한다 (API 설계 2-1: JSON 은 camelCase).
#: 예전에는 두 응답이 각자 만들어서 isolationAcceptance / isolation_accepted 처럼
#: 같은 개념이 다른 이름으로 나갔다.
ACTION_API_NAMES = {
    "personal_info": "personalInfo",
    "link_click": "linkClick",
    "app_install": "appInstall",
    "transfer_consent": "transferConsent",
    "isolation_accepted": "isolationAcceptance",
}


@dataclass
class GradeResult:
    grade: str
    is_correct: bool
    judged_turn: int | None
    first_detectable_turn: int | None
    delta: int | None
    #: 판단 시점까지 노출됐는데 놓친 단서 (tp_key 순서 유지)
    missed_tell_points: list[str] = field(default_factory=list)
    risky_actions: list[str] = field(default_factory=list)
    has_critical_action: bool = False


def first_detectable_turn(scenario):
    """최초 판별 가능 턴. 사기 시나리오는 risk 신호, 정상 시나리오는 legitimacy 신호."""
    wanted = "risk" if scenario.is_scam else "legitimacy"
    turns = [tp.first_detectable_turn for tp in scenario.tell_points if tp.signal_type == wanted]
    return min(turns) if turns else None


def exchange_index(turn):
    """턴 번호 → 훈련생이 세는 "N번째 대화".

    state.turn 은 상대 발화(1) 다음에 훈련생 1턴 + 상대 1턴씩 늘어서 상대의 메시지는
    항상 홀수 턴이다(1, 3, 5...). 화면에는 이 값을 그대로 "N번째 대화"라고 쓰면 안 된다 -
    turn 3 은 세 번째가 아니라 두 번째 대화다.
    """
    return None if turn is None else (turn + 1) // 2


def exchanges_since_detectable(judged_turn, t_first):
    """판별 가능 시점 이후 몇 번을 더 주고받고 판단했는가.

    ⚠️ 턴 차이를 그대로 쓰면 안 된다. 한 번의 교환마다 턴이 2씩 오르고 t_first 는
    거의 항상 1이라 차이가 늘 짝수가 된다. 그러면 S(<=1)·A(<=3) 의 홀수 임계값에
    아무도 걸리지 않아 **한 마디라도 하면 S 가 불가능**했고, 반대로
    _missed_tell_points 의 delta<=1 게이트도 0교환이 아니면 항상 열려서 거의 모든
    훈련생이 "1번째 대화 신호를 지나쳤다" 는 리포트를 받았다.
    """
    if judged_turn is None or t_first is None:
        return None
    return (judged_turn - t_first) // 2


def grade(scenario, state):
    """시나리오 카드와 세션 상태로 등급을 낸다.

    state.user_judgment 가 None 이면 훈련생이 끝까지 판단하지 않은 것으로 본다.
    """
    judgment = state.user_judgment
    judged_turn = judgment.turn if judgment else None
    guessed_scam = judgment.is_scam_guess if judgment else None

    risky_actions = [action.type for action in state.risky_actions]
    has_critical = any(action in CRITICAL_ACTIONS for action in risky_actions)
    has_minor = any(action in MINOR_ACTIONS for action in risky_actions)

    t_first = first_detectable_turn(scenario)
    #: 턴 수가 아니라 **주고받은 횟수**다 (exchanges_since_detectable 주석 참고).
    delta = exchanges_since_detectable(judged_turn, t_first)

    if not scenario.is_scam:
        return _grade_normal(
            guessed_scam, judged_turn, t_first, delta, risky_actions, has_critical
        )

    missed = _missed_tell_points(scenario, judged_turn, delta)
    is_correct = guessed_scam is True

    if not is_correct:
        # 끝까지 못 알아챘거나 정상이라고 판단했다 - 실제였다면 피해로 이어진다.
        grade_letter = "D"
    elif has_critical:
        grade_letter = "C"
    # 아래 임계값의 단위는 "대화 횟수" 다. S=바로 알아챔, A=몇 번 안에, B=늦게.
    elif delta is not None and delta <= 1 and not risky_actions:
        grade_letter = "S"
    elif delta is not None and delta <= 3 and not risky_actions:
        grade_letter = "A"
    elif (delta is not None and delta <= 6) or has_minor:
        grade_letter = "B"
    else:
        grade_letter = "C"

    return GradeResult(
        grade=grade_letter,
        is_correct=is_correct,
        judged_turn=judged_turn,
        first_detectable_turn=t_first,
        delta=delta,
        missed_tell_points=missed,
        risky_actions=risky_actions,
        has_critical_action=has_critical,
    )


def _grade_normal(guessed_scam, judged_turn, t_first, delta, risky_actions, has_critical):
    """정상 시나리오. 사기로 신고하면 오탐이다 (기능명세 F-21).

    과잉 의심도 실패로 다루되 비난하지 않는다 - "의심 자체는 옳은 반응"이라는
    피드백은 diagnosis 가 붙인다.
    """
    if guessed_scam is True:
        return GradeResult(
            grade=FALSE_ALARM,
            is_correct=False,
            judged_turn=judged_turn,
            first_detectable_turn=t_first,
            delta=delta,
            risky_actions=risky_actions,
            has_critical_action=has_critical,
        )

    return GradeResult(
        grade="C" if has_critical else "S",
        is_correct=True,
        judged_turn=judged_turn,
        first_detectable_turn=t_first,
        delta=delta,
        risky_actions=risky_actions,
        has_critical_action=has_critical,
    )


def _missed_tell_points(scenario, judged_turn, delta):
    """판단하기까지 지나쳐 보낸 단서.

    ⚠️ "판단 시점까지 노출된 단서" 를 그대로 쓰면 안 된다. 판별 가능해지자마자
    알아채 S 등급을 받은 훈련생에게도 리포트가 "N번째 턴 신호를 지나쳤습니다"
    (diagnosis._weakness) 라고 말하게 된다. 등급과 정면으로 모순된다.

    훈련생이 실제로 무엇을 알아챘는지 관찰하는 주체가 아직 없어서 - state 의
    hit_tell_points 는 "훈련생이 알아챘다" 가 아니라 "턴 번호상 노출됐다" 는
    뜻이다 - 판단 시점으로 근사한다. 두 가지를 반영한다.

    · 최초 판별 가능 시점 직후(대화 1회 이내)에 알아챘으면 지나친 단서는 없다.
    · 판단한 바로 그 턴에 처음 드러난 단서는 지나친 것이 아니다 (< 로 자른다).

    판정기에 "훈련생이 이 단서를 언급했는가" 가 추가되면 이 근사를 걷어낸다.
    """
    if delta is not None and delta <= 1:
        return []

    limit = judged_turn if judged_turn is not None else float("inf")
    return [
        tp.id
        for tp in scenario.tell_points
        if tp.signal_type == "risk" and tp.first_detectable_turn < limit
    ]
