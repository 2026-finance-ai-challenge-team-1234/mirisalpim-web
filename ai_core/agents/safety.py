"""안전 필터 에이전트 — 사기꾼 발화가 화면에 나가기 전 마지막 방어선.

판정기와 검증 대상이 반대다: 판정기는 훈련생 발화를, 안전 필터는 사기꾼(LLM)
발화를 본다. CLAUDE.md 의 "비협상 안전 제약" 중 텍스트로 검증 가능한 항목만
확인한다(실제 URL·계좌·실존 기관명·역할 깨기). 음성 클로닝·로그 내보내기 등은
이 필터의 대상이 아니다(다른 레이어의 제약).

구조화 출력(response_schema)만 지원한다 — 지금은 gemini 경로 전용.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..cost import Usage
from ..llm import ChatRequest, chat
from ..prompts import SAFETY_CORE, SAFETY_SCHEMA


@dataclass
class SafetyResult:
    blocked: bool
    #: role_break/prompt_leak/real_url/real_account/real_org 중 해당하는 것
    violations: list[str]
    reasoning: str
    model: str
    latency_ms: int
    usage: Usage = field(default_factory=Usage)


def check_safety(scammer_text: str) -> SafetyResult:
    """사기꾼이 방금 생성한 발화 하나를 검사한다.

    세션 맥락은 필요 없다 — 발화 자체에 금지 콘텐츠가 있는지만 본다.
    """
    res = chat(
        "safety",
        ChatRequest(
            system=SAFETY_CORE,
            messages=[{"role": "user", "content": scammer_text}],
            response_schema=SAFETY_SCHEMA,
        ),
    )

    data = json.loads(res.text)

    return SafetyResult(
        blocked=bool(data["blocked"]),
        violations=list(data["violations"]),
        reasoning=str(data["reasoning"]),
        model=res.model,
        latency_ms=res.latency_ms,
        usage=res.usage,
    )
