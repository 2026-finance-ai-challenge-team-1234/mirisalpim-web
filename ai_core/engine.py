"""턴 파이프라인. Django 뷰에서 그대로 호출할 수 있도록 프레임워크 의존이 없다.

판정기 제안 → 코드 상태 승인 흐름:
  1. 훈련생 발화를 기록한다.
  2. 판정기가 이번 발화를 분석해 제안한다 (advance_stage / risky_actions / resisted).
  3. 위험행동·저항횟수는 그대로 상태에 반영한다 (state.apply_judgment) — 이건
     판정기가 "관찰한 사실"이라 코드가 다시 검증할 필요가 없다.
  4. advance_stage 제안은 try_advance_stage() 에 proposed 로 넘긴다 — 최소 턴 수
     조건과 함께 코드가 최종 승인해야 실제로 전환된다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .agents.judge import generate_judge_turn
from .agents.safety import check_safety
from .agents.scammer import generate_scammer_turn
from .cost import Usage
from .prompts import SAFETY_FALLBACK_TEXT
from .state import (
    apply_judgment,
    create_session,
    current_stage,
    is_final_stage,
    mark_tell_points,
    record_turn,
    try_advance_stage,
)
from .types import Difficulty, Scenario, SessionState

#: mirisalpim-web/data/scenarios/ — ai_core 와 형제 디렉터리. Django(SCENARIO_SEED_DIR)와
#: 같은 원본을 읽는다. 배포 저장소(mirisalpim-web) 안에 있어야 Railway 등에서 실제로 존재한다 —
#: 예전에는 AI_challenge/scenario/ 를 가리켜서 mirisalpim-web 단독 체크아웃 시 없는 경로였다.
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"


def load_scenario(scenario_id: str) -> Scenario:
    path = DATA_DIR / f"{scenario_id}.json"
    if not path.exists():
        available = ", ".join(p.stem for p in DATA_DIR.glob("*.json")) or "(없음)"
        raise FileNotFoundError(
            f"시나리오 '{scenario_id}' 없음. 사용 가능: {available}"
        )
    return Scenario.from_dict(json.loads(path.read_text(encoding="utf-8")))


@dataclass
class Engine:
    scenario: Scenario
    state: SessionState


def start_session(scenario: Scenario, difficulty: Difficulty | None = None) -> Engine:
    state = create_session(scenario, difficulty)
    stage = current_stage(scenario, state)

    # 1턴은 API 호출 없이 시나리오의 opening 을 그대로 쓴다.
    # 결정적이고, 지연이 0이고, 반드시 각본 위에서 시작한다.
    state.turn = 1
    state.turns_in_stage = 1
    record_turn(state, "scammer", stage.opening or "(opening 미정의)", stage.id)
    mark_tell_points(scenario, state)

    return Engine(scenario=scenario, state=state)


@dataclass
class TurnOutcome:
    scammer_text: str
    latency_ms: int
    first_token_ms: int
    stage_changed: str | None
    ended: bool
    end_reason: str | None = None
    #: 판정기 + 사기꾼 호출 합산
    usage: Usage = field(default_factory=Usage)
    #: 이번 턴 판정기가 관찰한 위험행동 (RiskyAction.ACTION_TYPE 값들). use_judge=False 면 빈 리스트
    risky_actions: list[str] = field(default_factory=list)
    #: 이번 턴 훈련생이 저항했는가. use_judge=False 면 None(판정 안 함)
    resisted: bool | None = None
    #: 안전 필터가 사기꾼 발화를 차단했는가. 차단 시 scammer_text 는 대체 문구다.
    blocked: bool = False
    #: 차단 사유 (role_break/prompt_leak/real_url/real_account/real_org). use_safety=False 면 빈 리스트
    safety_violations: list[str] = field(default_factory=list)


def step(
    engine: Engine,
    user_text: str,
    on_delta: Callable[[str], None] | None = None,
    use_judge: bool = True,
    use_safety: bool = True,
) -> TurnOutcome:
    """사용자 발화를 받아 한 턴 진행.

    use_judge=True(기본) 면 판정기를 호출해 advance_stage 를 제안받는다.
    use_safety=True(기본) 면 사기꾼 발화를 안전 필터로 검사해 위반 시 대체 문구로 바꾼다.
    둘 다 지금은 gemini 프로바이더 전용이다 (llm.py, response_schema 구조화 출력).
    판정기·안전 필터 없이 기존 PoC-1 방식(min_turns만으로 전환, 필터 없이 그대로 표시)으로
    쓰려면 둘 다 False 로 호출한다.

    ⚠️ on_delta 로 스트리밍하는 경로와 안전 필터는 아직 상호작용을 정리하지 않았다 —
    지금은 완성된 전체 텍스트를 사후 검사한다. Controlled Streaming Cascade(문장 단위
    TTS)를 실제로 붙일 때는 문장 단위 검사로 다시 설계해야 한다 (idea-plan.md §4.1,
    텍스트 수직 통합 이후 순서로 이미 그렇게 계획돼 있음).
    """
    scenario, state = engine.scenario, engine.state

    state.turn += 1
    record_turn(state, "user", user_text, current_stage(scenario, state).id)

    usage = Usage()
    proposed = True
    risky_actions: list[str] = []
    resisted: bool | None = None

    if use_judge:
        # 최종 단계에서도 판정기는 호출한다 — advance_stage 제안은 try_advance_stage()가
        # is_final_stage 로 어차피 무시하지만, risky_actions/resisted 관찰은 extraction
        # 단계(송금 동의 등 가장 중요한 위험행동이 실제로 일어나는 곳)에서도 필요하다.
        judgment = generate_judge_turn(scenario, state)
        apply_judgment(state, judgment.risky_actions, judgment.resisted)
        proposed = judgment.advance_stage
        risky_actions = judgment.risky_actions
        resisted = judgment.resisted
        usage.add(judgment.usage)

    adv = try_advance_stage(scenario, state, proposed=proposed)
    stage_changed = current_stage(scenario, state).id if adv.advanced else None

    if state.turn >= scenario.max_turns:
        return TurnOutcome(
            scammer_text="",
            latency_ms=0,
            first_token_ms=0,
            stage_changed=stage_changed,
            ended=True,
            end_reason=f"최대 턴({scenario.max_turns}) 도달",
            usage=usage,
            risky_actions=risky_actions,
            resisted=resisted,
        )

    state.turn += 1
    state.turns_in_stage += 1

    result = generate_scammer_turn(scenario, state, on_delta)
    usage.add(result.usage)

    scammer_text = result.text
    blocked = False
    safety_violations: list[str] = []

    if use_safety:
        safety = check_safety(result.text)
        usage.add(safety.usage)
        blocked = safety.blocked
        safety_violations = safety.violations
        if blocked:
            # 차단된 원문은 기록하지 않는다 — 대체 문구만 transcript 에 남긴다.
            scammer_text = SAFETY_FALLBACK_TEXT

    record_turn(
        state,
        "scammer",
        scammer_text,
        current_stage(scenario, state).id,
        result.latency_ms,
    )
    mark_tell_points(scenario, state)

    return TurnOutcome(
        scammer_text=scammer_text,
        latency_ms=result.latency_ms,
        first_token_ms=result.first_token_ms,
        stage_changed=stage_changed,
        ended=False,
        usage=usage,
        risky_actions=risky_actions,
        resisted=resisted,
        blocked=blocked,
        safety_violations=safety_violations,
    )


def stage_progress(engine: Engine) -> str:
    scenario, state = engine.scenario, engine.state
    bars = "".join(
        "●" if i < state.stage_index else "◉" if i == state.stage_index else "○"
        for i in range(len(scenario.stages))
    )
    final = " (최종)" if is_final_stage(scenario, state) else ""
    return f"{bars} {current_stage(scenario, state).id}{final}"
