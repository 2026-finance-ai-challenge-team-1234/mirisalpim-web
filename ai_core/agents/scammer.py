"""사기꾼 에이전트

캐싱(Anthropic): 시나리오 카드는 세션 내내 고정이므로 cache_control 대상.
턴마다 변하는 상태는 system 이 아니라 messages 끝으로 보낸다.
(Ollama/Gemini 경로에서는 마지막 user 메시지에 접혀 들어간다 — llm.py 참조)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..cost import Usage
from ..llm import ChatRequest, chat
from ..prompts import SCAMMER_CORE, scenario_block, turn_state_block
from ..state import current_stage
from ..types import Scenario, SessionState


@dataclass
class ScammerResult:
    text: str
    latency_ms: int
    #: 첫 토큰까지 걸린 시간 — 음성 파이프라인 실현 가능성 판단용
    first_token_ms: int
    model: str
    usage: Usage = field(default_factory=Usage)


def generate_scammer_turn(
    scenario: Scenario,
    state: SessionState,
    on_delta: Callable[[str], None] | None = None,
) -> ScammerResult:
    stage = current_stage(scenario, state)

    messages: list[dict[str, str]] = [
        {"role": "user", "content": "(통화가 연결되었습니다)"}
    ]
    for t in state.transcript:
        messages.append(
            {
                "role": "assistant" if t.role == "scammer" else "user",
                "content": t.text,
            }
        )

    res = chat(
        "scammer",
        ChatRequest(
            system=SCAMMER_CORE,
            cached_system=scenario_block(scenario),
            messages=messages,
            turn_state=turn_state_block(stage, state),
        ),
        on_delta,
    )

    return ScammerResult(
        text=res.text,
        latency_ms=res.latency_ms,
        first_token_ms=res.first_token_ms,
        model=res.model,
        usage=res.usage,
    )
