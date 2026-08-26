"""진단 리포트 생성 — 규칙 기반.

리포트 문서 §4: 진단 LLM 은 이미 계산된 사실을 받아 "해석·요약만" 한다. 점수·등급·
단서 발생 여부·위험행동 발생 여부는 전부 코드가 정한다.

지금은 규칙 기반 문장만 만든다. API 설계 9절이 진단에 "180초 + 규칙 기반 fallback"
을 두기로 했으므로, LLM 이 붙어도 이 경로는 fallback 으로 남는다.

🔜 LLM 훅: build_report() 가 만든 dict 의 summary/strength/weakness 를 진단 LLM
   출력으로 덮어쓰면 된다. grade·missed_tell_points·guidance 는 덮어쓰지 않는다.
"""

from .grading import FALSE_ALARM

#: 놓친 단서 설명은 시나리오 카드의 why 를 그대로 쓴다 (리포트 문서 §5-④:
#: "이 부분은 LLM 생성이 필요하지 않다").


def build_report(scenario, state, result):
    """등급 결과 → 화면에 그대로 쓸 수 있는 리포트 dict."""
    tell_points = {tp.id: tp for tp in scenario.tell_points}
    missed = [
        {
            "id": tp_id,
            "turn": tell_points[tp_id].first_detectable_turn,
            "trigger": tell_points[tp_id].trigger,
            "why": tell_points[tp_id].why,
            "weight": tell_points[tp_id].weight,
        }
        for tp_id in result.missed_tell_points
        if tp_id in tell_points
    ]

    return {
        "grade": result.grade,
        "isCorrect": result.is_correct,
        "judgedTurn": result.judged_turn,
        "firstDetectableTurn": result.first_detectable_turn,
        "summary": _summary(scenario, result),
        "strength": _strength(state, result),
        "weakness": _weakness(missed, result),
        "missedTellPoints": missed,
        "riskyActions": result.risky_actions,
        "guidance": list(scenario.debrief_points),
        "timeline": _timeline(state, tell_points, result),
    }


def _summary(scenario, result):
    if result.grade == FALSE_ALARM:
        return (
            "이번 상황은 정상 안내였습니다. 다만 의심하고 재확인하려는 행동 자체는 "
            "안전한 대응입니다. 다음에는 안내받은 번호가 아니라 공식 앱·대표번호로 "
            "직접 확인해 보세요."
        )
    if not scenario.is_scam:
        return "이번 상황은 정상 안내였고, 사기로 단정하지 않으셨습니다."
    if not result.is_correct:
        return "끝까지 사기임을 알아차리지 못했습니다. 실제였다면 피해로 이어졌을 상황입니다."

    line = f"{result.judged_turn}번째 턴에서 사기임을 알아차리셨습니다."
    if result.first_detectable_turn is not None:
        line += f" 가장 빠른 판별 가능 시점은 {result.first_detectable_turn}번째 턴이었습니다."
    return line


def _strength(state, result):
    """리포트 문서 §8: 잘한 점을 반드시 1개 이상 포함한다.

    ⚠️ safe_actions(공식 채널 재확인·링크 거부 등)를 관찰하는 주체가 아직 없어서
    저항 횟수와 위험행동 부재로만 판단한다. 판정기에 safe_actions 가 추가되면
    여기를 그 값으로 바꾼다.
    """
    if state.resistance_count > 0:
        return (
            f"상대의 요구를 그대로 따르지 않고 {state.resistance_count}번 되물었거나 "
            "거절하셨습니다."
        )
    if not result.risky_actions:
        return "개인정보 제공·송금·앱 설치 같은 위험한 행동은 하지 않으셨습니다."
    if result.is_correct:
        return "늦었지만 스스로 사기임을 알아차리고 대화를 멈추셨습니다."
    return "끝까지 대화를 이어가며 상대의 수법을 직접 겪어보셨습니다."


def _weakness(missed, result):
    if result.has_critical_action:
        return "실제였다면 곧바로 피해로 이어질 행동까지 진행하셨습니다."
    if not missed:
        return "특별히 놓친 판별 단서는 없었습니다."
    heaviest = max(missed, key=lambda m: m["weight"])
    return f"{heaviest['turn']}번째 턴의 신호를 지나쳤습니다 — {heaviest['trigger']}"


def _timeline(state, tell_points, result):
    """턴별 마커. 원문 텍스트는 담지 않는다 (종료 후 파기 대상이라 재현 불가)."""
    by_turn = {}
    for tp in tell_points.values():
        if tp.id in result.missed_tell_points:
            by_turn.setdefault(tp.first_detectable_turn, []).append("tellPoint")
    for action in state.risky_actions:
        by_turn.setdefault(action.turn, []).append("riskyAction")
    if result.judged_turn is not None:
        by_turn.setdefault(result.judged_turn, []).append("judgment")

    return [
        {"turn": turn, "markers": markers}
        for turn, markers in sorted(by_turn.items())
    ]
