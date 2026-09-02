"""사기꾼 에이전트

캐싱(Anthropic): 시나리오 카드는 세션 내내 고정이므로 cache_control 대상.
턴마다 변하는 상태는 system 이 아니라 messages 끝으로 보낸다.
(Ollama/Gemini 경로에서는 마지막 user 메시지에 접혀 들어간다 — llm.py 참조)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from ..config import scammer_fallback_for
from ..cost import Usage
from ..llm import ChatRequest, chat, is_transient_model_error
from ..prompts import SCAMMER_CORE, scenario_block, turn_state_block
from ..state import current_stage
from ..types import Scenario, SessionState

logger = logging.getLogger(__name__)


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

    req = ChatRequest(
        system=SCAMMER_CORE,
        cached_system=scenario_block(scenario),
        messages=messages,
        turn_state=turn_state_block(stage, state),
    )

    # 이미 내보낸 문장이 있으면 재시도하지 않는다. on_delta 는 StreamingSafetyGate 로
    # 이어지고 승인된 문장은 자막·TTS 로 이미 나갔으므로, 다시 생성하면 훈련생에게
    # 같은 말이 두 번 들린다. 스트림 도중 끊긴 경우가 여기 해당한다.
    emitted = False

    def track(piece: str) -> None:
        nonlocal emitted
        emitted = True
        if on_delta:
            on_delta(piece)

    try:
        res = chat("scammer", req, track)
    except Exception as exc:
        fallback = scammer_fallback_for()
        if emitted or fallback is None or not is_transient_model_error(exc):
            raise
        logger.warning(
            "사기범 모델 일시 장애 - %s 로 한 번 재시도합니다 (%s: %s)",
            fallback,
            type(exc).__name__,
            exc,
        )
        res = chat("scammer", req, track, model=fallback)

    return ScammerResult(
        text=res.text,
        latency_ms=res.latency_ms,
        first_token_ms=res.first_token_ms,
        model=res.model,
        usage=res.usage,
    )
