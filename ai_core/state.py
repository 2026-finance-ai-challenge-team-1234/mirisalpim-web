"""상태머신

핵심 원칙: 단계 전환은 **코드가 승인한다.**
판정기(LLM)는 "전환해야 할 것 같다"고 제안(propose)할 수 있을 뿐,
실제 전환 여부는 이 파일의 조건 검사가 결정한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import (
    DIFFICULTY_BY_LEVEL,
    Difficulty,
    RiskyAction,
    Scenario,
    SessionState,
    Stage,
    Turn,
)


def create_session(scenario: Scenario, difficulty: Difficulty | None = None) -> SessionState:
    """세션 생성.

    difficulty 는 Q4(대응 습관)로 정해진다 (scenario.md §4·§5). 문답을 건너뛰면
    시나리오 카드의 기본 난이도를 쓴다 — 카테고리와는 독립된 축이다.
    """
    return SessionState(
        scenario_id=scenario.scenario_id,
        difficulty=difficulty or DIFFICULTY_BY_LEVEL.get(scenario.difficulty, "normal"),
    )


def current_stage(scenario: Scenario, state: SessionState) -> Stage:
    try:
        return scenario.stages[state.stage_index]
    except IndexError as e:
        raise IndexError(f"stage_index {state.stage_index} 범위 초과") from e


def is_final_stage(scenario: Scenario, state: SessionState) -> bool:
    return state.stage_index >= len(scenario.stages) - 1


@dataclass
class AdvanceResult:
    advanced: bool
    reason: str


def try_advance_stage(
    scenario: Scenario, state: SessionState, proposed: bool = True
) -> AdvanceResult:
    """전환 승인.

    `proposed` 는 판정기의 제안. 최소 턴 수를 채우지 못했으면 무조건 거부하고,
    채웠더라도 판정기가 명시적으로 반대(`proposed=False`)하면 아직 전환하지 않는다.

    기본값이 `True`인 이유: 판정기를 아직 호출하지 않는 경로(테스트, 스모크 등)가
    기존과 동일하게 min_turns 만으로 전환되도록 하기 위함이다. 실제 판정기를 붙인
    경로(engine.step())는 매번 `proposed=judgment.advance_stage` 를 명시적으로 넘긴다.
    """
    stage = current_stage(scenario, state)

    if is_final_stage(scenario, state):
        return AdvanceResult(False, "마지막 단계")

    if state.turns_in_stage < stage.min_turns:
        suffix = " — 판정기 제안 거부" if proposed else ""
        return AdvanceResult(
            False, f"최소 턴 미달 ({state.turns_in_stage}/{stage.min_turns}){suffix}"
        )

    if not proposed:
        return AdvanceResult(False, "최소 턴은 충족했으나 판정기가 아직 이르다고 판단")

    state.stage_index += 1
    state.turns_in_stage = 0
    return AdvanceResult(True, f"→ {current_stage(scenario, state).id}")


def record_turn(
    state: SessionState, role: str, text: str, stage: str, latency_ms: int | None = None
) -> None:
    state.transcript.append(
        Turn(role=role, text=text, turn=state.turn, stage=stage, latency_ms=latency_ms)  # type: ignore[arg-type]
    )


def mark_tell_points(scenario: Scenario, state: SessionState) -> None:
    """이번 턴에 노출된 tell point 를 상태에 기록"""
    for tp in scenario.tell_points:
        if tp.id in state.hit_tell_points:
            continue
        if tp.first_detectable_turn <= state.turn:
            state.hit_tell_points.append(tp.id)


def apply_judgment(state: SessionState, risky_actions: list[str], resisted: bool) -> None:
    """판정기 출력 중 코드가 그대로 신뢰해도 되는 부분(위험행동·저항횟수)을 상태에 반영한다.

    advance_stage 는 여기서 다루지 않는다 — try_advance_stage() 에 proposed 로
    넘겨 min_turns 조건과 함께 검사해야 하므로 호출부(engine.step())가 직접 처리한다.
    """
    for action_type in risky_actions:
        state.risky_actions.append(RiskyAction(turn=state.turn, type=action_type))
    if resisted:
        state.resistance_count += 1
