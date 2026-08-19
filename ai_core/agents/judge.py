"""판정기 에이전트

핵심 원칙: 단계 전환은 **코드가 승인한다.**
이 에이전트는 advance_stage 를 "제안"할 뿐이며, 실제 전환 여부는
state.try_advance_stage() 가 min_turns 등 다른 조건과 함께 최종 결정한다.

risky_actions 는 training.RiskyAction.ACTION_TYPE(Django 모델)과 동일한 5종 enum만
반환한다 — 이 값을 그대로 RiskyAction 행으로 저장할 수 있다.

구조화 출력(response_schema)만 지원한다 — 지금은 gemini 경로 전용
(llm.py 의 _chat_anthropic 에는 아직 output_config.format 이 없다).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..cost import Usage
from ..llm import ChatRequest, chat
from ..prompts import JUDGE_CORE, JUDGE_SCHEMA, advance_criteria_block, scenario_block
from ..state import current_stage
from ..types import Scenario, SessionState


@dataclass
class JudgeResult:
    advance_stage: bool
    #: training.RiskyAction.ACTION_TYPE 값만 (personal_info/link_click/app_install/
    #: transfer_consent/isolation_accepted). 중복 없이 0개 이상.
    risky_actions: list[str]
    resisted: bool
    reasoning: str
    model: str
    latency_ms: int
    usage: Usage = field(default_factory=Usage)


def generate_judge_turn(scenario: Scenario, state: SessionState) -> JudgeResult:
    """가장 최근 훈련생(user) 발화를 판정한다. transcript 끝이 user 턴이어야 한다."""
    if not state.transcript or state.transcript[-1].role != "user":
        raise ValueError("판정할 훈련생 발화가 없습니다 (transcript 마지막이 user 가 아님)")

    stage = current_stage(scenario, state)

    # 역할 반전 없음 — 사기꾼 발화가 assistant, 훈련생 발화가 user (스캠 시점 그대로)
    messages: list[dict[str, str]] = [
        {"role": "user", "content": "(통화가 연결되었습니다)"}
    ]
    for t in state.transcript:
        messages.append(
            {"role": "assistant" if t.role == "scammer" else "user", "content": t.text}
        )

    turn_state = (
        f"[현재 단계] {stage.id} — {stage.objective}"
        f"{advance_criteria_block(stage)}\n"
        "판정 대상은 위 대화의 마지막 훈련생(user) 발화입니다."
    )

    res = chat(
        "judge",
        ChatRequest(
            system=JUDGE_CORE,
            cached_system=scenario_block(scenario),
            messages=messages,
            turn_state=turn_state,
            response_schema=JUDGE_SCHEMA,
        ),
    )

    data = json.loads(res.text)

    return JudgeResult(
        advance_stage=bool(data["advance_stage"]),
        risky_actions=list(data["risky_actions"]),
        resisted=bool(data["resisted"]),
        reasoning=str(data["reasoning"]),
        model=res.model,
        latency_ms=res.latency_ms,
        usage=res.usage,
    )
