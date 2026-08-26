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
    delta = (judged_turn - t_first) if (judged_turn is not None and t_first is not None) else None

    if not scenario.is_scam:
        return _grade_normal(
            guessed_scam, judged_turn, t_first, delta, risky_actions, has_critical
        )

    missed = _missed_tell_points(scenario, judged_turn)
    is_correct = guessed_scam is True

    if not is_correct:
        # 끝까지 못 알아챘거나 정상이라고 판단했다 - 실제였다면 피해로 이어진다.
        grade_letter = "D"
    elif has_critical:
        grade_letter = "C"
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


def _missed_tell_points(scenario, judged_turn):
    """판단 시점까지 노출됐는데 훈련생이 지나친 단서."""
    limit = judged_turn if judged_turn is not None else float("inf")
    return [
        tp.id
        for tp in scenario.tell_points
        if tp.signal_type == "risk" and tp.first_detectable_turn <= limit
    ]
